"""レンダラー中核。

機能:
- `format_lines`: capture-pane の出力を W×H に整形（左基準×下端H行、右端クリップ、ANSI保持、行末リセット）。
- `diff_indices`: 2つの行配列の差分（変更インデックス）を返す。
- `FrameScheduler`: max_fps に基づく描画スケジューリング（短時間リクエストの抑制）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .utils_wcwidth import clip_right, ensure_reset


def format_lines(captured: str, width: int, height: int) -> List[str]:
    """capture-pane の文字列を W×H 行へ整形して返す。

    - 下端H行: 入力の末尾から H 行を採用。H 未満なら上部を空行で満たす。
    - 右端クリップ: 可視幅が `width` を超える場合は `clip_right` を適用。
    - ANSI保持: 色などは保持するが、行末に `\x1b[0m` を付与してリセットする。
    """
    raw_lines = captured.splitlines()
    # 末尾から height 行を取る
    tail = raw_lines[-height:] if height > 0 else []
    # 上詰め（空行で埋める）
    if len(tail) < height:
        pad = [""] * (height - len(tail))
        tail = pad + tail

    out: List[str] = []
    for line in tail:
        clipped = clip_right(line, width)
        out.append(ensure_reset(clipped))
    return out


def diff_indices(prev: List[str], curr: List[str]) -> List[int]:
    """2つの行配列の差分インデックスを返す。長さ不一致にも対応。"""
    n = max(len(prev), len(curr))
    changed: List[int] = []
    for i in range(n):
        a = prev[i] if i < len(prev) else None
        b = curr[i] if i < len(curr) else None
        if a != b:
            changed.append(i)
    return changed


@dataclass
class FrameScheduler:
    """描画フレームのスケジューラ。

    max_fps: 秒間最大描画回数。
    drop_stale_frames: 短時間に連続要求が来ても、期間内は描画を抑制（実質古い要求をドロップ）。
    """

    max_fps: float = 30.0
    time_fn: callable = None  # type: ignore[assignment]
    drop_stale_frames: bool = True

    def __post_init__(self):
        if self.time_fn is None:
            import time

            self.time_fn = time.monotonic
        self._last_render_at = -1e9
        self._period = 1.0 / self.max_fps if self.max_fps > 0 else 0.0

    def ready(self) -> bool:
        """現在時刻で描画してよいか判定し、許可時は内部時刻を更新する。"""
        now = float(self.time_fn())
        if self._period <= 0:
            self._last_render_at = now
            return True
        if now - self._last_render_at >= self._period:
            self._last_render_at = now
            return True
        return False

