"""tmux I/O ドライバ（libtmux/cli）の挙動テスト。

目的:
- 設定に応じたドライバ選択（libtmux/cli）。
- 主要APIの呼び出し内容（list_sessions/window_size/capture_pane/set_window_option/set_pane_title）。
"""

from __future__ import annotations

import types
import pytest


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
    # H=10の場合、デフォルト設定では max(10*2, 10+20) = 30行を取得
    assert "capture-pane -p -e -J -S -30 -t %1" in issued[0]
    assert "hello" in out

    io.set_window_option("dashboard:0", "pane-border-status", "top")
    assert "set-option -w -t dashboard:0 pane-border-status top" in issued[1]

    io.set_pane_title("%1", "alpha")
    assert "select-pane -t %1 -T alpha" in issued[2]


def test_cli_get_and_set_window_option(monkeypatch):
    """目的: CLI経路の window option 取得/設定契約を確認する。
    前提: show-options が `window-size manual` を返す。
    期待: get は `manual` を返し、set は `-w` で `latest` を設定する。
    """
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    issued = []

    def fake_run(args, capture_output=True, check=True):
        issued.append(" ".join(args))
        if args[:3] == ["tmux", "show-options", "-w"]:
            return _fake_completed("window-size manual\n")
        return _fake_completed("")

    monkeypatch.setattr(tmuxio, "_run_subprocess", fake_run)

    c = config.load_config(None)
    c.tmux.driver = "cli"
    io = tmuxio.create_from_config(c)

    current = io.get_window_option("dashboard:0", "window-size")
    io.set_window_option("dashboard:0", "window-size", "latest")

    assert current == "manual"
    assert any("show-options -w -t dashboard:0 window-size" in cmd for cmd in issued)
    assert any("set-option -w -t dashboard:0 window-size latest" in cmd for cmd in issued)


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

    # 検証（set-option / select-pane は server.cmd 側で呼び出す実装）
    # H=5の場合、デフォルト設定では max(5*2, 5+20) = 25行を取得
    assert pane_calls[0] == ["capture-pane", "-p", "-e", "-S", "-25", "-t", "%9"]
    assert ["set-option", "-w", "-t", "dashboard:0", "pane-border-status", "top"] in server_calls
    assert ["select-pane", "-t", "%9", "-T", "name"] in server_calls
    assert (w, h) == (120, 50)


def test_libtmux_get_and_set_window_option():
    """目的: libtmux経路の window option 取得/設定契約を確認する。
    前提: show-options が `window-size manual` を返す。
    期待: get は `manual` を返し、set は `-w` で `latest` を設定する。
    """
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    server_calls = []

    class FakeResult:
        def __init__(self, stdout=None, stderr=None, returncode=0):
            self.stdout = stdout or [""]
            self.stderr = stderr or [""]
            self.returncode = returncode

    class FakeServer:
        def cmd(self, *args):
            server_calls.append(list(args))
            if args[:4] == ("show-options", "-w", "-t", "dashboard:0"):
                return FakeResult(stdout=["window-size manual"])
            return FakeResult()

    c = config.load_config(None)
    c.tmux.driver = "libtmux"
    io = tmuxio.create_from_config(c)
    io.driver._server = FakeServer()  # type: ignore[attr-defined]

    current = io.get_window_option("dashboard:0", "window-size")
    io.set_window_option("dashboard:0", "window-size", "latest")

    assert current == "manual"
    assert ["show-options", "-w", "-t", "dashboard:0", "window-size"] in server_calls
    assert ["set-option", "-w", "-t", "dashboard:0", "window-size", "latest"] in server_calls


