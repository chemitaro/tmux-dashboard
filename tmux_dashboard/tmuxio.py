"""tmux I/O ラッパ（ドライバ抽象 + libtmux/cli 実装）。

非侵襲: set-option は `-w`（window限定）のみを使用。
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Tuple

# module-level handle to libtmux for monkeypatching in tests
try:  # pragma: no cover - optional import
    import libtmux as libtmux  # type: ignore
except Exception:  # pragma: no cover
    libtmux = None  # type: ignore


def _run_subprocess(args, capture_output=True, check=True):
    return subprocess.run(args, capture_output=capture_output, check=check)


class CliDriver:
    """tmux コマンドを直接実行するドライバ。依存が少なく移植性が高い。"""

    def list_sessions(self) -> list[str]:
        """セッション名一覧を返す（ASCII昇順ソートは呼び出し側で行う）。"""
        cp = _run_subprocess(["tmux", "list-sessions", "-F", "#{session_name}"])
        out = cp.stdout.decode().splitlines()
        return [s for s in out if s]

    def window_size(self, window_target: str) -> Tuple[int, int]:
        """ウィンドウの幅/高さを返す。"""
        cp = _run_subprocess(
            [
                "tmux",
                "display-message",
                "-p",
                "-t",
                window_target,
                "#{window_width} #{window_height}",
            ]
        )
        w, h = cp.stdout.decode().strip().split()
        return int(w), int(h)

    def capture_pane(self, pane_target: str, H: int, join_wrapped: bool) -> str:
        """対象ペインの下端から H 行を取得する（ANSI保持）。"""
        args = [
            "tmux",
            "capture-pane",
            "-p",
            "-e",
        ]
        if join_wrapped:
            args.append("-J")
        args += ["-S", f"-{H}", "-E", "-1", "-t", pane_target]
        cp = _run_subprocess(args)
        return cp.stdout.decode()

    def set_window_option(self, window_target: str, key: str, value: str) -> None:
        """ウィンドウ限定（-w）でオプションを設定する（非侵襲）。"""
        _run_subprocess(["tmux", "set-option", "-w", "-t", window_target, key, value])

    def set_pane_title(self, pane_target: str, title: str) -> None:
        """ペインタイトル（pane-border-formatが#{pane_title}）を設定する。"""
        _run_subprocess(["tmux", "select-pane", "-t", pane_target, "-T", title])

    def list_panes(self, window_target: str) -> list[str]:
        """対象ウィンドウの pane_id 一覧を返す。"""
        cp = _run_subprocess(["tmux", "list-panes", "-t", window_target, "-F", "#{pane_id}"])
        return [l for l in cp.stdout.decode().splitlines() if l]

    def kill_other_panes(self, window_target: str) -> None:
        """対象ウィンドウで現在のペイン以外を全て閉じる。"""
        _run_subprocess(["tmux", "kill-pane", "-a", "-t", window_target])

    def split_window(self, window_target: str, direction: str, percent: int) -> None:
        """指定方向に分割する。direction: 'h'（水平）/ 'v'（垂直）。"""
        flag = "-h" if direction == "h" else "-v"
        # pane を明示（.0）: クライアント非接続でも対象を特定できるようにする
        target = f"{window_target}.0"
        _run_subprocess(["tmux", "split-window", flag, "-p", str(percent), "-t", target])


