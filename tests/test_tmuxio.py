"""tmux I/O ドライバ（libtmux/cli）の挙動テスト。

目的:
- 設定に応じたドライバ選択（libtmux/cli）。
- 主要APIの呼び出し内容（list_sessions/window_size/capture_pane/set_window_option/set_pane_title）。
"""

from __future__ import annotations

import types


def _fake_completed(stdout: str):
    c = types.SimpleNamespace()
    c.returncode = 0
    c.stdout = stdout.encode()
    c.stderr = b""
    return c


def test_driver_selection(monkeypatch):
    """config.tmux.driver に応じてドライバが選択される。"""
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    c = config.load_config(None)
    c.tmux.driver = "cli"
    io = tmuxio.create_from_config(c)
    assert isinstance(io.driver, tmuxio.CliDriver)

    c.tmux.driver = "libtmux"
    io = tmuxio.create_from_config(c)
    assert isinstance(io.driver, tmuxio.LibtmuxDriver)


def test_cli_list_sessions_and_window_size(monkeypatch):
    """CLIドライバはtmuxコマンドを正しく組み立てて実行する。"""
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    captured = []

    def fake_run(args, capture_output=True, check=True):
        cmd = " ".join(args)
        captured.append(cmd)
        if "list-sessions" in cmd:
            return _fake_completed("s1\ns2\n")
        if "display-message" in cmd:
            return _fake_completed("120 60\n")
        raise AssertionError("unexpected command: " + cmd)

    monkeypatch.setattr(tmuxio, "_run_subprocess", fake_run)

    c = config.load_config(None)
    c.tmux.driver = "cli"
    io = tmuxio.create_from_config(c)

    sessions = io.list_sessions()
    assert sessions == ["s1", "s2"]
    w, h = io.window_size("dashboard:0")
    assert (w, h) == (120, 60)
    # コマンド構築の確認
    assert "tmux list-sessions -F" in captured[0]
    assert "tmux display-message -p -t dashboard:0" in captured[1]


def test_cli_capture_and_set_options(monkeypatch):
    """CLIドライバの capture-pane / set-option -w / select-pane -T を検証する。"""
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    issued = []

    def fake_run(args, capture_output=True, check=True):
        cmd = " ".join(args)
        issued.append(cmd)
        if "capture-pane" in cmd:
            return _fake_completed("hello\n")
        return _fake_completed("")

    monkeypatch.setattr(tmuxio, "_run_subprocess", fake_run)

    c = config.load_config(None)
    c.tmux.driver = "cli"
    io = tmuxio.create_from_config(c)

    out = io.capture_pane("%1", H=10, join_wrapped=True)
    assert "capture-pane -p -e -J -S -10 -E -1 -t %1" in issued[0]
    assert "hello" in out

    io.set_window_option("dashboard:0", "pane-border-status", "top")
    assert "set-option -w -t dashboard:0 pane-border-status top" in issued[1]

    io.set_pane_title("%1", "alpha")
    assert "select-pane -t %1 -T alpha" in issued[2]


def test_libtmux_calls_use_cmd(monkeypatch):
    """libtmuxドライバは obj.cmd(...) を用いて必要な引数で呼び出す。"""
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    # フェイクのlibtmuxサーバ/ウィンドウ/ペイン
    pane_calls = []
    window_calls = []
    server_calls = []

    class FakeCmdResult:
        def __init__(self, stdout):
            self.stdout = stdout

    class FakePane:
        def cmd(self, *args):
            pane_calls.append(list(args))
            if args[0] == "capture-pane":
                return FakeCmdResult(["ok\n"])
            return FakeCmdResult([""])

    class FakeWindow:
        def __init__(self):
            self.window_width = "120"
            self.window_height = "50"

        def cmd(self, *args):
            window_calls.append(list(args))
            return FakeCmdResult([""])

    class FakeServer:
        def __init__(self):
            self._pane = FakePane()
            self._window = FakeWindow()
            # sessions 構造（未使用）
            self.sessions = []

        def cmd(self, *args):
            server_calls.append(list(args))
            return FakeCmdResult([""])

    # ドライバの内部オブジェクトを差し替え
    c = config.load_config(None)
    c.tmux.driver = "libtmux"
    io = tmuxio.create_from_config(c)
    io.driver._server = FakeServer()  # type: ignore[attr-defined]

    # 呼び出し
    _ = io.capture_pane("%9", H=5, join_wrapped=False)
    io.set_window_option("dashboard:0", "pane-border-status", "top")
    io.set_pane_title("%9", "name")
    w, h = io.window_size("dashboard:0")

    # 検証（select-pane は server.cmd 側で呼び出す実装）
    assert pane_calls[0] == ["capture-pane", "-p", "-e", "-S", "-5", "-E", "-1", "-t", "%9"]
    assert window_calls[0] == ["set-option", "-w", "-t", "dashboard:0", "pane-border-status", "top"]
    assert ["select-pane", "-t", "%9", "-T", "name"] in server_calls
    assert (w, h) == (120, 50)


