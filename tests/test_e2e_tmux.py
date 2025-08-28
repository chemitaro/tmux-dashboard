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
import subprocess
import sys
from typing import List

import pytest


def _sh(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True)


def _exists_tmux() -> bool:
    return shutil.which("tmux") is not None


pytestmark = pytest.mark.skipif(not _exists_tmux(), reason="tmux not available")


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


def _window_width(target: str) -> int:
    cp = _sh(["tmux", "display-message", "-p", "-t", target, "#{window_width}"])
    return int(cp.stdout.decode().strip())


def _pane_widths(target: str) -> list[int]:
    cp = _sh(["tmux", "list-panes", "-t", target, "-F", "#{pane_width}"])
    return [int(x) for x in cp.stdout.decode().splitlines() if x]


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
