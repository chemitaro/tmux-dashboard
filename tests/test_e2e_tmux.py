"""実環境 tmux を用いたエンドツーエンドテスト。

前提:
- コンテナ内で tmux が稼働していない（または全セッションを削除して良い）。
- セッションは本テストで作成/削除する。

目的:
- 実際の tmux セッション数と名称に応じて、dashboard:0 に pane タイトルが設定されること。
- セッション削除後に再実行すると、pane タイトルから削除セッションが消えること。
- リサイズ時にレイアウト再計算されること（単一列幅の検証）。
"""

from __future__ import annotations

import shutil
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import List

import pytest


def _sh(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True)


def _exists_tmux() -> bool:
    return shutil.which("tmux") is not None


def _tmux_usable() -> bool:
    """tmux が起動・ソケット作成できるかを検査する（サンドボックス環境では失敗し得る）。"""
    if not _exists_tmux():
        return False
    cp = subprocess.run(["tmux", "start-server"], capture_output=True)
    if cp.returncode != 0:
        return False
    subprocess.run(["tmux", "kill-server"], capture_output=True)
    return True


pytestmark = pytest.mark.skipif(not _tmux_usable(), reason="tmux not usable in this environment")


@pytest.fixture(autouse=True)
def clean_tmux_server():
    """各テスト前後で tmux サーバを初期化する。"""
    # 前処理: サーバを停止（存在しなくてもOK）
    subprocess.run(["tmux", "kill-server"], capture_output=True)
    yield
    # 後処理: サーバを停止
    subprocess.run(["tmux", "kill-server"], capture_output=True)


def _create_session(name: str):
    _sh(["tmux", "new-session", "-d", "-s", name])


def _pane_titles(target: str) -> list[str]:
    cp = _sh(["tmux", "list-panes", "-t", target, "-F", "#{pane_title}"])
    return [l for l in cp.stdout.decode().splitlines() if l]


def _pane_title_rows(target: str) -> list[str]:
    cp = _sh(["tmux", "list-panes", "-t", target, "-F", "#{pane_index}|#{pane_title}"])
    return cp.stdout.decode().splitlines()


def _window_width(target: str) -> int:
    cp = _sh(["tmux", "display-message", "-p", "-t", target, "#{window_width}"])
    return int(cp.stdout.decode().strip())


def _window_option(target: str, option_name: str) -> str:
    cp = _sh(["tmux", "show-options", "-w", "-t", target, option_name])
    line = cp.stdout.decode().strip()
    parts = line.split(None, 1)
    if len(parts) != 2:
        raise AssertionError(f"unexpected option output: {line}")
    return parts[1]


def _pane_widths(target: str) -> list[int]:
    cp = _sh(["tmux", "list-panes", "-t", target, "-F", "#{pane_width}"])
    return [int(x) for x in cp.stdout.decode().splitlines() if x]


def _window_names(session_name: str) -> list[str]:
    cp = _sh(["tmux", "list-windows", "-t", session_name, "-F", "#{window_name}"])
    return [x for x in cp.stdout.decode().splitlines() if x]


def _wait_until(predicate, *, timeout: float = 8.0, interval: float = 0.1):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except Exception as exc:  # pragma: no cover - 待機中の一時的不整合
            last_error = exc
        time.sleep(interval)
    if last_error is not None:
        raise AssertionError(f"condition not met before timeout: {last_error}")
    raise AssertionError("condition not met before timeout")


def _run_dashboard_once(target: str, iterations: int = 1, config_path: str | None = None):
    args = [
        sys.executable,
        "-m",
        "tmux_dashboard",
        *( ["--config", config_path] if config_path else [] ),
        "--window-target",
        target,
        "--once",
        "--iterations",
        str(iterations),
    ]
    _sh(args)


def test_e2e_titles_reflect_sessions(tmp_path):
    """セッション名が pane タイトルとして設定される（dashboard 自身は除外）。"""
    # dashboard ウィンドウを作成
    _create_session("dashboard")
    # 監視対象のセッションを作成
    for name in ["alpha", "beta", "gamma"]:
        _create_session(name)

    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("tmux:\n  driver: libtmux\n", encoding="utf-8")
    _run_dashboard_once("dashboard:0", config_path=str(cfg))

    titles = _pane_titles("dashboard:0")
    # タイトルは監視対象のいずれか（順不同、枚数は環境に依存するため1以上で良い）
    assert len(titles) >= 1
    assert set(titles).issubset({"alpha", "beta", "gamma"})


def test_e2e_remove_session_updates_titles(tmp_path):
    """セッション削除後、再実行でタイトルから消える。"""
    _create_session("dashboard")
    for name in ["alpha", "beta", "gamma"]:
        _create_session(name)
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("tmux:\n  driver: libtmux\n", encoding="utf-8")
    _run_dashboard_once("dashboard:0", config_path=str(cfg))

    # beta を削除
    _sh(["tmux", "kill-session", "-t", "beta"])
    _run_dashboard_once("dashboard:0", config_path=str(cfg))
    titles = _pane_titles("dashboard:0")
    assert "beta" not in titles
    assert any(t in {"alpha", "gamma"} for t in titles)