def test_libtmux_window_target_resolution(monkeypatch):
    """libtmuxドライバが 'sess:0' の target から Window/Panes を解決する。"""
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    class Obj:
        pass

    class FakePane:
        def __init__(self, pid):
            self.pane_id = pid

    class FakeWindow:
        def __init__(self, idx, w, h, panes):
            self.window_index = str(idx)
            self.window_width = str(w)
            self.window_height = str(h)
            self.panes = [FakePane(p) for p in panes]

        def cmd(self, *args):
            return Obj()

    class FakeSession:
        def __init__(self, name, windows):
            self.session_name = name
            self.windows = windows

    class FakeServer:
        def __init__(self):
            self.sessions = [FakeSession("sess", [FakeWindow(0, 80, 25, ["%X", "%Y"])])]

    c = config.load_config(None)
    c.tmux.driver = "libtmux"
    io = tmuxio.create_from_config(c)
    io.driver._server = FakeServer()  # type: ignore[attr-defined]

    w, h = io.window_size("sess:0")
    assert (w, h) == (80, 25)
    assert io.list_panes("sess:0") == ["%X", "%Y"]


def test_libtmux_respects_socket_options(monkeypatch):
    """libtmux.Server 作成時に socket_name/path を反映する。"""
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    created = {}

    class FakeLibTmux:
        class Server:
            def __init__(self, **kwargs):
                created.update(kwargs)

    monkeypatch.setattr(tmuxio, "libtmux", FakeLibTmux)

    c = config.load_config(None)
    c.tmux.driver = "libtmux"
    c.tmux.socket_name = "mysock"
    c.tmux.socket_path = "/tmp/tmux-1000/default"
    io = tmuxio.create_from_config(c)
    _ = io.driver._ensure_server()  # type: ignore[attr-defined]
    assert created.get("socket_name") == "mysock"
    assert created.get("socket_path") == "/tmp/tmux-1000/default"


def test_cli_panes_and_split_commands(monkeypatch):
    """CLIドライバの list-panes / kill-pane -a / split-window のコマンドを検証する。"""
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    issued = []

    def fake_run(args, capture_output=True, check=True):
        cmd = " ".join(args)
        issued.append(cmd)
        if "list-panes" in cmd:
            return _fake_completed("%1\n%2\n")
        return _fake_completed("")

    monkeypatch.setattr(tmuxio, "_run_subprocess", fake_run)

    c = config.load_config(None)
    c.tmux.driver = "cli"
    io = tmuxio.create_from_config(c)

    panes = io.list_panes("dashboard:0")
    assert panes == ["%1", "%2"]

    io.kill_other_panes("dashboard:0")
    assert any("kill-pane -a -t dashboard:0" in x for x in issued)

    io.split_window("dashboard:0", direction="h", percent=33)
    assert any("split-window -h -p 33 -t dashboard:0" in x for x in issued)
    io.split_window("dashboard:0", direction="v", percent=50)
    assert any("split-window -v -p 50 -t dashboard:0" in x for x in issued)


def test_libtmux_panes_and_split_calls():
    """libtmuxドライバの list_panes / kill_other_panes / split_window 呼び出しを検証する。"""
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    window_calls = []

    class FakeCmdResult:
        def __init__(self, stdout):
            self.stdout = stdout

    class FakeWindow:
        def __init__(self):
            self.window_width = "100"
            self.window_height = "40"
            self.panes = ["%A", "%B"]

        def cmd(self, *args):
            window_calls.append(list(args))
            return FakeCmdResult([""])

    class FakeServer:
        def __init__(self):
            self._window = FakeWindow()
            self._pane = None

    c = config.load_config(None)
    c.tmux.driver = "libtmux"
    io = tmuxio.create_from_config(c)
    io.driver._server = FakeServer()  # type: ignore[attr-defined]

    panes = io.list_panes("dashboard:0")
    assert panes == ["%A", "%B"]

    io.kill_other_panes("dashboard:0")
    assert ["kill-pane", "-a", "-t", "dashboard:0"] in window_calls

    io.split_window("dashboard:0", direction="h", percent=25)
    assert ["split-window", "-h", "-p", "25", "-t", "dashboard:0"] in window_calls
    io.split_window("dashboard:0", direction="v", percent=75)
    assert ["split-window", "-v", "-p", "75", "-t", "dashboard:0"] in window_calls
