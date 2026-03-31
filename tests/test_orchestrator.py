"""オーケストレータのテスト。

目的:
- staging window を使った non-destructive apply の挙動を確認する。
- pane 数不足の明示失敗、integrity 判定順序、0セッション正常終了を確認する。
"""

from __future__ import annotations

from unittest.mock import Mock


class FakeIO:
    """Orchestrator テスト用の最小 tmux I/O フェイク。"""

    def __init__(self, sessions, width, height, panes):
        self._sessions = sessions
        self._width = width
        self._height = height
        self.set_window_option_calls = []
        self.get_window_option_calls = []
        self.set_title_calls = []
        self.split_calls = []
        self.kill_calls = 0
        self.create_window_calls = []
        self.swap_window_calls = []
        self.kill_window_calls = []
        self.rename_window_calls = []
        self.respawn_calls = []

        self.fail_split_for_targets = set()
        self.freeze_split_growth_for_targets = set()
        self.fail_title_for_targets = set()
        self.flip_title_once_for_targets = set()
        self.fail_kill_window_targets = set()
        self.fail_create_window_targets = set()
        self.partial_create_window_targets = set()
        self.fail_swap_window_pairs = set()
        self.overwrite_title_on_respawn = False

        self._details_by_window = {}
        self._pane_to_window = {}
        self._pane_titles = {}
        self._window_options = {}
        self._window_names = {}
        self._next_pane_num = 100

        self._init_window("dashboard:0", panes)

    def _init_window(self, window_target: str, pane_ids: list[str]):
        details = []
        for idx, pane_id in enumerate(pane_ids):
            details.append((pane_id, idx * 40, 0))
            self._pane_to_window[pane_id] = window_target
            self._pane_titles.setdefault(pane_id, "")
        self._details_by_window[window_target] = details
        self._window_options.setdefault(window_target, {"window-size": "manual"})
        self._window_names.setdefault(window_target, "dashboard" if window_target == "dashboard:0" else "python3.12")

    def _new_pane_id(self) -> str:
        self._next_pane_num += 1
        return f"%{self._next_pane_num}"

    def _append_pane(self, window_target: str, left: int, top: int):
        pane_id = self._new_pane_id()
        self._details_by_window.setdefault(window_target, []).append((pane_id, left, top))
        self._pane_to_window[pane_id] = window_target
        self._pane_titles[pane_id] = ""
        return pane_id

    def _session_of_target(self, window_target: str) -> str:
        return window_target.split(":", 1)[0]

    def list_sessions(self):
        return list(self._sessions)

    def window_size(self, window_target: str):
        return self._width, self._height

    def list_panes(self, window_target: str):
        return [pid for pid, _, _ in self._details_by_window.get(window_target, [])]

    def list_panes_detailed(self, window_target: str):
        return list(self._details_by_window.get(window_target, []))

    def set_window_option(self, window_target: str, key: str, value: str):
        self.set_window_option_calls.append((window_target, key, value))
        self._window_options.setdefault(window_target, {})[key] = value

    def get_window_option(self, window_target: str, key: str):
        self.get_window_option_calls.append((window_target, key))
        return self._window_options.get(window_target, {}).get(key, "")

    def set_pane_title(self, pane_id: str, title: str):
        self.set_title_calls.append((pane_id, title))
        self._pane_titles[pane_id] = title

    def kill_other_panes(self, window_target: str):
        self.kill_calls += 1
        details = self._details_by_window.get(window_target, [])
        if not details:
            return
        keep = details[:1]
        for pid, _, _ in details[1:]:
            self._pane_to_window.pop(pid, None)
            self._pane_titles.pop(pid, None)
        self._details_by_window[window_target] = keep

    def split_window(
        self,
        window_target: str,
        direction: str,
        length: str | int | None = None,
        *,
        percent: int | None = None,
    ):
        self.split_calls.append((window_target, direction, length, percent))
        if window_target in self.fail_split_for_targets:
            raise RuntimeError("forced split failure")
        if window_target in self.freeze_split_growth_for_targets:
            return
        details = self._details_by_window.get(window_target, [])
        if not details:
            self._append_pane(window_target, 0, 0)
            return
        if direction == "h":
            left = max(x[1] for x in details) + 40
            top = 0
        else:
            left = details[0][1]
            top = max(x[2] for x in details) + 10
        self._append_pane(window_target, left, top)

    def select_pane(self, pane_id: str):
        return None

    def split_pane(
        self,
        pane_id: str,
        direction: str,
        length: str | int | None = None,
        *,
        percent: int | None = None,
    ):
        window_target = self._pane_to_window[pane_id]
        self.split_calls.append((window_target, direction, length, percent))
        if window_target in self.fail_split_for_targets:
            raise RuntimeError("forced split failure")
        if window_target in self.freeze_split_growth_for_targets:
            return
        details = self._details_by_window.get(window_target, [])
        base = next((x for x in details if x[0] == pane_id), details[0])
        if direction == "v":
            left = base[1]
            top = max(x[2] for x in details if x[1] == left) + 10
        else:
            left = max(x[1] for x in details) + 40
            top = base[2]
        self._append_pane(window_target, left, top)

    def list_panes_with_titles(self, window_target: str):
        if window_target in self.fail_title_for_targets:
            raise RuntimeError("forced title fetch failure")
        rows = [(pid, self._pane_titles.get(pid, "")) for pid, _, _ in self._details_by_window.get(window_target, [])]
        if window_target in self.flip_title_once_for_targets and rows:
            self.flip_title_once_for_targets.remove(window_target)
            wrong_title = "__transient_mismatch__"
            rows = [(rows[0][0], wrong_title), *rows[1:]]
        return rows

    def list_windows_with_active(self, session_name: str):
        indexes = []
        for target in self._details_by_window:
            sess, idx = target.split(":", 1)
            if sess == session_name:
                indexes.append(int(idx))
        indexes.sort()
        return [(idx, 1 if idx == 0 else 0) for idx in indexes]

    def create_window(
        self,
        session_name: str,
        window_index: int,
        detached: bool = True,
        *,
        width: int | None = None,
        height: int | None = None,
        window_name: str | None = None,
    ):
        target = f"{session_name}:{window_index}"
        self.create_window_calls.append((session_name, window_index, detached, width, height, window_name))
        if target in self.fail_create_window_targets:
            raise RuntimeError("forced create-window failure")
        if target in self._details_by_window:
            raise RuntimeError("window already exists")
        self._init_window(target, [self._new_pane_id()])
        if window_name is not None:
            self._window_names[target] = window_name
        if target in self.partial_create_window_targets:
            raise RuntimeError("forced create-window post-create failure")
        return target

    def swap_window(self, source_target: str, destination_target: str):
        self.swap_window_calls.append((source_target, destination_target))
        if (source_target, destination_target) in self.fail_swap_window_pairs:
            raise RuntimeError("forced swap-window failure")
        src = self._details_by_window[source_target]
        dst = self._details_by_window[destination_target]
        src_name = self._window_names[source_target]
        dst_name = self._window_names[destination_target]
        self._details_by_window[source_target], self._details_by_window[destination_target] = dst, src
        self._window_names[source_target], self._window_names[destination_target] = dst_name, src_name
        for pid, _, _ in self._details_by_window[source_target]:
            self._pane_to_window[pid] = source_target
        for pid, _, _ in self._details_by_window[destination_target]:
            self._pane_to_window[pid] = destination_target

    def rename_window(self, window_target: str, window_name: str):
        self.rename_window_calls.append((window_target, window_name))
        self._window_names[window_target] = window_name

    def kill_window(self, window_target: str):
        self.kill_window_calls.append(window_target)
        if window_target in self.fail_kill_window_targets:
            raise RuntimeError("forced kill-window failure")
        removed = self._details_by_window.pop(window_target, [])
        self._window_names.pop(window_target, None)
        for pid, _, _ in removed:
            self._pane_to_window.pop(pid, None)
            self._pane_titles.pop(pid, None)

    def resolve_best_pane(self, session_name: str):
        return f"{session_name}:0.0"

    def respawn_pane(self, pane_id: str, argv):
        self.respawn_calls.append((pane_id, list(argv)))
        if self.overwrite_title_on_respawn:
            self._pane_titles[pane_id] = "node@host"


