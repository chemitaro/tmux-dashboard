"""オーケストレータのテスト。

目的:
- セッション検出→ASCII昇順→`dashboard`除外。
- ウィンドウ寸法からレイアウト計算（columns/rows）。
- スプリット呼び出し回数（簡易）とタイトル設定（pane title）を確認。
"""

from __future__ import annotations


class FakeIO:
    def __init__(self, sessions, width, height, panes):
        self._sessions = sessions
        self._width = width
        self._height = height
        self._panes = list(panes)
        self.set_window_option_calls = []
        self.set_title_calls = []
        self.split_calls = []  # (dir, percent)
        self.kill_calls = 0

    def list_sessions(self):
        return list(self._sessions)

    def window_size(self, window_target: str):
        return self._width, self._height

    def list_panes(self, window_target: str):
        return list(self._panes)

    def set_window_option(self, window_target: str, key: str, value: str):
        self.set_window_option_calls.append((window_target, key, value))

    def set_pane_title(self, pane_id: str, title: str):
        self.set_title_calls.append((pane_id, title))

    def split_window(self, window_target: str, direction: str, percent: int):
        self.split_calls.append((direction, percent))

    def kill_other_panes(self, window_target: str):
        self.kill_calls += 1


def test_scan_sort_exclude_and_titles_and_layout():
    """セッションはASCII昇順で`dashboard`除外、columns/rows計算とタイトル設定を行う。"""
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["gamma", "dashboard", "alpha", "beta"], width=120, height=50, panes=["%1", "%2", "%3"])
    c = config.load_config(None)
    o = orchestrator.Orchestrator(io=io, cfg=c)
    plan = o.run_once(window_target="dashboard:0")

    assert plan["columns"] == 3
    assert plan["rows"] == 1
    # タイトル設定はASCII昇順でpaneに割り当て
    assert io.set_window_option_calls[0] == ("dashboard:0", "pane-border-status", "top")
    assert io.set_window_option_calls[1] == ("dashboard:0", "pane-border-format", "#{pane_title}")
    assert io.set_title_calls == [("%1", "alpha"), ("%2", "beta"), ("%3", "gamma")]


def test_layout_recalc_on_resize():
    """幅の変化で列数が変わること。"""
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["a", "b", "c"], width=120, height=40, panes=["%1", "%2", "%3"])
    c = config.load_config(None)
    o = orchestrator.Orchestrator(io=io, cfg=c)
    p1 = o.run_once(window_target="dashboard:0")
    assert p1["columns"] == 3
    # リサイズ
    io._width = 79
    p2 = o.run_once(window_target="dashboard:0")
    assert p2["columns"] == 1


def test_apply_layout_split_calls():
    """C=3, R=2 のとき、水平分割はC-1=2回、垂直分割はC*(R-1)=3回。"""
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["a", "b", "c", "d"], width=120, height=40, panes=["%1", "%2", "%3", "%4"])
    c = config.load_config(None)
    o = orchestrator.Orchestrator(io=io, cfg=c)
    plan = o.compute_plan(window_target="dashboard:0")
    # N=4, W=120, min=40 => C=3, R=2 → target_total=6 → 分割は5回（縦分割のみ）
    assert plan["columns"] == 3 and plan["rows"] == 2
    o.apply_layout(window_target="dashboard:0", columns=plan["columns"], rows=plan["rows"])
    v = [d for d, _ in io.split_calls if d == "v"]
    assert len(v) == 5