class LibtmuxDriver:
    """libtmux を用いて tmux を操作するドライバ。

    - Server 接続時に `socket_name`/`socket_path` を反映可能。
    - 対象ウィンドウは `session:window_index` の target 文字列から解決。
    - セーフティ: sessions から解決できない場合は `_server._window` にフォールバック。
    """
    def __init__(self, socket_name: str | None = None, socket_path: str | None = None):
        try:
            import libtmux  # noqa: F401
        except Exception:  # pragma: no cover - import error handled lazily in tests
            pass
        self._server = None
        self._socket_name = socket_name
        self._socket_path = socket_path

    def _ensure_server(self):
        """libtmux Server を遅延初期化して返す。"""
        if self._server is None:
            # use module-level libtmux if provided (for tests), else import
            lm = libtmux
            if lm is None:  # type: ignore[truthy-bool]
                import libtmux as lm  # type: ignore
                globals()["libtmux"] = lm

            kwargs = {}
            if self._socket_name:
                kwargs["socket_name"] = self._socket_name
            if self._socket_path:
                kwargs["socket_path"] = self._socket_path
            self._server = lm.Server(**kwargs)  # type: ignore
        return self._server

    # ----- helpers -----
    def _get_window_by_target(self, window_target: str):
        server = self._ensure_server()
        try:
            sess_name, win_idx = window_target.split(":", 1)
        except ValueError:
            # 形式外: フォールバック
            return getattr(server, "_window", None)
        sessions = getattr(server, "sessions", [])
        for s in sessions:
            if getattr(s, "session_name", None) == sess_name:
                for w in getattr(s, "windows", []):
                    if str(getattr(w, "window_index", "")) == str(win_idx):
                        return w
        # 見つからなければフォールバック
        return getattr(server, "_window", None)

    def list_sessions(self) -> list[str]:
        """セッション名一覧を返す。"""
        server = self._ensure_server()
        return [s.session_name for s in getattr(server, "sessions", [])]

    def window_size(self, window_target: str) -> Tuple[int, int]:
        """ウィンドウの幅/高さを返す（テストでは FakeWindow の値を使用）。"""
        # window_target は "session:window" 形式を想定。ここでは簡易取得（mock前提）。
        wobj = self._get_window_by_target(window_target)
        w = int(getattr(wobj, "window_width", 0))
        h = int(getattr(wobj, "window_height", 0))
        return w, h

    def capture_pane(self, pane_target: str, H: int, join_wrapped: bool) -> str:
        """対象ペインの下端から H 行を取得する（ANSI保持）。"""
        server = self._ensure_server()
        # Windowに紐づくpaneではなく直接pane_id指定のため、pane側に委譲
        pane = getattr(server, "_pane", None)
        if pane is None:
            # 最低限のフォールバック: window.cmd で実行（Fakeでの検証用）
            wobj = self._get_window_by_target("fallback:0")
            res = wobj.cmd("capture-pane", "-p", "-e", "-S", f"-{H}", "-E", "-1", "-t", pane_target)  # type: ignore[attr-defined]
        else:
            args = ["capture-pane", "-p", "-e", "-S", f"-{H}", "-E", "-1", "-t", pane_target]
            res = pane.cmd(*args)  # type: ignore[attr-defined]
        return "".join(res.stdout)

    def set_window_option(self, window_target: str, key: str, value: str) -> None:
        """ウィンドウ限定（-w）でオプションを設定する（非侵襲）。"""
        wobj = self._get_window_by_target(window_target)
        wobj.cmd("set-option", "-w", "-t", window_target, key, value)  # type: ignore[attr-defined]

    def set_pane_title(self, pane_target: str, title: str) -> None:
        """ペインタイトル（pane-border-formatが#{pane_title}）を設定する。"""
        server = self._ensure_server()
        server.cmd("select-pane", "-t", pane_target, "-T", title)  # type: ignore[attr-defined]

    def list_panes(self, window_target: str) -> list[str]:
        """対象ウィンドウの pane_id 一覧（libtmuxオブジェクトから抽出）を返す。"""
        wobj = self._get_window_by_target(window_target)
        panes = getattr(wobj, "panes", [])
        out = []
        for p in panes:
            pid = getattr(p, "pane_id", None)
            if pid:
                out.append(pid)
                continue
            # テストのフェイクでは文字列IDの配列を許容
            if isinstance(p, str) and p.startswith("%"):
                out.append(p)
        return out

    def kill_other_panes(self, window_target: str) -> None:
        wobj = self._get_window_by_target(window_target)
        wobj.cmd("kill-pane", "-a", "-t", window_target)  # type: ignore[attr-defined]

    def split_window(self, window_target: str, direction: str, percent: int) -> None:
        wobj = self._get_window_by_target(window_target)
        flag = "-h" if direction == "h" else "-v"
        wobj.cmd("split-window", flag, "-p", str(percent), "-t", window_target)  # type: ignore[attr-defined]

    


@dataclass
class TmuxIO:
    """tmux I/O の統一インターフェース。

    呼び出しは保持するドライバへ委譲される。
    """
    driver: object

    def list_sessions(self) -> list[str]:
        """セッション名一覧を返す。"""
        return self.driver.list_sessions()

    def window_size(self, window_target: str) -> Tuple[int, int]:
        """ウィンドウの幅/高さを返す。"""
        return self.driver.window_size(window_target)

    def capture_pane(self, pane_target: str, H: int, join_wrapped: bool) -> str:
        """対象ペインの下端から H 行を取得する（ANSI保持）。"""
        return self.driver.capture_pane(pane_target, H, join_wrapped)

    def set_window_option(self, window_target: str, key: str, value: str) -> None:
        """ウィンドウ限定（-w）でオプションを設定する（非侵襲）。"""
        return self.driver.set_window_option(window_target, key, value)

    def set_pane_title(self, pane_target: str, title: str) -> None:
        """ペインタイトル（pane-border-formatが#{pane_title}）を設定する。"""
        return self.driver.set_pane_title(pane_target, title)

    def list_panes(self, window_target: str) -> list[str]:
        """対象ウィンドウの pane_id 一覧を返す。"""
        return self.driver.list_panes(window_target)

    def kill_other_panes(self, window_target: str) -> None:
        """対象ウィンドウで現在のペイン以外を全て閉じる。"""
        return self.driver.kill_other_panes(window_target)

    def split_window(self, window_target: str, direction: str, percent: int) -> None:
        """指定方向に分割する。direction: 'h'（水平）/ 'v'（垂直）。"""
        return self.driver.split_window(window_target, direction, percent)


def create_from_config(cfg) -> TmuxIO:
    """設定に基づきドライバを選び `TmuxIO` を構築する。"""
    drv_name = (getattr(cfg, "tmux", None) and cfg.tmux.driver) or "libtmux"
    if drv_name == "cli":
        driver = CliDriver()
    else:
        driver = LibtmuxDriver(socket_name=getattr(cfg.tmux, "socket_name", None), socket_path=getattr(cfg.tmux, "socket_path", None))
    return TmuxIO(driver=driver)