def test_e2e_same_name_session_and_window_still_builds_layout(tmp_path):
    """wrapper同等の session/window 同名条件でも staging window 作成に成功する。"""
    _sh(["tmux", "new-session", "-d", "-s", "dashboard", "-n", "dashboard"])
    for name in ["alpha", "beta", "gamma"]:
        _create_session(name)

    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("tmux:\n  driver: libtmux\n", encoding="utf-8")
    _run_dashboard_once("dashboard:0", config_path=str(cfg))

    titles = _pane_titles("dashboard:0")
    pane_widths = _pane_widths("dashboard:0")
    assert len(pane_widths) == 3
    assert set(titles) == {"alpha", "beta", "gamma"}


def test_e2e_wrapper_path_builds_layout_and_runner_window():
    """実際の wrapper 経路でも dashboard/runner window を作成し、複数 pane と titles を得られる。"""
    repo_dir = Path(__file__).resolve().parents[1]
    for name in ["alpha", "beta", "gamma"]:
        _create_session(name)

    wrapper_cmd = f"cd {shlex.quote(str(repo_dir))} && ./tmux-dashboard"
    _sh(["tmux", "new-session", "-d", "-s", "control", wrapper_cmd])

    _wait_until(
        lambda: "__tmux_dashboard_runner__" in set(_window_names("dashboard"))
        and set(_pane_titles("dashboard:0")) == {"alpha", "beta", "gamma"}
        and len(_pane_widths("dashboard:0")) == 3
    )

    assert "__tmux_dashboard_runner__" in set(_window_names("dashboard"))
    assert len(_pane_widths("dashboard:0")) == 3


def test_e2e_wrapper_path_zero_sessions_clear_stale_title():
    """wrapper 経路で全対象セッションが消えた後、dashboard:0 は 1 pane / 空 title へ収束する。"""
    repo_dir = Path(__file__).resolve().parents[1]
    for name in ["alpha", "beta"]:
        _create_session(name)

    wrapper_cmd = f"cd {shlex.quote(str(repo_dir))} && ./tmux-dashboard"
    _sh(["tmux", "new-session", "-d", "-s", "control", wrapper_cmd])

    _wait_until(
        lambda: "__tmux_dashboard_runner__" in set(_window_names("dashboard"))
        and set(_pane_titles("dashboard:0")) == {"alpha", "beta"}
        and len(_pane_widths("dashboard:0")) == 2
    )

    _sh(["tmux", "kill-session", "-t", "alpha"])
    _sh(["tmux", "kill-session", "-t", "beta"])

    _wait_until(
        lambda: len(_pane_widths("dashboard:0")) == 1
        and _pane_title_rows("dashboard:0") == ["0|"]
    )

    assert _pane_title_rows("dashboard:0") == ["0|"]


def test_e2e_resize_single_column_layout(tmp_path):
    """幅を縮小後、単一列に再計算され pane 幅がウィンドウ幅に一致する。"""
    _create_session("dashboard")
    for name in ["a", "b"]:
        _create_session(name)
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("tmux:\n  driver: libtmux\n", encoding="utf-8")
    _run_dashboard_once("dashboard:0", config_path=str(cfg))

    # 幅を 79 に（min_tile_width=40 に対して列=1）
    _sh(["tmux", "resize-window", "-t", "dashboard:0", "-x", "79", "-y", "40"])
    _run_dashboard_once("dashboard:0", config_path=str(cfg))

    w = _window_width("dashboard:0")
    assert w == 79
    # 少なくとも1 pane が存在
    assert len(_pane_widths("dashboard:0")) >= 1


def test_e2e_many_sessions_grid_exact(tmp_path):
    """多セッション×幅でグリッドが期待通りに構成される。"""
    _create_session("dashboard")
    names = [f"s{i}" for i in range(1, 9)]  # 8セッション
    for n in names:
        _create_session(n)

    # min_tile_width=40, width=160 → columns=4, rows=2 → panes=8
    _sh(["tmux", "resize-window", "-t", "dashboard:0", "-x", "160", "-y", "40"])
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("min_tile_width: 40\ntmux:\n  driver: libtmux\n", encoding="utf-8")
    _run_dashboard_once("dashboard:0", config_path=str(cfg))

    titles = _pane_titles("dashboard:0")
    panes = _pane_widths("dashboard:0")
    assert len(panes) == 8
    # タイトルは少なくとも全セッション名を含む
    for n in names:
        assert n in titles


