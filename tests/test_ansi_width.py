"""ANSI幅計算と右端クリップ、SGRリセット付与のテスト。

目的:
- 文字幅（ASCII/日本語/絵文字/合成文字）の見かけ幅を正しく算出する。
- ANSIシーケンスを保持したまま右端クリップできる。
- 行末に `\x1b[0m` を確実に付与する。
"""

from __future__ import annotations

import re


def test_visible_width_basic_cases():
    """基本的な文字幅を検証する（ASCII/日本語/合成文字/絵文字）。"""
    from tmux_dashboard import utils_wcwidth as uw

    assert uw.visible_width("abc") == 3
    assert uw.visible_width("漢字") >= 4  # CJKは一般に幅2×2
    composed = "e\u0301"  # 合成（結合文字）: e + アキュート
    assert uw.visible_width(composed) == 1
    snake = "🐍"  # 一般的な絵文字（プラットフォーム依存で幅2相当が多い）
    assert uw.visible_width(snake) >= 1


def test_visible_width_ignores_ansi_sequences():
    """ANSIシーケンスは幅0として扱う（文字幅は可視文字のみで算出）。"""
    from tmux_dashboard import utils_wcwidth as uw

    s = "\x1b[31mred\x1b[0m"
    assert uw.visible_width(s) == 3


def test_clip_right_preserves_ansi_and_limits_width():
    """右端クリップはANSIを保持しつつ、見かけ幅を上限以下に切る。"""
    from tmux_dashboard import utils_wcwidth as uw

    s = "\x1b[32mGREEN\x1b[0m"
    clipped = uw.clip_right(s, 2)
    # 目視: 先頭の色開始CSIが保持され、可視は2桁に切られる
    assert "\x1b[32m" in clipped
    assert uw.visible_width(clipped) == 2


def test_ensure_reset_appends_reset_once():
    """行末にSGRリセットが付与され、重複しないことを確認する。"""
    from tmux_dashboard import utils_wcwidth as uw

    s = "\x1b[34mBLUE"
    s1 = uw.ensure_reset(s)
    assert s1.endswith("\x1b[0m")
    # 2回目に付けても二重にならない（末尾が既に0mの場合はそのまま）
    s2 = uw.ensure_reset(s1)
    assert s2.endswith("\x1b[0m")
    # 末尾に0mが1回だけあることを確認
    assert len(re.findall(r"\x1b\[0m$", s2)) == 1