def test_scan_sort_exclude_and_titles_and_layout():
    """目的: run_once でセッション並び替え・レイアウト適用・タイトル設定を確認する。
    前提: dashboard 以外に 3 セッションが存在する。
    期待: ASCII昇順でタイトルが設定され、計画の列/行が期待通りになる。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(
        sessions=["gamma", "dashboard", "alpha", "beta"],
        width=120,
        height=50,
        panes=["%1", "%2", "%3"],
    )
    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)
    plan = o.run_once(window_target="dashboard:0")

    assert plan["columns"] == 3
    assert plan["rows"] == 1
    assert sorted({title for _, title in io.set_title_calls}) == ["alpha", "beta", "gamma"]
    assert io.swap_window_calls == [("dashboard:99", "dashboard:0")]
    assert io.create_window_calls == [("dashboard", 99, True, 120, 50, "__tmux_dashboard_staging__99")]


def test_run_once_restores_visible_dashboard_window_name_after_swap():
    """目的: swap 後に visible dashboard window 名 invariant を回復することを確認する。
    前提: staging window は一時名で作られ、swap により visible target がその名前を受け取る。
    期待: old window を退避名へ rename し、新しい visible target は `dashboard` へ rename される。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(
        sessions=["gamma", "dashboard", "alpha", "beta"],
        width=120,
        height=50,
        panes=["%1", "%2", "%3"],
    )
    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)

    o.run_once(window_target="dashboard:0")

    assert io.rename_window_calls[1:3] == [
        ("dashboard:99", "__tmux_dashboard_old__99"),
        ("dashboard:0", "dashboard"),
    ]
    assert io.kill_window_calls == ["dashboard:99"]
    assert io._window_names["dashboard:0"] == "dashboard"


