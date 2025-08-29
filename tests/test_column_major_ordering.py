"""列優先（縦方向優先）配置のテスト。

目的:
- tile_positions が列優先で座標を生成することを検証
- orchestrator が列優先で pane をソートすることを検証
"""

from __future__ import annotations


def test_tile_positions_column_major():
    """列優先（上→下、左→右）で N 個の座標を生成する。"""
    from tmux_dashboard import layout
    
    # 3列×2行で5個のタイル
    N = 5
    C = 3
    R = 2
    
    pos = layout.tile_positions(N, C, R)
    
    # 期待される順序: 列優先
    # 1列目: (0,0), (1,0)
    # 2列目: (0,1), (1,1)
    # 3列目: (0,2) で N=5 に達する
    expected = [
        (0, 0),  # 1列目上
        (1, 0),  # 1列目下
        (0, 1),  # 2列目上
        (1, 1),  # 2列目下
        (0, 2),  # 3列目上（N=5のためここまで）
    ]
    
    assert pos == expected
    assert len(pos) == N


def test_tile_positions_column_major_single_column():
    """1列の場合も正しく動作する。"""
    from tmux_dashboard import layout
    
    N = 3
    C = 1
    R = 3
    
    pos = layout.tile_positions(N, C, R)
    
    expected = [
        (0, 0),
        (1, 0),
        (2, 0),
    ]
    
    assert pos == expected


def test_tile_positions_column_major_single_row():
    """1行の場合も正しく動作する。"""
    from tmux_dashboard import layout
    
    N = 3
    C = 3
    R = 1
    
    pos = layout.tile_positions(N, C, R)
    
    expected = [
        (0, 0),
        (0, 1),
        (0, 2),
    ]
    
    assert pos == expected


def test_orchestrator_pane_sorting_column_major():
    """Orchestrator が pane を列優先（left, top）でソートする。"""
    from tmux_dashboard import orchestrator
    from tmux_dashboard import config
    from dataclasses import dataclass
    
    # モックIO
    @dataclass
    class FakeIO:
        def list_sessions(self):
            return ["alpha", "beta", "gamma"]
        
        def window_size(self, target):
            return (120, 60)
        
        def list_panes_detailed(self, target):
            # pane_id, left, top の順
            # わざとバラバラな順序で返す
            return [
                ("%3", 40, 0),   # 2列目上
                ("%1", 0, 0),    # 1列目上
                ("%4", 40, 30),  # 2列目下
                ("%2", 0, 30),   # 1列目下
                ("%5", 80, 0),   # 3列目上
            ]
        
        def set_window_option(self, target, key, value):
            pass
        
        def set_pane_title(self, pane_id, title):
            self.titles.append((pane_id, title))
        
        def __post_init__(self):
            self.titles = []
    
    cfg = config.load_config(None)
    cfg.min_tile_width = 40
    io = FakeIO()
    orch = orchestrator.Orchestrator(io, cfg)
    
    # apply_titles を呼び出す
    orch.apply_titles("dashboard:0", ["alpha", "beta", "gamma", "delta", "epsilon"])
    
    # 期待される順序: 列優先（left優先、次にtop）
    # left=0: %1(top=0), %2(top=30)
    # left=40: %3(top=0), %4(top=30)
    # left=80: %5(top=0)
    expected_order = [
        ("%1", "alpha"),    # 1列目上
        ("%2", "beta"),     # 1列目下
        ("%3", "gamma"),    # 2列目上
        ("%4", "delta"),    # 2列目下
        ("%5", "epsilon"),  # 3列目上
    ]
    
    assert io.titles == expected_order