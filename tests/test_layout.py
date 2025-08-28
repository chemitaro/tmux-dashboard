"""レイアウト計算（列数/行数/分割比率/行優先マッピング）のテスト。

目的:
- columns/rows の計算が仕様どおり（代表ケースA〜Hに一致）。
- 分割比率は末尾吸収で合計100%になる。
- タイルの配置は行優先（左→右，上→下）で空セルを生成しない。
"""

from __future__ import annotations

from math import floor
from tmux_dashboard import layout


def test_columns_rows_cases():
    """代表ケースA〜Hの columns と rows を検証する。"""

    cases = [
        # (W, min, N, expC, expR)
        (120, 40, 3, 3, 1),  # A
        (120, 40, 4, 3, 2),  # B
        (79, 40, 2, 1, 2),   # C
        (200, 60, 5, 3, 2),  # D
        (200, 100, 3, 2, 2), # E
        (160, 45, 7, 3, 3),  # F
        (120, 40, 1, 1, 1),  # G
        (30, 40, 4, 1, 4),   # H
    ]

    for W, m, N, expC, expR in cases:
        C = layout.calc_columns(W, m, N)
        R = layout.calc_rows(N, C)
        assert C == expC
        assert R == expR


def test_percent_splits_sum_to_100():
    """分割比率は末尾吸収で合計100%（列/行）になる。"""

    cols = layout.percent_splits(3)
    assert cols[:-1] == [floor(100 / 3)] * 2
    assert sum(cols) == 100

    rows = layout.percent_splits(2)
    assert rows == [50, 50]
    assert sum(rows) == 100

    rows3 = layout.percent_splits(3)
    assert rows3[:-1] == [33, 33]
    assert rows3[-1] == 34
    assert sum(rows3) == 100


def test_tile_positions_row_major_no_empty_cells():
    """行優先でN個だけ位置を返し、空セルを生成しない。"""

    N = 5
    C = 3
    R = 2
    pos = layout.tile_positions(N, C, R)
    assert pos == [
        (0, 0), (0, 1), (0, 2),  # 1段目 左→右
        (1, 0), (1, 1),          # 2段目 左→右（N=5のためここまで）
    ]
    assert len(pos) == N