def test_apply_layout_split_calls_and_result():
    """目的: apply_layout が結果オブジェクトを返し、分割を実行することを確認する。
    前提: 4 セッション相当の列/行を与える。
    期待: success=True かつ水平/垂直分割が記録される。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["a", "b", "c", "d"], width=120, height=40, panes=["%1", "%2", "%3", "%4"])
    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)
    result = o.apply_layout(window_target="dashboard:0", columns=3, rows=2)

    assert result.success is True
    h = [x for x in io.split_calls if x[1] == "h"]
    v = [x for x in io.split_calls if x[1] == "v"]
    assert len(h) == 2
    assert len(v) >= 1


def test_apply_layout_uses_given_sessions_without_rescan():
    """目的: apply_layout が引数 sessions を優先し再スキャンしないことを確認する。
    前提: scan_sessions を呼ぶと失敗するようにする。
    期待: 例外なく success=True で分割処理が完了する。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["a", "b", "c"], width=120, height=40, panes=["%1", "%2", "%3"])
    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)
    o.scan_sessions = lambda: (_ for _ in ()).throw(AssertionError("scan_sessions must not be called"))  # type: ignore[method-assign]

    result = o.apply_layout(
        window_target="dashboard:0",
        columns=3,
        rows=1,
        sessions=["a", "b", "c"],
    )
    assert result.success is True


