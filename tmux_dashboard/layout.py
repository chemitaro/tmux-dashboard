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

    columns = max(1, min(N, floor(W / min_tile_width)))
    """
    if min_tile_width <= 0:
        return max(1, session_count)
    raw = window_width // min_tile_width
    cols = max(1, min(session_count, raw))
    return cols


def calc_rows(session_count: int, columns: int) -> int:
    """行数を計算する（ceil(N / columns)）。"""
    columns = max(1, columns)
    return ceil(session_count / columns) if session_count > 0 else 1


def percent_splits(parts: int) -> List[int]:
    """百分率の分割配列を返す。末尾で端数を吸収し、合計100にする。"""
    parts = max(1, parts)
    base = floor(100 / parts)
    arr = [base] * parts
    # 端数を最後に加算
    arr[-1] = 100 - base * (parts - 1)
    return arr


def tile_positions(n: int, columns: int, rows: int) -> List[Tuple[int, int]]:
    """行優先（左→右、上→下）で N 個の (row, col) を返す。空セルは含めない。"""
    out: List[Tuple[int, int]] = []
    count = 0
    for r in range(rows):
        for c in range(columns):
            if count >= n:
                return out
            out.append((r, c))
            count += 1
    return out

