"""可視幅計算と右端クリップ、SGRリセット補助。

前提:
- ANSIシーケンスは幅0として扱い、原文に保持する。
- 可視幅は `wcwidth` に準拠し、おおむね端末表示と整合させる。
"""

from __future__ import annotations

import re
from typing import Iterable

from wcwidth import wcwidth


# CSI (Control Sequence Introducer) 一般形: ESC [ ... final
CSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _iter_tokens(s: str) -> Iterable[tuple[str, bool]]:
    """テキストをANSI/非ANSIトークンへ分割する。

    戻り値: (token, is_ansi)。`is_ansi=True` は幅0として扱う。
    """
    i = 0
    n = len(s)
    while i < n:
        m = CSI_RE.match(s, i)
        if m:
            yield (m.group(0), True)
            i = m.end()
            continue
        ch = s[i]
        yield (ch, False)
        i += 1


def visible_width(s: str) -> int:
    """ANSIを除外した可視幅（列数）を返す。"""
    width = 0
    for tok, is_ansi in _iter_tokens(s):
        if is_ansi:
            continue
        w = wcwidth(tok)
        if w < 0:
            w = 0
        width += w
    return width


def clip_right(s: str, max_cols: int) -> str:
    """ANSIを保持したまま、可視幅が `max_cols` を超えないよう右端を切る。"""
    if max_cols <= 0:
        # ANSIのみ返す意味は薄いので、空を返す（必要に応じて見直し）
        return ""
    out_parts: list[str] = []
    used = 0
    for tok, is_ansi in _iter_tokens(s):
        if is_ansi:
            out_parts.append(tok)
            continue
        w = wcwidth(tok)
        if w < 0:
            w = 0
        if used + w > max_cols:
            break
        out_parts.append(tok)
        used += w
        if used >= max_cols:
            break
    return "".join(out_parts)


def ensure_reset(s: str) -> str:
    """行末に SGR リセット(\x1b[0m) を確実に付与する。"""
    if s.endswith("\x1b[0m"):
        return s
    return s + "\x1b[0m"