def test_run_once_preserves_dashboard_on_staging_failure():
    """目的: staging で分割失敗しても既存 dashboard を保持することを確認する。
    前提: staging target で split が例外になる。
    期待: swap は実行されず、staging のみ cleanup され、dashboard:0 は維持される。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["dashboard", "a", "b"], width=120, height=40, panes=["%1", "%2"])
    io.fail_split_for_targets.add("dashboard:99")
    original = io.list_panes("dashboard:0")

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)
    _ = o.run_once(window_target="dashboard:0")

    assert io.swap_window_calls == []
    assert "dashboard:99" in io.kill_window_calls
    assert io.list_panes("dashboard:0") == original


def test_run_once_logs_explicit_error_when_create_window_fails():
    """目的: staging window 作成失敗を explicit な error ログで観測し、dashboard を保持することを確認する。
    前提: create_window が例外を送出する。
    期待: swap は実行されず、dashboard:0 は不変で create-window failed を含む error ログが残る。
    かつ、実在しない predicted staging target は cleanup / residual retry 対象にしない。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config
    import logging

    io = FakeIO(sessions=["dashboard", "a", "b"], width=120, height=40, panes=["%1", "%2"])
    io.fail_create_window_targets.add("dashboard:99")
    original = io.list_panes("dashboard:0")

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)

    fake_logger = Mock()
    fake_logger.info.return_value = None
    fake_logger.error.return_value = None
    fake_logger.warning.return_value = None

    original_get_logger = logging.getLogger
    logging.getLogger = lambda _name: fake_logger  # type: ignore[assignment]
    try:
        _ = o.run_once(window_target="dashboard:0")
    finally:
        logging.getLogger = original_get_logger  # type: ignore[assignment]

    assert io.swap_window_calls == []
    assert io.kill_window_calls == []
    assert io.list_panes("dashboard:0") == original
    assert o._residual_window_target is None
    errors = [call.args[0] % call.args[1:] for call in fake_logger.error.call_args_list]
    assert any("create-window failed" in message for message in errors)


def test_run_once_cleans_predicted_staging_target_when_create_window_fails_after_partial_create():
    """目的: create_window の post-create failure 時でも予測 staging target を cleanup することを確認する。
    前提: create_window が window を作成した後に例外を送出する。
    期待: predicted staging target に対して kill_window が呼ばれ、半端な staging window が残らない。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["dashboard", "a", "b"], width=120, height=40, panes=["%1", "%2"])
    io.partial_create_window_targets.add("dashboard:99")

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)
    _ = o.run_once(window_target="dashboard:0")

    assert io.swap_window_calls == []
    assert io.kill_window_calls == ["dashboard:99"]
    assert "dashboard:99" not in io._details_by_window
    assert o._residual_window_target is None


def test_run_once_logs_warning_when_staging_cleanup_fails():
    """目的: staging cleanup が失敗した場合に warning ログを残すことを確認する。
    前提: staging で分割失敗し、続く kill_window も失敗する。
    期待: cleanup 失敗を warning で観測でき、run_once は例外化しない。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config
    import logging

    io = FakeIO(sessions=["dashboard", "a", "b"], width=120, height=40, panes=["%1", "%2"])
    io.fail_split_for_targets.add("dashboard:99")
    io.fail_kill_window_targets.add("dashboard:99")

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)

    fake_logger = Mock()
    fake_logger.info.return_value = None
    fake_logger.error.return_value = None
    fake_logger.warning.return_value = None

    original_get_logger = logging.getLogger
    logging.getLogger = lambda _name: fake_logger  # type: ignore[assignment]
    try:
        _ = o.run_once(window_target="dashboard:0")
    finally:
        logging.getLogger = original_get_logger  # type: ignore[assignment]

    warnings = [call.args[0] % call.args[1:] for call in fake_logger.warning.call_args_list]
    assert any("failed to cleanup staging window" in message for message in warnings)


