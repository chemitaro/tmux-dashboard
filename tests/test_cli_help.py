"""CLI ヘルプの出力と正常終了コードを検証するテスト。"""

import subprocess
import sys


def test_cli_help_exits_zero():
    """`python -m tmux_dashboard -h` が 0 終了し、ヘルプ文言を表示することを確認する。"""
    # Run module as a script and ensure it exits successfully with -h
    proc = subprocess.run([sys.executable, "-m", "tmux_dashboard", "-h"], capture_output=True)
    assert proc.returncode == 0, proc.stderr.decode() if proc.stderr else proc.stdout.decode()
    out = proc.stdout.decode("utf-8", errors="ignore")
    assert "Tmux dashboard" in out or "usage" in out.lower()