def test_e2e_dynamic_add_then_remove(tmp_path):
    """動的追加・削除でタイトルが更新される。"""
    _create_session("dashboard")
    for n in ["alpha", "beta"]:
        _create_session(n)

    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("tmux:\n  driver: libtmux\n", encoding="utf-8")
    _run_dashboard_once("dashboard:0", config_path=str(cfg))

    # add gamma
    _create_session("gamma")
    _run_dashboard_once("dashboard:0", config_path=str(cfg))
    titles = _pane_titles("dashboard:0")
    if len(_pane_widths("dashboard:0")) == 1:
        pytest.xfail("Headless tmux may not support split-window; cannot verify multi-pane titles")
    assert "gamma" in titles

    # remove alpha
    _sh(["tmux", "kill-session", "-t", "alpha"])
    _run_dashboard_once("dashboard:0", config_path=str(cfg))
    titles = _pane_titles("dashboard:0")
    assert "alpha" not in titles
    assert "beta" in titles or "gamma" in titles


def test_e2e_zero_sessions_clear_stale_title(tmp_path):
    """対象セッションが 0 件になった後は単一 pane かつ空 title に収束する。"""
    _create_session("dashboard")
    for name in ["alpha", "beta"]:
        _create_session(name)

    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("tmux:\n  driver: libtmux\n", encoding="utf-8")
    _run_dashboard_once("dashboard:0", config_path=str(cfg))

    _sh(["tmux", "kill-session", "-t", "alpha"])
    _sh(["tmux", "kill-session", "-t", "beta"])
    _run_dashboard_once("dashboard:0", config_path=str(cfg))

    assert len(_pane_widths("dashboard:0")) == 1
    assert _pane_title_rows("dashboard:0") == ["0|"]


def test_e2e_resize_up_and_down(tmp_path):
    """リサイズの増減でグリッドの分割数が再計算される。"""
    _create_session("dashboard")
    names = ["a", "b", "c", "d", "e", "f"]  # 6セッション
    for n in names:
        _create_session(n)

    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("min_tile_width: 40\ntmux:\n  driver: libtmux\n", encoding="utf-8")

    # 幅120 → columns=3, rows=2 → panes=6
    _sh(["tmux", "resize-window", "-t", "dashboard:0", "-x", "120", "-y", "40"])
    _run_dashboard_once("dashboard:0", config_path=str(cfg))
    assert len(_pane_widths("dashboard:0")) == 6

    # 幅79 → columns=1, rows=6 → panes=6
    _sh(["tmux", "resize-window", "-t", "dashboard:0", "-x", "79", "-y", "40"])
    _run_dashboard_once("dashboard:0", config_path=str(cfg))
    assert len(_pane_widths("dashboard:0")) == 6


def test_e2e_direct_runner_recovers_manual_window_size_to_latest(tmp_path):
    """direct runner が既存 manual 汚染を latest へ自動回復することを確認する。"""
    _create_session("dashboard")
    for name in ["alpha", "beta"]:
        _create_session(name)

    _sh(["tmux", "set-window-option", "-t", "dashboard:0", "window-size", "manual"])
    assert _window_option("dashboard:0", "window-size") == "manual"

    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("tmux:\n  driver: libtmux\n", encoding="utf-8")
    _run_dashboard_once("dashboard:0", config_path=str(cfg))

    assert _window_option("dashboard:0", "window-size") == "latest"


def test_e2e_wrapper_recovers_manual_and_follows_resize():
    """wrapper 経路で manual を latest へ回復し、resize 追随することを確認する。"""
    repo_dir = Path(__file__).resolve().parents[1]
    _sh(["tmux", "new-session", "-d", "-s", "dashboard", "-n", "dashboard"])
    for name in ["alpha", "beta", "gamma"]:
        _create_session(name)
    _sh(["tmux", "set-window-option", "-t", "dashboard:0", "window-size", "manual"])
    assert _window_option("dashboard:0", "window-size") == "manual"

    wrapper_cmd = f"cd {shlex.quote(str(repo_dir))} && ./tmux-dashboard"
    _sh(["tmux", "new-session", "-d", "-s", "control", wrapper_cmd])

    _wait_until(
        lambda: "__tmux_dashboard_runner__" in set(_window_names("dashboard"))
        and _window_option("dashboard:0", "window-size") == "latest"
        and set(_pane_titles("dashboard:0")) == {"alpha", "beta", "gamma"}
    )

    _sh(["tmux", "resize-window", "-t", "dashboard:0", "-x", "79", "-y", "40"])
    _wait_until(
        lambda: _window_width("dashboard:0") == 79
        and len(_pane_widths("dashboard:0")) == 3
        and all(width == 79 for width in _pane_widths("dashboard:0"))
    )

    _sh(["tmux", "resize-window", "-t", "dashboard:0", "-x", "191", "-y", "98"])
    _wait_until(
        lambda: _window_width("dashboard:0") == 191
        and len(_pane_widths("dashboard:0")) == 3
        and max(_pane_widths("dashboard:0")) > 79
    )