def test_run_once_logs_explicit_error_and_cleans_staging_when_swap_fails():
    """目的: swap-window 失敗を explicit な error ログで観測し、dashboard を保持することを確認する。
    前提: staging 構築は成功するが swap_window が例外を送出する。
    期待: dashboard:0 は不変で、staging は cleanup され、swap-window failed を含む error ログが残る。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config
    import logging

    io = FakeIO(sessions=["dashboard", "a", "b"], width=120, height=40, panes=["%1", "%2"])
    io.fail_swap_window_pairs.add(("dashboard:99", "dashboard:0"))
    original = io.list_panes("dashboard:0")

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)

    fake_logger = Mock()
    fake_logger.info.return_value = None
    fake_logger.error.return_value = None
    fake_logger.warning.return_value = None

    original_get_logger = logging.getLogger
    logging.getLogger = lambda _name: fake_logger  # type: ignore[assignment]
    try:
        _ = o.run_once(window_target="dashboard:0")
    finally:
        logging.getLogger = original_get_logger  # type: ignore[assignment]

    assert io.swap_window_calls == [("dashboard:99", "dashboard:0")]
    assert io.kill_window_calls == ["dashboard:99"]
    assert io.list_panes("dashboard:0") == original
    errors = [call.args[0] % call.args[1:] for call in fake_logger.error.call_args_list]
    assert any("swap-window failed" in message for message in errors)


def test_run_once_retries_residual_cleanup_without_blocking_new_layout():
    """目的: swap後 cleanup 失敗の残置 window を次サイクルで再cleanupしつつ、新規 apply を妨げないことを確認する。
    前提: 1回目は swap 後の kill_window が失敗し、2回目は residual cleanup が成功する。
    期待: residual target が再試行後に消え、後続の run_once は追加の staging 作成なしで正常終了する。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["dashboard", "alpha", "beta"], width=120, height=40, panes=["%1", "%2"])
    io.fail_kill_window_targets.add("dashboard:99")

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)

    first_plan = o.run_once(window_target="dashboard:0")
    assert o._residual_window_target == "dashboard:99"
    assert io.kill_window_calls == ["dashboard:99"]

    io.fail_kill_window_targets.remove("dashboard:99")
    _ = o.run_once(window_target="dashboard:0")

    assert first_plan["sessions"] == ["alpha", "beta"]
    assert o._residual_window_target is None
    assert io.kill_window_calls == ["dashboard:99", "dashboard:99"]
    assert len(io.create_window_calls) == 1


def test_run_once_logs_retry_cleanup_failure_and_still_relayouts():
    """目的: residual cleanup の再失敗を warning で観測しつつ、新しい staging で再レイアウト継続することを確認する。
    前提: 1回目で旧 window cleanup が失敗し、2回目冒頭の residual retry も再失敗する。
    期待: retry failure を warning で記録し、次サイクルでは別 index の staging window を作って relayout を継続する。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config
    import logging

    io = FakeIO(sessions=["dashboard", "alpha", "beta"], width=120, height=40, panes=["%1", "%2"])
    io.fail_kill_window_targets.add("dashboard:99")

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)

    fake_logger = Mock()
    fake_logger.info.return_value = None
    fake_logger.error.return_value = None
    fake_logger.warning.return_value = None

    original_get_logger = logging.getLogger
    logging.getLogger = lambda _name: fake_logger  # type: ignore[assignment]
    try:
        _ = o.run_once(window_target="dashboard:0")
        io._sessions.append("gamma")
        _ = o.run_once(window_target="dashboard:0")
    finally:
        logging.getLogger = original_get_logger  # type: ignore[assignment]

    warnings = [call.args[0] % call.args[1:] for call in fake_logger.warning.call_args_list]
    assert any("failed to retry residual window cleanup" in message for message in warnings)
    assert [call[1] for call in io.create_window_calls] == [99, 100]
    assert io.swap_window_calls == [("dashboard:99", "dashboard:0"), ("dashboard:100", "dashboard:0")]
    assert io.kill_window_calls == ["dashboard:99", "dashboard:99", "dashboard:100"]
    assert o._residual_window_target == "dashboard:99"
    titles = {title for _, title in io.list_panes_with_titles("dashboard:0")}
    assert titles == {"alpha", "beta", "gamma"}


def test_run_once_keeps_older_residual_pending_while_preserving_newer_cleanup_failure():
    """目的: 古い residual を優先再試行しつつ、新たな cleanup failure も失わないことを確認する。
    前提: 1回目で dashboard:99 が residual 化し、2回目は 99 の retry が失敗したまま 100 も cleanup 失敗する。
    期待: pending residual は [99, 100] の順で保持され、99 解消後も 100 が次の retry 対象として残る。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["dashboard", "alpha", "beta"], width=120, height=40, panes=["%1", "%2"])
    io.fail_kill_window_targets.add("dashboard:99")

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)

    _ = o.run_once(window_target="dashboard:0")
    io._sessions.append("gamma")
    io.fail_kill_window_targets.add("dashboard:100")
    _ = o.run_once(window_target="dashboard:0")

    assert o._residual_window_targets == ["dashboard:99", "dashboard:100"]

    io.fail_kill_window_targets.remove("dashboard:99")
    _ = o.run_once(window_target="dashboard:0")

    assert o._residual_window_targets == ["dashboard:100"]
    assert o._residual_window_target == "dashboard:100"
    assert io.kill_window_calls == ["dashboard:99", "dashboard:99", "dashboard:100", "dashboard:99"]


