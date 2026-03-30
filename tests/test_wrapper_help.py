"""ラッパースクリプト `tmux-dashboard` のヘルプ出力を検証するテスト。

目的:
- 利用者が wrapper と runner の引数境界を誤解しない文言を維持する。
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_wrapper_help_shows_wrapper_and_runner_options():
    """`tmux-dashboard -h` の文言整合を確認する。

    前提: リポジトリ直下の `tmux-dashboard` が実行可能である。
    期待: wrapper 固有引数と runner 主要オプション案内が同時に表示される。
    """
    script = Path(__file__).resolve().parents[1] / "tmux-dashboard"
    proc = subprocess.run([str(script), "-h"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout

    out = proc.stdout
    assert "Usage:" in out
    assert "tmux-dashboard [--config PATH]" in out
    assert "-h, --help" in out
    assert "Wrapper options:" in out
    assert "Internal runner:" in out
    assert "python -m tmux_dashboard" in out
    assert "--once" in out
    assert "--iterations" in out
    assert "--window-target" in out
    assert "Examples:" in out
