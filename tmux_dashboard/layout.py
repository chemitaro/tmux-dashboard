"""レイアウト計算ユーティリティ。

機能:
- 列/行数の決定
- 百分率分割（末尾で端数吸収）
- 行優先マッピング（左→右、上→下）でN個のタイル位置を返す
"""

from __future__ import annotations

from math import ceil, floor
from typing import List, Tuple


def calc_columns(window_width: int, min_tile_width: int, session_count: int) -> int:
    """列数を計算する。

    仕様: `max(1, min(N, floor(W / min_tile_width)))`
    """
    if min_tile_width <= 0:
        return max(1, session_count)
    raw = window_width // min_tile_width
    cols = max(1, min(session_count, raw))
    return cols


def calc_rows(session_count: int, columns: int) -> int:
    """行数を計算する（`ceil(N / columns)`）。"""
    columns = max(1, columns)
    return ceil(session_count / columns) if session_count > 0 else 1


def percent_splits(parts: int) -> List[int]:
    """百分率の分割配列を返す。

    各要素は整数％。末尾で端数を吸収し、合計100を保証する。
    """
    parts = max(1, parts)
    base = floor(100 / parts)
    arr = [base] * parts
    # 端数を最後に加算
    arr[-1] = 100 - base * (parts - 1)
    return arr


def progressive_percent_splits(parts: int) -> List[int]:
    """tmux split-windowコマンド用の累進的なパーセント配列を返す。
    
    各分割ステップで、残りのペインを均等に分割するための
    正しいパーセンテージを計算する。
    
    Args:
        parts: 分割する総数（2以上）
    
    Returns:
        各分割ステップで使用するパーセンテージのリスト
        （最後の分割は不要なので、長さは parts-1）
    
    Examples:
        >>> progressive_percent_splits(2)
        [50]  # 2分割: 100%を50%で分割
        
        >>> progressive_percent_splits(3)
        [33, 50]  # 3分割: 100%を33%、残り67%を50%で分割
        
        >>> progressive_percent_splits(4)
        [25, 33, 50]  # 4分割: 100%を25%、75%を33%、50%を50%で分割
        
        >>> progressive_percent_splits(5)
        [20, 25, 33, 50]  # 5分割: 1/5, 1/4, 1/3, 1/2
    """
    if parts <= 1:
        return []
    
    percentages = []
    for i in range(parts - 1):
        # i番目の分割では、残り(parts - i)個に分割する
        # そのうち1個を新しいペインにするので、1/(parts - i)
        remaining_parts = parts - i
        percent = 100 // remaining_parts
        percentages.append(percent)
    
    return percentages


def tile_positions(n: int, columns: int, rows: int) -> List[Tuple[int, int]]:
    """行優先（左→右、上→下）で N 個の (row, col) を返す。

    空セルは生成せず、N 個に達した時点で終了する。
    """
    out: List[Tuple[int, int]] = []
    count = 0
    for r in range(rows):
        for c in range(columns):
            if count >= n:
                return out
            out.append((r, c))
            count += 1
    return out
