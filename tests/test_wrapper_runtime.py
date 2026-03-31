"""wrapper の runtime 健全性と runner 起動失敗検知を検証するテスト。

目的:
- `.venv` 健全性チェックで壊れた runtime を attach 前に止める。
- runner pane の即死を検知し、plain shell の dashboard を黙って残さない。
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _write_fake_python(path: Path) -> None:
    path.write_text(
        """#!/bin/sh
if [ "$1" = "-c" ]; then
  if [ "${FAKE_PYTHON_IMPORT_OK:-1}" = "1" ]; then
    exit 0
  fi
  echo "ModuleNotFoundError: No module named 'yaml'" >&2
  exit 1
fi
exit 0
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_fake_tmux(path: Path, state_file: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

state_path = Path(os.environ["FAKE_TMUX_STATE"])

if state_path.exists():
    state = json.loads(state_path.read_text())
else:
    state = {
        "session_exists": False,
        "windows": [],
        "capture_output": os.environ.get("FAKE_TMUX_CAPTURE_OUTPUT", ""),
    }

args = sys.argv[1:]

def save():
    state_path.write_text(json.dumps(state))

def window_by_name(name):
    for item in state["windows"]:
        if item["name"] == name:
            return item
    return None

if args[:2] == ["has-session", "-t"]:
    sys.exit(0 if state["session_exists"] and args[2] == "dashboard" else 1)

if args[:4] == ["new-session", "-d", "-s", "dashboard"]:
    state["session_exists"] = True
    state["windows"] = [{
        "index": 0,
        "name": "dashboard",
        "pane_dead": "0",
        "pane_start_command": "zsh",
    }]
    save()
    sys.exit(0)

if args[:3] == ["list-windows", "-t", "dashboard"]:
    fmt = args[-1]
    lines = []
    for item in sorted(state["windows"], key=lambda x: x["index"]):
        if fmt == "#{window_index}|#{window_name}":
            lines.append(f"{item['index']}|{item['name']}")
        elif fmt == "#{window_index}|#{window_name}|#{window_active}":
            active = "1" if item["index"] == 0 else "0"
            lines.append(f"{item['index']}|{item['name']}|{active}")
    if lines:
        sys.stdout.write("\\n".join(lines) + "\\n")
    sys.exit(0)

if len(args) >= 2 and args[0] == "set-option":
    sys.exit(0)

if args[:3] == ["new-window", "-d", "-a"]:
    name = args[args.index("-n") + 1]
    target = window_by_name(name)
    if target is None:
      state["windows"].append({
          "index": 1,
          "name": name,
          "pane_dead": "0",
          "pane_start_command": "zsh",
      })
      save()
    sys.exit(0)

if args[:2] == ["display-message", "-p"]:
    target = args[args.index("-t") + 1]
    fmt = args[-1]
    if target == "dashboard:1.0":
        runner = window_by_name("__tmux_dashboard_runner__")
        if runner is None:
            sys.exit(1)
        if fmt == "#{pane_dead}|#{pane_start_command}":
            sys.stdout.write(f"{runner['pane_dead']}|{runner['pane_start_command']}\\n")
            sys.exit(0)
        if fmt == "#{pane_dead}":
            sys.stdout.write(f"{runner['pane_dead']}\\n")
            sys.exit(0)
    sys.exit(1)

if args[:2] == ["respawn-pane", "-k"]:
    runner = window_by_name("__tmux_dashboard_runner__")
    if runner is None:
        sys.stderr.write("can't find window: 1\\n")
        sys.exit(1)
    runner["pane_start_command"] = args[-1]
    if os.environ.get("FAKE_TMUX_RUNNER_FAIL", "0") == "1":
        runner["pane_dead"] = "1"
    else:
        runner["pane_dead"] = "0"
    save()
    sys.exit(0)

if args[:2] == ["capture-pane", "-p"]:
    sys.stdout.write(state.get("capture_output", ""))
    sys.exit(0)

if args[:2] == ["switch-client", "-t"]:
    sys.exit(0)

if args[:2] == ["attach", "-t"]:
    sys.exit(0)

sys.stderr.write(f"unexpected tmux args: {args}\\n")
sys.exit(1)
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _run_wrapper(tmp_path: Path, *, import_ok: bool, runner_fail: bool) -> subprocess.CompletedProcess[str]:
    """wrapper を fake tmux/python で起動し、終了状態を返す。

    前提: fake tmux と fake python を PATH / env override で参照できる。
    期待: runtime 健全性と runner bootstrap 判定だけを deterministic に観測できる。
    """
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python"
    fake_tmux = fake_bin / "tmux"
    state_file = tmp_path / "tmux-state.json"
    _write_fake_python(fake_python)
    _write_fake_tmux(fake_tmux, state_file)

    script = Path(__file__).resolve().parents[1] / "tmux-dashboard"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["TMUX_DASHBOARD_PYTHON_BIN"] = str(fake_python)
    env["TMUX_DASHBOARD_SKIP_ATTACH"] = "1"
    env["TMUX_DASHBOARD_RUNNER_GRACE_SEC"] = "0"
    env["FAKE_TMUX_STATE"] = str(state_file)
    env["FAKE_PYTHON_IMPORT_OK"] = "1" if import_ok else "0"
    env["FAKE_TMUX_RUNNER_FAIL"] = "1" if runner_fail else "0"
    env["FAKE_TMUX_CAPTURE_OUTPUT"] = "Traceback: runner died\\n"

    return subprocess.run([str(script)], capture_output=True, text=True, env=env)


def test_wrapper_fails_fast_when_virtualenv_imports_are_broken(tmp_path):
    """壊れた `.venv` では tmux 操作前に fail-fast する。

    前提: import probe が `yaml` 欠落で失敗する。
    期待: wrapper は non-zero で終了し、修復手順を stderr に出す。
    """
    proc = _run_wrapper(tmp_path, import_ok=False, runner_fail=False)

    assert proc.returncode == 1
    assert "broken virtualenv" in proc.stderr
    assert "UV_CACHE_DIR" in proc.stderr


def test_wrapper_reports_runner_bootstrap_failure_before_attach(tmp_path):
    """runner pane の即死を検知して attach 前に止める。

    前提: import probe は成功するが、respawn 後の runner pane が dead になる。
    期待: wrapper は non-zero で終了し、pane 出力 tail を含む診断を返す。
    """
    proc = _run_wrapper(tmp_path, import_ok=True, runner_fail=True)

    assert proc.returncode == 1
    assert "runner bootstrap failed before attach" in proc.stderr
    assert "Traceback: runner died" in proc.stderr


def test_wrapper_succeeds_when_runtime_and_runner_are_healthy(tmp_path):
    """runtime 健全で runner が生存していれば成功終了する。

    前提: import probe と respawn 後の runner pane がともに成功する。
    期待: wrapper は 0 終了し、stderr に診断エラーを出さない。
    """
    proc = _run_wrapper(tmp_path, import_ok=True, runner_fail=False)

    assert proc.returncode == 0, proc.stderr
    assert "broken virtualenv" not in proc.stderr
    assert "runner bootstrap failed before attach" not in proc.stderr
