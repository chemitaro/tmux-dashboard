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
    # 低コストのコマンドトレース（DEBUG）
    try:
        import logging
        logging.getLogger("tmux_dashboard.tmuxio").debug("run: %s", " ".join(map(str, args)))
    except Exception:
        pass
    return subprocess.run(args, capture_output=capture_output, check=check)


class CliDriver:
    """tmux コマンドを直接実行するドライバ。依存が少なく移植性が高い。"""

    def __init__(self, cfg=None):
        """設定を受け取って初期化。"""
        self.cfg = cfg

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
        """対象ペインから適切な量の履歴を含めて取得（ANSI保持）。
        
        ダッシュボードのタイル高さ(H)に応じて、履歴バッファから
        十分な行数を取得し、format_linesで最後のH行を表示。
        """
        # スマートな取得行数の計算（設定値を使用）
        if self.cfg and hasattr(self.cfg, 'viewer'):
            multiplier = self.cfg.viewer.capture_buffer_multiplier
            max_lines = self.cfg.viewer.capture_buffer_max
            min_extra = self.cfg.viewer.capture_buffer_min_extra
        else:
            # デフォルト値
            multiplier = 2.0
            max_lines = 200
            min_extra = 20
        
        capture_lines = min(max(int(H * multiplier), H + min_extra), max_lines)
        
        args = [
            "tmux",
            "capture-pane",
            "-p",
            "-e",
        ]
        if join_wrapped:
            args.append("-J")
        # 履歴バッファの終端からcapture_lines行を取得
        args += ["-S", f"-{capture_lines}", "-t", pane_target]
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

    def _normalize_split_length(self, length: str | int | None, percent: int | None) -> str:
        """split-window の -l に渡す長さ文字列を正規化する。"""
        if length is None:
            if percent is None:
                raise ValueError("split length is required")
            return f"{percent}%"
        if isinstance(length, int):
            return str(length)
        return length

    def split_window(
        self,
        window_target: str,
        direction: str,
        length: str | int | None = None,
        *,
        percent: int | None = None,
    ) -> None:
        """指定方向に分割する。direction: 'h'（水平）/ 'v'（垂直）。"""
        flag = "-h" if direction == "h" else "-v"
        # pane を明示（.0）: クライアント非接続でも対象を特定できるようにする
        target = f"{window_target}.0"
        split_length = self._normalize_split_length(length, percent)
        _run_subprocess(["tmux", "split-window", flag, "-l", split_length, "-t", target])

    def select_pane(self, pane_id: str) -> None:
        _run_subprocess(["tmux", "select-pane", "-t", pane_id])

    def split_pane(
        self,
        pane_id: str,
        direction: str,
        length: str | int | None = None,
        *,
        percent: int | None = None,
    ) -> None:
        flag = "-h" if direction == "h" else "-v"
        split_length = self._normalize_split_length(length, percent)
        _run_subprocess(["tmux", "split-window", flag, "-l", split_length, "-t", pane_id])

    def list_panes_detailed(self, window_target: str) -> list[tuple[str, int, int]]:
        cp = _run_subprocess(["tmux", "list-panes", "-t", window_target, "-F", "#{pane_id} #{pane_left} #{pane_top}"])
        out: list[tuple[str, int, int]] = []
        for line in cp.stdout.decode().splitlines():
            if not line.strip():
                continue
            pid, left, top = line.strip().split()
            out.append((pid, int(left), int(top)))
        return out

    # ---- new helpers for renderer orchestration ----
    def list_windows_with_active(self, session_name: str) -> list[tuple[int, int]]:
        """Return (window_index, window_active) list for a session."""
        cp = _run_subprocess(["tmux", "list-windows", "-t", session_name, "-F", "#{window_index} #{window_active}"])
        out: list[tuple[int, int]] = []
        for line in cp.stdout.decode().splitlines():
            line = line.strip()
            if not line:
                continue
            wi, act = line.split()
            out.append((int(wi), int(act)))
        return out

    def list_panes_in_window_with_active(self, session_name: str, window_index: int) -> list[tuple[int, int, str]]:
        """Return (pane_index, pane_active, pane_id) list for a session:window."""
        target = f"{session_name}:{window_index}"
        cp = _run_subprocess(["tmux", "list-panes", "-t", target, "-F", "#{pane_index} #{pane_active} #{pane_id}"])
        out: list[tuple[int, int, str]] = []
        for line in cp.stdout.decode().splitlines():
            line = line.strip()
            if not line:
                continue
            pi, act, pid = line.split()
            out.append((int(pi), int(act), pid))
        return out

    def resolve_active_pane(self, session_name: str) -> str | None:
        """Pick a deterministic pane_id per spec: active window/pane else minimum index."""
        wins = self.list_windows_with_active(session_name)
        if not wins:
            return None
        # prefer active, else min index
        wins_sorted = sorted(wins, key=lambda x: (0 if x[1] == 1 else 1, x[0]))
        win_idx = wins_sorted[0][0]
        panes = self.list_panes_in_window_with_active(session_name, win_idx)
        if not panes:
            return None
        panes_sorted = sorted(panes, key=lambda x: (0 if x[1] == 1 else 1, x[0]))
        return panes_sorted[0][2]
    
    def _calculate_content_freshness(self, content: str) -> int:
        """内容の新鮮さをスコア化。
        
        - ANSIエスケープシーケンスの存在
        - プロンプトの存在
        - 空でない行の数
        """
        if not content:
            return 0
        
        score = 0
        lines = content.split('\n')
        
        # 最後の10行を重視
        recent_lines = lines[-10:] if len(lines) > 10 else lines
        
        for line in recent_lines:
            if '\x1b[' in line:  # ANSIエスケープ
                score += 1
            if any(prompt in line for prompt in ['$', '>', '#', '%']):  # プロンプト
                score += 2
            if line.strip():  # 空でない行
                score += 0.5
        
        return int(score)
    
    def resolve_best_pane(self, session_name: str) -> str | None:
        """VS Codeターミナルでも確実に動作するインテリジェントpane選択。
        
        1. まず従来の方法を試す（パフォーマンスのため）
        2. 内容が空の場合、全paneをスキャン
        3. 内容の新鮮さで優先順位を決定
        """
        # Step 1: アクティブなwindow/paneがあるか確認
        wins = self.list_windows_with_active(session_name)
        has_active = any(win_active == 1 for _, win_active in wins)
        
        if has_active:
            # アクティブなwindow/paneがある場合は従来の方法を使う
            active_pane = self.resolve_active_pane(session_name)
            if active_pane:
                # 内容を確認
                try:
                    # デフォルト値でキャプチャ
                    if self.cfg and hasattr(self.cfg, 'viewer'):
                        multiplier = self.cfg.viewer.capture_buffer_multiplier
                        max_lines = self.cfg.viewer.capture_buffer_max
                    else:
                        multiplier = 2.0
                        max_lines = 200
                    
                    H = 50  # 仮の高さ
                    capture_lines = min(int(H * multiplier), max_lines)
                    
                    args = ["tmux", "capture-pane", "-p", "-e", "-S", f"-{capture_lines}", "-t", active_pane]
                    cp = _run_subprocess(args)
                    content = cp.stdout.decode()
                    
                    if content and len(content.strip()) > 0:
                        return active_pane
                except Exception:
                    pass
        
        # Step 2: 全window/paneをスキャン
        panes_with_content = []
        
        wins = self.list_windows_with_active(session_name)
        for win_idx, _ in wins:
            panes = self.list_panes_in_window_with_active(session_name, win_idx)
            for pane_idx, _, pane_id in panes:
                try:
                    # より多くの履歴を取得
                    args = ["tmux", "capture-pane", "-p", "-e", "-S", "-1000", "-t", pane_id]
                    cp = _run_subprocess(args)
                    content = cp.stdout.decode()
                    
                    if content and len(content.strip()) > 0:
                        freshness = self._calculate_content_freshness(content)
                        panes_with_content.append({
                            'pane_id': pane_id,
                            'content_length': len(content),
                            'freshness': freshness,
                            'window_index': win_idx,
                            'pane_index': pane_idx
                        })
                except Exception:
                    continue
        
        # Step 3: 最適なpaneを選択
        if panes_with_content:
            # 優先順位: 新鮮さ > window_index > pane_index
            best_pane = sorted(panes_with_content,
                             key=lambda x: (-x['freshness'],
                                          x['window_index'],
                                          x['pane_index']))[0]
            return best_pane['pane_id']
        
        # Step 4: フォールバック
        return f"{session_name}:0.0"

    def respawn_pane(self, pane_id: str, argv: list[str]) -> None:
        """Kill current program in pane and start argv as new program (respawn-pane)."""
        _run_subprocess(["tmux", "respawn-pane", "-k", "-t", pane_id] + argv, capture_output=False)
    
    def create_session(self, session_name: str, detached: bool = True) -> None:
        """新しいtmuxセッションを作成する。"""
        args = ["tmux", "new-session", "-s", session_name]
        if detached:
            args.append("-d")
        _run_subprocess(args)
    
    def list_panes_with_titles(self, window_target: str) -> list[tuple[str, str]]:
        """指定ウィンドウのペインIDとタイトルのリストを返す。
        
        Returns:
            [(pane_id, pane_title), ...]
        """
        cp = _run_subprocess(["tmux", "list-panes", "-t", window_target, "-F", "#{pane_id} #{pane_title}"])
        out: list[tuple[str, str]] = []
        for line in cp.stdout.decode().splitlines():
            if not line.strip():
                continue
            parts = line.strip().split(' ', 1)
            if len(parts) == 2:
                pane_id, title = parts
                out.append((pane_id, title))
            elif len(parts) == 1:
                # タイトルが空の場合
                out.append((parts[0], ""))
        return out