def test_run_once_detects_pane_shortage_without_silent_zip():
    """目的: pane 数不足を明示失敗として扱うことを確認する。
    前提: staging 側で split 成長を無効化し pane 数を増やせない。
    期待: swap を行わず失敗扱いとなり、既存 dashboard を維持する。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["dashboard", "a", "b", "c"], width=120, height=40, panes=["%1", "%2", "%3"])
    io.freeze_split_growth_for_targets.add("dashboard:99")
    original = io.list_panes("dashboard:0")

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)
    _ = o.run_once(window_target="dashboard:0")

    assert io.swap_window_calls == []
    assert "dashboard:99" in io.kill_window_calls
    assert io.list_panes("dashboard:0") == original


def test_run_once_ignores_staging_title_fetch_failure_for_swap():
    """目的: staging 昇格判定が title 依存でないことを確認する。
    前提: staging target の list_panes_with_titles が例外を送出する。
    期待: 構造整合が満たされていれば swap は実行される。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["dashboard", "a", "b"], width=120, height=40, panes=["%1", "%2"])
    io.fail_title_for_targets.add("dashboard:99")
    original = io.list_panes("dashboard:0")

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)
    _ = o.run_once(window_target="dashboard:0")

    assert io.swap_window_calls == [("dashboard:99", "dashboard:0")]
    assert "dashboard:99" in io.kill_window_calls
    assert io.list_panes("dashboard:0") != original


def test_integrity_check_order_avoids_initial_noise():
    """目的: initial integrity ノイズを避ける呼び出し順を確認する。
    前提: 同一 signature で 2 回 run_once を実行する。
    期待: 1 回目は swap 後に strict 評価、2 回目は active window で通常評価される。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["dashboard", "alpha", "beta"], width=120, height=40, panes=["%1", "%2"])
    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)

    called_calls = []

    def fake_check(target, strict=False, invalidate_signature=True):
        called_calls.append((target, strict, invalidate_signature))
        return False

    o.check_pane_integrity = fake_check  # type: ignore[method-assign]
    _ = o.run_once(window_target="dashboard:0")
    _ = o.run_once(window_target="dashboard:0")

    assert called_calls[0] == ("dashboard:0", True, False)
    assert called_calls[1] == ("dashboard:0", False, True)
    assert len(called_calls) == 2


def test_zero_sessions_keeps_single_pane_and_returns_normally():
    """目的: 0セッション時の正常終了を確認する。
    前提: dashboard 以外のセッションが存在しない。
    期待: 単一pane維持のみ実行し、staging 操作や respawn は発生しない。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["dashboard"], width=120, height=40, panes=["%1", "%2"])
    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)
    plan = o.run_once(window_target="dashboard:0")

    assert plan["sessions"] == []
    assert len(io.list_panes("dashboard:0")) == 1
    assert io.create_window_calls == []
    assert io.swap_window_calls == []
    assert io.respawn_calls == []