def test_libtmux_get_window_option_fail_closed_on_tmux_failure():
    """目的: libtmux経路の get_window_option が失敗時に fail-closed になることを確認する。
    前提: show-options が returncode 異常を返す。
    期待: RuntimeError を送出し、サイレントに空値を返さない。
    """
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    class FakeResult:
        def __init__(self, stdout=None, stderr=None, returncode=0):
            self.stdout = stdout or [""]
            self.stderr = stderr or [""]
            self.returncode = returncode

    class FakeServer:
        def cmd(self, *args):
            return FakeResult(returncode=1)

    c = config.load_config(None)
    c.tmux.driver = "libtmux"
    io = tmuxio.create_from_config(c)
    io.driver._server = FakeServer()  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError):
        io.get_window_option("dashboard:0", "window-size")


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
            self._calls = []

        def cmd(self, *args):
            self._calls.append(list(args))
            # emulate list-panes output
            if args and args[0] == "list-panes":
                class R:
                    stdout = ["%X", "%Y"]
                return R()
            class R:
                stdout = [""]
            return R()

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
    """CLIドライバの list-panes / kill-pane -a / split-window(-l) を検証する。"""
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

    io.split_window("dashboard:0", direction="h", length="40")
    assert any("split-window -h -l 40 -t dashboard:0.0" in x for x in issued)
    io.split_window("dashboard:0", direction="v", length="50%")
    assert any("split-window -v -l 50% -t dashboard:0.0" in x for x in issued)
    # 既存呼び出し互換: percent 指定は `%` へ変換される
    io.split_window("dashboard:0", direction="h", percent=33)
    assert any("split-window -h -l 33% -t dashboard:0.0" in x for x in issued)

    io.split_pane("%1", direction="h", length="12")
    assert any("split-window -h -l 12 -t %1" in x for x in issued)
    io.split_pane("%1", direction="v", length="60%")
    assert any("split-window -v -l 60% -t %1" in x for x in issued)
    # 既存呼び出し互換: percent 指定は `%` へ変換される
    io.split_pane("%1", direction="h", percent=45)
    assert any("split-window -h -l 45% -t %1" in x for x in issued)


def test_libtmux_panes_and_split_calls():
    """libtmuxドライバの list_panes / kill_other_panes / split_window(-l) を検証する。"""
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    window_calls = []
    server_calls = []

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
            self._calls = []

        def cmd(self, *args):
            server_calls.append(list(args))
            if args and args[0] == "list-panes":
                class R:
                    stdout = ["%A", "%B"]
                return R()
            class R:
                stdout = [""]
            return R()

    c = config.load_config(None)
    c.tmux.driver = "libtmux"
    io = tmuxio.create_from_config(c)
    io.driver._server = FakeServer()  # type: ignore[attr-defined]

    panes = io.list_panes("dashboard:0")
    assert panes == ["%A", "%B"]

    io.kill_other_panes("dashboard:0")
    # server.cmd 経由で呼び出される
    assert ["kill-pane", "-a", "-t", "dashboard:0.0"] in server_calls

    io.split_window("dashboard:0", direction="h", length="25")
    assert ["split-window", "-h", "-l", "25", "-t", "dashboard:0.0"] in server_calls
    io.split_window("dashboard:0", direction="v", length="75%")
    assert ["split-window", "-v", "-l", "75%", "-t", "dashboard:0.0"] in server_calls
    # 既存呼び出し互換: percent 指定は `%` へ変換される
    io.split_window("dashboard:0", direction="h", percent=40)
    assert ["split-window", "-h", "-l", "40%", "-t", "dashboard:0.0"] in server_calls

    io.split_pane("%A", direction="h", length="10")
    assert ["split-window", "-h", "-l", "10", "-t", "%A"] in server_calls
    io.split_pane("%A", direction="v", length="65%")
    assert ["split-window", "-v", "-l", "65%", "-t", "%A"] in server_calls
    # 既存呼び出し互換: percent 指定は `%` へ変換される
    io.split_pane("%A", direction="h", percent=35)
    assert ["split-window", "-h", "-l", "35%", "-t", "%A"] in server_calls


def test_cli_split_raises_value_error_when_length_and_percent_missing(monkeypatch):
    """目的: CLI経路の split 系入力検証を確認する。
    前提: length と percent をどちらも渡さない。
    期待: split_window / split_pane が ValueError を送出し、tmuxコマンドは実行されない。
    """
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    def fake_run(args, capture_output=True, check=True):
        raise AssertionError("split入力エラー時にtmux実行が呼ばれてはいけない")

    monkeypatch.setattr(tmuxio, "_run_subprocess", fake_run)

    c = config.load_config(None)
    c.tmux.driver = "cli"
    io = tmuxio.create_from_config(c)

    with pytest.raises(ValueError):
        io.split_window("dashboard:0", direction="h")
    with pytest.raises(ValueError):
        io.split_pane("%1", direction="v")


