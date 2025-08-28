"""レンダラー中核のテスト。

目的:
- W×H 成形（左基準×下端H行、右端クリップ、ANSI保持、末尾リセット）。
- 行差分検出（変更行のみ）。
- フレームスケジューラ（max_fps、短時間の要求はドロップ）。
"""

from __future__ import annotations


def test_format_lines_bottom_aligned_and_clipped():
    """下端H行が表示され、右端はクリップ、各行末にリセットが付与される。"""
    from tmux_dashboard import renderer

    captured = "line1\nline2\n\x1b[31mREDLINE\x1b[0m\n"
    out = renderer.format_lines(captured, width=5, height=2)
    # 下端2行: line2, REDLI（色開始は保持、見かけ幅は5にクリップ）
    assert len(out) == 2
    assert out[0].endswith("\x1b[0m")
    assert out[1].endswith("\x1b[0m")
    # 幅の検証（見かけ幅は5）
    from tmux_dashboard.utils_wcwidth import visible_width

    assert visible_width(out[0]) == 5 or visible_width(out[0]) == len("line2")
    assert visible_width(out[1]) == 5


def test_format_lines_short_input_fills_top():
    """入力行がH未満の場合、上側に空行を詰めて下に寄せる。"""
    from tmux_dashboard import renderer
    out = renderer.format_lines("only\n", width=10, height=3)
    assert out == ["\x1b[0m", "\x1b[0m", "only\x1b[0m"]


def test_diff_indices_detects_changes():
    """行ごとの差分インデックスが検出される。"""
    from tmux_dashboard import renderer
    prev = ["a\x1b[0m", "b\x1b[0m", "c\x1b[0m"]
    curr = ["a\x1b[0m", "B\x1b[0m", "c\x1b[0m"]
    assert renderer.diff_indices(prev, curr) == [1]


def test_frame_scheduler_respects_max_fps(monkeypatch):
    """frameスケジューラは max_fps を超える頻度の描画要求を抑制する。"""
    from tmux_dashboard import renderer

    t = {"now": 0.0}

    def fake_time():
        return t["now"]

    fs = renderer.FrameScheduler(max_fps=2.0, time_fn=fake_time, drop_stale_frames=True)
    # 最初のフレームは許可
    assert fs.ready() is True
    # 0.2秒後: まだ不可
    t["now"] = 0.2
    assert fs.ready() is False
    # 0.5秒後: 許可
    t["now"] = 0.5
    assert fs.ready() is True
    # 急速に3回要求しても期間内は1回だけ許可
    t["now"] = 0.5
    assert fs.ready() is False
    t["now"] = 0.6
    assert fs.ready() is False
    t["now"] = 1.0
    assert fs.ready() is True

