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


def test_tile_positions_column_major_no_empty_cells():
    """列優先でN個だけ位置を返し、空セルを生成しない。"""

    N = 5
    C = 3
    R = 2
    pos = layout.tile_positions(N, C, R)
    assert pos == [
        (0, 0), (1, 0),  # 1列目 上→下
        (0, 1), (1, 1),  # 2列目 上→下
        (0, 2),          # 3列目 上のみ（N=5のためここまで）
    ]
    assert len(pos) == N


def test_progressive_percent_splits_basic():
    """progressive_percent_splits の基本動作を検証する。"""
    
    # 2分割: 100%を50%で分割
    assert layout.progressive_percent_splits(2) == [50]
    
    # 3分割: 100%を33%、残り67%を50%で分割
    assert layout.progressive_percent_splits(3) == [33, 50]
    
    # 4分割: 100%を25%、75%を33%、50%を50%で分割
    assert layout.progressive_percent_splits(4) == [25, 33, 50]
    
    # 5分割: 1/5, 1/4, 1/3, 1/2
    assert layout.progressive_percent_splits(5) == [20, 25, 33, 50]
    
    # 1以下の場合は空リスト
    assert layout.progressive_percent_splits(1) == []
    assert layout.progressive_percent_splits(0) == []


def test_progressive_percent_splits_simulation():
    """progressive_percent_splits で均等な分割ができることをシミュレーションで検証する。"""
    
    def simulate_splits(parts: int):
        """分割をシミュレートして最終的なペインサイズを返す。"""
        if parts <= 1:
            return [100.0] if parts == 1 else []
        
        percentages = layout.progressive_percent_splits(parts)
        panes = [100.0]  # 初期状態
        
        for percent in percentages:
            target_size = panes[-1]
            new_pane = target_size * percent / 100
            remaining = target_size - new_pane
            panes[-1] = remaining
            panes.insert(-1, new_pane)
        
        return panes
    
    # 2分割の検証
    panes_2 = simulate_splits(2)
    assert len(panes_2) == 2
    assert all(abs(p - 50.0) < 0.1 for p in panes_2)  # ほぼ50%ずつ
    
    # 3分割の検証
    panes_3 = simulate_splits(3)
    assert len(panes_3) == 3
    expected_3 = 100.0 / 3
    assert all(abs(p - expected_3) < 1.0 for p in panes_3)  # ほぼ33.3%ずつ
    
    # 4分割の検証
    panes_4 = simulate_splits(4)
    assert len(panes_4) == 4
    expected_4 = 100.0 / 4
    assert all(abs(p - expected_4) < 1.0 for p in panes_4)  # ほぼ25%ずつ
    
    # 5分割の検証
    panes_5 = simulate_splits(5)
    assert len(panes_5) == 5
    expected_5 = 100.0 / 5
    assert all(abs(p - expected_5) < 1.0 for p in panes_5)  # ほぼ20%ずつ