def test_libtmux_split_raises_value_error_when_length_and_percent_missing():
    """目的: libtmux経路の split 系入力検証を確認する。
    前提: length と percent をどちらも渡さない。
    期待: split_window / split_pane が ValueError を送出し、server.cmd は呼ばれない。
    """
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    server_calls = []

    class FakeServer:
        def cmd(self, *args):
            server_calls.append(list(args))
            class R:
                stdout = [""]
            return R()

    c = config.load_config(None)
    c.tmux.driver = "libtmux"
    io = tmuxio.create_from_config(c)
    io.driver._server = FakeServer()  # type: ignore[attr-defined]

    with pytest.raises(ValueError):
        io.split_window("dashboard:0", direction="h")
    with pytest.raises(ValueError):
        io.split_pane("%A", direction="v")

    assert server_calls == []


def test_cli_window_lifecycle_commands(monkeypatch):
    """目的: CLI経路の window lifecycle API を確認する。
    前提: create/swap/kill を順に実行する。
    期待: tmux の new-window/swap-window/kill-window が正しい引数で呼ばれる。
    """
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    issued = []

    def fake_run(args, capture_output=True, check=True):
        issued.append(" ".join(args))
        if args[:3] == ["tmux", "list-panes", "-t"]:
            return _fake_completed("%9\n")
        return _fake_completed("")

    monkeypatch.setattr(tmuxio, "_run_subprocess", fake_run)

    c = config.load_config(None)
    c.tmux.driver = "cli"
    io = tmuxio.create_from_config(c)

    target = io.create_window("dashboard", 99, detached=True, width=120, height=50)
    io.swap_window("dashboard:99", "dashboard:0")
    io.kill_window("dashboard:99")

    assert target == "dashboard:99"
    assert any("new-window -d -P -F #{session_name}:#{window_index} -t dashboard:99" in cmd for cmd in issued)
    assert any("resize-window -t dashboard:99 -x 120 -y 50" in cmd for cmd in issued)
    assert any("list-panes -t dashboard:99 -F #{pane_id}" in cmd for cmd in issued)
    assert any("swap-window -s dashboard:99 -t dashboard:0" in cmd for cmd in issued)
    assert any("kill-window -t dashboard:99" in cmd for cmd in issued)


def test_libtmux_window_lifecycle_calls():
    """目的: libtmux経路の window lifecycle API を確認する。
    前提: create/swap/kill を順に実行する。
    期待: server.cmd が対応コマンドで呼ばれる。
    """
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    server_calls = []

    class FakeServer:
        def cmd(self, *args):
            server_calls.append(list(args))

            class R:
                stdout = ["%9"] if args[:3] == ("list-panes", "-t", "dashboard:99") else [""]
                stderr = [""]
                returncode = 0

            return R()

    c = config.load_config(None)
    c.tmux.driver = "libtmux"
    io = tmuxio.create_from_config(c)
    io.driver._server = FakeServer()  # type: ignore[attr-defined]

    target = io.create_window("dashboard", 99, detached=True, width=120, height=50)
    io.swap_window("dashboard:99", "dashboard:0")
    io.kill_window("dashboard:99")

    assert target == "dashboard:99"
    assert [
        "new-window",
        "-d",
        "-P",
        "-F",
        "#{session_name}:#{window_index}",
        "-t",
        "dashboard:99",
    ] in server_calls
    assert ["list-panes", "-t", "dashboard:99", "-F", "#{pane_id}"] in server_calls
    assert ["resize-window", "-t", "dashboard:99", "-x", "120", "-y", "50"] in server_calls
    assert ["swap-window", "-s", "dashboard:99", "-t", "dashboard:0"] in server_calls
    assert ["kill-window", "-t", "dashboard:99"] in server_calls


def test_cli_create_window_raises_when_created_target_does_not_exist(monkeypatch):
    """目的: CLI経路の create_window が phantom target を返さず fail-closed になることを確認する。
    前提: new-window 自体は成功するが、作成後の target 実在確認では pane が見つからない。
    期待: create_window は例外を送出し、存在しない target を返さない。
    """
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    issued = []

    def fake_run(args, capture_output=True, check=True):
        issued.append(" ".join(args))
        if args[:3] == ["tmux", "list-panes", "-t"]:
            return _fake_completed("")
        return _fake_completed("")

    monkeypatch.setattr(tmuxio, "_run_subprocess", fake_run)

    c = config.load_config(None)
    c.tmux.driver = "cli"
    io = tmuxio.create_from_config(c)

    with pytest.raises(RuntimeError, match="dashboard:99"):
        io.create_window("dashboard", 99, detached=True)

    assert any("new-window -d -P -F #{session_name}:#{window_index} -t dashboard:99" in cmd for cmd in issued)
    assert any("list-panes -t dashboard:99 -F #{pane_id}" in cmd for cmd in issued)