class LibtmuxDriver:
    """libtmux を用いて tmux を操作するドライバ。

    - Server 接続時に `socket_name`/`socket_path` を反映可能。
    - 対象ウィンドウは `session:window_index` の target 文字列から解決。
    - セーフティ: sessions から解決できない場合は `_server._window` にフォールバック。
    """
    def __init__(self, cfg=None, socket_name: str | None = None, socket_path: str | None = None):
        try:
            import libtmux  # noqa: F401
        except Exception:  # pragma: no cover - import error handled lazily in tests
            pass
        self.cfg = cfg
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
        """セッション名一覧を返す（cmd 経由で最新を取得）。"""
        server = self._ensure_server()
        try:
            logger = __import__("logging").getLogger("tmux_dashboard.tmuxio")
            logger.debug("libtmux: list-sessions -F #{session_name}")
        except Exception:
            logger = None
        res = server.cmd("list-sessions", "-F", "#{session_name}")  # type: ignore[attr-defined]
        # libtmux の stdout は既に行ごとのリストになっている前提。join しない。
        items = []
        for s in getattr(res, "stdout", []) or []:
            name = str(s).strip()
            if name:
                items.append(name)
        if logger:
            logger.debug("sessions=%s", items)
        return items

    def window_size(self, window_target: str) -> Tuple[int, int]:
        """ウィンドウの幅/高さを返す（テストでは FakeWindow の値を使用）。"""
        # window_target は "session:window" 形式を想定。ここでは簡易取得（mock前提）。
        wobj = self._get_window_by_target(window_target)
        w = int(getattr(wobj, "window_width", 0))
        h = int(getattr(wobj, "window_height", 0))
        return w, h

    def capture_pane(self, pane_target: str, H: int, join_wrapped: bool) -> str:
        """対象ペインから適切な量の履歴を含めて取得（ANSI保持）。
        
        ダッシュボードのタイル高さ(H)に応じて、履歴バッファから
        十分な行数を取得し、format_linesで最後のH行を表示。
        """
        # スマートな取得行数の計算（設定値を使用）
        if self.cfg and hasattr(self.cfg, 'viewer'):
            multiplier = self.cfg.viewer.capture_buffer_multiplier
            max_lines = self.cfg.viewer.capture_buffer_max
            min_extra = self.cfg.viewer.capture_buffer_min_extra
        else:
            # デフォルト値
            multiplier = 2.0
            max_lines = 200
            min_extra = 20
        
        capture_lines = min(max(int(H * multiplier), H + min_extra), max_lines)
        
        server = self._ensure_server()
        # Windowに紐づくpaneではなく直接pane_id指定のため、pane側に委譲
        pane = getattr(server, "_pane", None)
        
        # -Jオプションの処理を追加
        base_args = ["capture-pane", "-p", "-e"]
        if join_wrapped:
            base_args.append("-J")
        # 履歴バッファの終端からcapture_lines行を取得
        base_args += ["-S", f"-{capture_lines}", "-t", pane_target]
        
        if pane is None:
            # 最低限のフォールバック: window.cmd で実行（Fakeでの検証用）
            wobj = self._get_window_by_target("fallback:0")
            res = wobj.cmd(*base_args)  # type: ignore[attr-defined]
        else:
            res = pane.cmd(*base_args)  # type: ignore[attr-defined]
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
        """対象ウィンドウの pane_id 一覧を返す（server.cmd 経由）。"""
        server = self._ensure_server()
        target = f"{window_target}.0"
        res = server.cmd("list-panes", "-t", target, "-F", "#{pane_id}")  # type: ignore[attr-defined]
        out: list[str] = []
        for s in getattr(res, "stdout", []) or []:
            pid = str(s).strip()
            if pid:
                out.append(pid)
        return out

    def kill_other_panes(self, window_target: str) -> None:
        server = self._ensure_server()
        target = f"{window_target}.0"
        server.cmd("select-window", "-t", window_target)  # type: ignore[attr-defined]
        server.cmd("kill-pane", "-a", "-t", target)  # type: ignore[attr-defined]

    def _normalize_split_length(self, length: str | int | None, percent: int | None) -> str:
        """split-window の -l に渡す長さ文字列を正規化する。"""
        if length is None:
            if percent is None:
                raise ValueError("split length is required")
            return f"{percent}%"
        if isinstance(length, int):
            return str(length)
        return length

    def split_window(
        self,
        window_target: str,
        direction: str,
        length: str | int | None = None,
        *,
        percent: int | None = None,
    ) -> None:
        server = self._ensure_server()
        flag = "-h" if direction == "h" else "-v"
        target = f"{window_target}.0"
        split_length = self._normalize_split_length(length, percent)
        server.cmd("select-window", "-t", window_target)  # type: ignore[attr-defined]
        server.cmd("split-window", flag, "-l", split_length, "-t", target)  # type: ignore[attr-defined]

    def select_pane(self, pane_id: str) -> None:
        server = self._ensure_server()
        server.cmd("select-pane", "-t", pane_id)  # type: ignore[attr-defined]

    def split_pane(
        self,
        pane_id: str,
        direction: str,
        length: str | int | None = None,
        *,
        percent: int | None = None,
    ) -> None:
        server = self._ensure_server()
        flag = "-h" if direction == "h" else "-v"
        split_length = self._normalize_split_length(length, percent)
        server.cmd("split-window", flag, "-l", split_length, "-t", pane_id)  # type: ignore[attr-defined]

    def list_panes_detailed(self, window_target: str) -> list[tuple[str, int, int]]:
        server = self._ensure_server()
        res = server.cmd("list-panes", "-t", window_target, "-F", "#{pane_id} #{pane_left} #{pane_top}")  # type: ignore[attr-defined]
        out: list[tuple[str, int, int]] = []
        for line in getattr(res, "stdout", []) or []:
            text = str(line).strip()
            if not text:
                continue
            parts = text.split()
            if len(parts) != 3:
                continue
            pid, left, top = parts
            out.append((pid, int(left), int(top)))
        return out

    # ---- new helpers for renderer orchestration ----
    def list_windows_with_active(self, session_name: str) -> list[tuple[int, int]]:
        server = self._ensure_server()
        res = server.cmd("list-windows", "-t", session_name, "-F", "#{window_index} #{window_active}")  # type: ignore[attr-defined]
        out: list[tuple[int, int]] = []
        for line in getattr(res, "stdout", []) or []:
            text = str(line).strip()
            if not text:
                continue
            wi, act = text.split()
            out.append((int(wi), int(act)))
        return out

    def list_panes_in_window_with_active(self, session_name: str, window_index: int) -> list[tuple[int, int, str]]:
        server = self._ensure_server()
        target = f"{session_name}:{window_index}"
        res = server.cmd("list-panes", "-t", target, "-F", "#{pane_index} #{pane_active} #{pane_id}")  # type: ignore[attr-defined]
        out: list[tuple[int, int, str]] = []
        for line in getattr(res, "stdout", []) or []:
            text = str(line).strip()
            if not text:
                continue
            pi, act, pid = text.split()
            out.append((int(pi), int(act), pid))
        return out

    def resolve_active_pane(self, session_name: str) -> str | None:
        wins = self.list_windows_with_active(session_name)
        if not wins:
            return None
        wins_sorted = sorted(wins, key=lambda x: (0 if x[1] == 1 else 1, x[0]))
        win_idx = wins_sorted[0][0]
        panes = self.list_panes_in_window_with_active(session_name, win_idx)
        if not panes:
            return None
        panes_sorted = sorted(panes, key=lambda x: (0 if x[1] == 1 else 1, x[0]))
        return panes_sorted[0][2]
    
    def _calculate_content_freshness(self, content: str) -> int:
        """内容の新鮮さをスコア化。
        
        - ANSIエスケープシーケンスの存在
        - プロンプトの存在
        - 空でない行の数
        """
        if not content:
            return 0
        
        score = 0
        lines = content.split('\n')
        
        # 最後の10行を重視
        recent_lines = lines[-10:] if len(lines) > 10 else lines
        
        for line in recent_lines:
            if '\x1b[' in line:  # ANSIエスケープ
                score += 1
            if any(prompt in line for prompt in ['$', '>', '#', '%']):  # プロンプト
                score += 2
            if line.strip():  # 空でない行
                score += 0.5
        
        return int(score)
    
    def resolve_best_pane(self, session_name: str) -> str | None:
        """VS Codeターミナルでも確実に動作するインテリジェントpane選択。
        
        1. まず従来の方法を試す（パフォーマンスのため）
        2. 内容が空の場合、全paneをスキャン
        3. 内容の新鮮さで優先順位を決定
        """
        # Step 1: アクティブなwindow/paneがあるか確認
        wins = self.list_windows_with_active(session_name)
        has_active = any(win_active == 1 for _, win_active in wins)
        
        if has_active:
            # アクティブなwindow/paneがある場合は従来の方法を使う
            active_pane = self.resolve_active_pane(session_name)
            if active_pane:
                # 内容を確認
                try:
                    server = self._ensure_server()
                    # デフォルト値でキャプチャ
                    H = 50  # 仮の高さ
                    capture_lines = 100  # 固定値で簡略化
                    
                    res = server.cmd("capture-pane", "-p", "-e", "-S", f"-{capture_lines}", "-t", active_pane)
                    content = "".join(getattr(res, "stdout", []) or [])
                    
                    if content and len(content.strip()) > 0:
                        return active_pane
                except Exception:
                    pass
        
        # Step 2: 全window/paneをスキャン
        panes_with_content = []
        
        wins = self.list_windows_with_active(session_name)
        for win_idx, _ in wins:
            panes = self.list_panes_in_window_with_active(session_name, win_idx)
            for pane_idx, _, pane_id in panes:
                try:
                    server = self._ensure_server()
                    # より多くの履歴を取得
                    res = server.cmd("capture-pane", "-p", "-e", "-S", "-1000", "-t", pane_id)
                    content = "".join(getattr(res, "stdout", []) or [])
                    
                    if content and len(content.strip()) > 0:
                        freshness = self._calculate_content_freshness(content)
                        panes_with_content.append({
                            'pane_id': pane_id,
                            'content_length': len(content),
                            'freshness': freshness,
                            'window_index': win_idx,
                            'pane_index': pane_idx
                        })
                except Exception:
                    continue
        
        # Step 3: 最適なpaneを選択
        if panes_with_content:
            # 優先順位: 新鮮さ > window_index > pane_index
            best_pane = sorted(panes_with_content,
                             key=lambda x: (-x['freshness'],
                                          x['window_index'],
                                          x['pane_index']))[0]
            return best_pane['pane_id']
        
        # Step 4: フォールバック
        return f"{session_name}:0.0"

    def respawn_pane(self, pane_id: str, argv: list[str]) -> None:
        server = self._ensure_server()
        server.cmd("respawn-pane", "-k", "-t", pane_id, *argv)  # type: ignore[attr-defined]
    
    def create_session(self, session_name: str, detached: bool = True) -> None:
        """新しいtmuxセッションを作成する。"""
        server = self._ensure_server()
        args = ["new-session", "-s", session_name]
        if detached:
            args.append("-d")
        server.cmd(*args)  # type: ignore[attr-defined]
    
    def list_panes_with_titles(self, window_target: str) -> list[tuple[str, str]]:
        """指定ウィンドウのペインIDとタイトルのリストを返す。
        
        Returns:
            [(pane_id, pane_title), ...]
        """
        window = self._get_window_by_target(window_target)
        if not window:
            return []
        
        out: list[tuple[str, str]] = []
        panes = getattr(window, "panes", [])
        for pane in panes:
            pane_id = getattr(pane, "id", "")
            # libtmuxではpane_titleプロパティがない場合があるので、cmdで取得
            try:
                res = pane.cmd("display-message", "-p", "#{pane_title}")  # type: ignore[attr-defined]
                title = str(getattr(res, "stdout", [""])[0]).strip() if hasattr(res, "stdout") else ""
            except Exception:
                title = getattr(pane, "pane_title", "")
            out.append((pane_id, title))
        return out

    


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

    def split_window(
        self,
        window_target: str,
        direction: str,
        length: str | int | None = None,
        *,
        percent: int | None = None,
    ) -> None:
        """指定方向に分割する。direction: 'h'（水平）/ 'v'（垂直）。"""
        return self.driver.split_window(window_target, direction, length, percent=percent)

    def select_pane(self, pane_id: str) -> None:
        """対象の pane を選択する。"""
        return self.driver.select_pane(pane_id)

    def split_pane(
        self,
        pane_id: str,
        direction: str,
        length: str | int | None = None,
        *,
        percent: int | None = None,
    ) -> None:
        """対象の pane を分割する。"""
        return self.driver.split_pane(pane_id, direction, length, percent=percent)

    def list_panes_detailed(self, window_target: str) -> list[tuple[str, int, int]]:
        """pane の (id, left, top) を返す。"""
        return self.driver.list_panes_detailed(window_target)

    # ---- new helpers ----
    def resolve_active_pane(self, session_name: str) -> str | None:
        """各セッションで表示対象とする pane_id を決定する。"""
        return self.driver.resolve_active_pane(session_name)
    
    def resolve_best_pane(self, session_name: str) -> str | None:
        """VS Codeターミナルでも確実に動作するインテリジェントpane選択。"""
        return self.driver.resolve_best_pane(session_name)

    def respawn_pane(self, pane_id: str, argv: list[str]) -> None:
        """pane 内のプログラムを指定コマンドで再起動する。"""
        return self.driver.respawn_pane(pane_id, argv)
    
    def create_session(self, session_name: str, detached: bool = True) -> None:
        """新しいtmuxセッションを作成する。"""
        return self.driver.create_session(session_name, detached)
    
    def list_panes_with_titles(self, window_target: str) -> list[tuple[str, str]]:
        """指定ウィンドウのペインIDとタイトルのリストを返す。"""
        return self.driver.list_panes_with_titles(window_target)


def create_from_config(cfg) -> TmuxIO:
    """設定に基づきドライバを選び `TmuxIO` を構築する。"""
    drv_name = (getattr(cfg, "tmux", None) and cfg.tmux.driver) or "libtmux"
    if drv_name == "cli":
        driver = CliDriver(cfg=cfg)
    else:
        driver = LibtmuxDriver(cfg=cfg, socket_name=getattr(cfg.tmux, "socket_name", None), socket_path=getattr(cfg.tmux, "socket_path", None))
    return TmuxIO(driver=driver)