def test_zero_sessions_clear_stale_single_pane_title():
    """目的: 0セッション short-circuit 後に stale pane title を残さないことを確認する。
    前提: 直前まで複数セッション名が pane_title に設定されている。
    期待: dashboard:0 は単一 pane へ収束し、残った pane_title は空文字になる。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["dashboard"], width=120, height=40, panes=["%1", "%2"])
    io.set_pane_title("%1", "alpha")
    io.set_pane_title("%2", "beta")

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)
    plan = o.run_once(window_target="dashboard:0")

    assert plan["sessions"] == []
    assert io.list_panes("dashboard:0") == ["%1"]
    assert io.list_panes_with_titles("dashboard:0") == [("%1", "")]


def test_run_once_ensures_window_size_latest_in_preflight():
    """目的: run_once の preflight で window-size manual を latest に是正することを確認する。
    前提: dashboard:0 の window-size が manual になっている。
    期待: run_once 実行後に dashboard 名と automatic-rename off と window-size latest が揃う。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["dashboard", "alpha", "beta"], width=120, height=40, panes=["%1", "%2"])
    io._window_options["dashboard:0"]["window-size"] = "manual"

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)
    _ = o.run_once(window_target="dashboard:0")

    assert io.get_window_option("dashboard:0", "window-size") == "latest"
    assert io.rename_window_calls[0] == ("dashboard:0", "dashboard")
    assert ("dashboard:0", "automatic-rename", "off") in io.set_window_option_calls
    assert ("dashboard:0", "window-size", "latest") in io.set_window_option_calls


def test_ensure_dashboard_window_policy_is_non_intrusive_for_non_dashboard_target():
    """目的: non-dashboard target では window-size policy 是正を行わないことを確認する。
    前提: `alpha:0` を run target として扱う。
    期待: get/set の window-size 操作は呼ばれない。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(
        sessions=["dashboard", "alpha", "beta"],
        width=120,
        height=40,
        panes=["%1", "%2"],
    )
    io._init_window("alpha:0", ["%8", "%9"])
    io._window_options["alpha:0"]["window-size"] = "manual"

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)
    o.ensure_dashboard_window_policy("alpha:0")

    assert ("alpha:0", "window-size") not in io.get_window_option_calls
    assert io.rename_window_calls == []
    assert ("alpha:0", "automatic-rename", "off") not in io.set_window_option_calls
    assert ("alpha:0", "window-size", "latest") not in io.set_window_option_calls


def test_run_once_reapplies_titles_after_respawn_overwrite():
    """目的: respawn が pane_title を上書きしても最終タイトルをセッション名に戻すことを確認する。
    前提: respawn 実行時に FakeIO がタイトルを `node@host` に上書きする。
    期待: run_once 後の dashboard:0 の pane_title はセッション名集合と一致する。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["dashboard", "alpha", "beta"], width=120, height=40, panes=["%1", "%2"])
    io.overwrite_title_on_respawn = True

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)
    _ = o.run_once(window_target="dashboard:0")

    titles = {title for _, title in io.list_panes_with_titles("dashboard:0")}
    assert titles == {"alpha", "beta"}


def test_run_once_keeps_signature_when_post_respawn_mismatch_recovers():
    """目的: post-respawn の一時的不整合復旧時に signature を無効化しないことを確認する。
    前提: dashboard:0 のタイトル取得が1回だけ不一致を返し、その後は通常値へ戻る。
    期待: 2回目の run_once で不要な再レイアウト（staging 作成）が発生しない。
    """
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config

    io = FakeIO(sessions=["dashboard", "alpha", "beta"], width=120, height=40, panes=["%1", "%2"])
    io.flip_title_once_for_targets.add("dashboard:0")
    io.overwrite_title_on_respawn = True

    c = config.Config()
    o = orchestrator.Orchestrator(io=io, cfg=c)

    first_plan = o.run_once(window_target="dashboard:0")
    expected_signature = (
        first_plan["columns"],
        first_plan["rows"],
        tuple(first_plan["sessions"]),
    )
    assert o._last_signature == expected_signature
    assert len(io.create_window_calls) == 1

    _ = o.run_once(window_target="dashboard:0")
    assert len(io.create_window_calls) == 1