def test_libtmux_create_window_raises_on_returncode_stderr_and_missing_target():
    """目的: libtmux経路の create_window が失敗要因ごとに fail-closed になることを確認する。
    前提: returncode異常、stderr出力、target未作成の3条件を順に与える。
    期待: いずれも例外を送出し、phantom target を返さない。
    """
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    class FakeResult:
        def __init__(self, stdout=None, stderr=None, returncode=0):
            self.stdout = stdout or [""]
            self.stderr = stderr or [""]
            self.returncode = returncode

    class FakeServer:
        def __init__(self):
            self.calls = []
            self.mode = "returncode"

        def cmd(self, *args):
            self.calls.append(list(args))
            if args[0] == "new-window":
                if self.mode == "returncode":
                    return FakeResult(returncode=1)
                if self.mode == "stderr":
                    return FakeResult(stderr=["create window failed: index 0 in use"])
                return FakeResult(stdout=["dashboard:99"])
            if args[0] == "list-panes":
                return FakeResult(stdout=[""])
            return FakeResult()

    c = config.load_config(None)
    c.tmux.driver = "libtmux"
    io = tmuxio.create_from_config(c)
    server = FakeServer()
    io.driver._server = server  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError):
        io.create_window("dashboard", 99, detached=True)

    server.mode = "stderr"
    with pytest.raises(RuntimeError, match="index 0 in use"):
        io.create_window("dashboard", 99, detached=True)

    server.mode = "missing"
    with pytest.raises(RuntimeError, match="dashboard:99"):
        io.create_window("dashboard", 99, detached=True)

    assert ["new-window", "-d", "-P", "-F", "#{session_name}:#{window_index}", "-t", "dashboard:99"] in server.calls
    assert ["list-panes", "-t", "dashboard:99", "-F", "#{pane_id}"] in server.calls


def test_libtmux_swap_and_kill_window_raise_on_tmux_failure():
    """目的: libtmux経路の swap_window / kill_window も fail-closed で例外化されることを確認する。
    前提: tmux command が returncode 異常または stderr を返す。
    期待: swap_window / kill_window は silent success にならず RuntimeError を送出する。
    """
    from tmux_dashboard import tmuxio
    from tmux_dashboard import config

    class FakeResult:
        def __init__(self, *, stdout=None, stderr=None, returncode=0):
            self.stdout = stdout or [""]
            self.stderr = stderr or [""]
            self.returncode = returncode

    class FakeServer:
        def __init__(self):
            self.calls = []
            self.swap_mode = "returncode"
            self.kill_mode = "stderr"

        def cmd(self, *args):
            self.calls.append(list(args))
            if args[0] == "swap-window":
                if self.swap_mode == "returncode":
                    return FakeResult(returncode=1)
                return FakeResult(stderr=["swap window failed"])
            if args[0] == "kill-window":
                if self.kill_mode == "returncode":
                    return FakeResult(returncode=1)
                return FakeResult(stderr=["kill window failed"])
            return FakeResult()

    c = config.load_config(None)
    c.tmux.driver = "libtmux"
    io = tmuxio.create_from_config(c)
    server = FakeServer()
    io.driver._server = server  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError):
        io.swap_window("dashboard:99", "dashboard:0")

    server.swap_mode = "stderr"
    with pytest.raises(RuntimeError, match="swap window failed"):
        io.swap_window("dashboard:99", "dashboard:0")

    server.kill_mode = "returncode"
    with pytest.raises(RuntimeError):
        io.kill_window("dashboard:99")

    server.kill_mode = "stderr"
    with pytest.raises(RuntimeError, match="kill window failed"):
        io.kill_window("dashboard:99")

    assert ["swap-window", "-s", "dashboard:99", "-t", "dashboard:0"] in server.calls
    assert ["kill-window", "-t", "dashboard:99"] in server.calls
