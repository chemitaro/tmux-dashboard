"""CLI エントリ（__main__）のテスト。

目的:
- --config の解釈と load_config 呼び出し引数。
- Orchestrator.run_once の呼び出し回数（--once/--iterations）。
- Ctrl-C（KeyboardInterrupt）を安全に処理して 0 終了する。
"""

from __future__ import annotations


def test_cli_runs_with_config_and_iterations(monkeypatch, tmp_path):
    """--config と --iterations を解釈し、Orchestrator.run_once を所定回数呼ぶ。"""
    # 偽のロード/生成/オーケストレータ
    load_args = {"path": None}

    class FakeCfg:
        poll_interval_sec = 0
        
        class logging:
            dir = "~/.local/state/tmux-dashboard"
            level = "INFO"
            rotate_max_bytes = 10485760
            rotate_backup_count = 5

    def fake_load(path):
        load_args["path"] = path
        return FakeCfg()

    class FakeIO:
        def list_sessions(self):
            return []
        def create_session(self, name, detached=True):
            pass

    created = {"count": 0}

    def fake_create(cfg):
        created["count"] += 1
        return FakeIO()

    runs = {"count": 0}

    class FakeOrch:
        def __init__(self, io, cfg):
            self.io = io
            self.cfg = cfg

        def run_once(self, window_target="dashboard:0"):
            runs["count"] += 1
            return {"ok": True}

    from tmux_dashboard import __main__ as cli

    cfgfile = tmp_path / "x.yaml"
    cfgfile.write_text("min_tile_width: 40\n", encoding="utf-8")

    monkeypatch.setattr(cli, "config", type("M", (), {"load_config": staticmethod(fake_load)}))
    monkeypatch.setattr(cli, "tmuxio", type("M", (), {"create_from_config": staticmethod(fake_create)}))
    monkeypatch.setattr(cli, "orchestrator", type("M", (), {"Orchestrator": FakeOrch}))

    rc = cli.main(["--config", str(cfgfile), "--once", "--iterations", "3"])
    assert rc == 0
    assert load_args["path"] == str(cfgfile)
    assert created["count"] == 1
    assert runs["count"] == 3


def test_cli_uses_default_when_no_config(monkeypatch):
    """--config 未指定時は load_config(None) を呼ぶ。"""
    called = {"path": "not-called"}

    class FakeCfg:
        poll_interval_sec = 0
        
        class logging:
            dir = "~/.local/state/tmux-dashboard"
            level = "INFO"
            rotate_max_bytes = 10485760
            rotate_backup_count = 5

    def fake_load(path):
        called["path"] = path
        return FakeCfg()

    class FakeOrch:
        def __init__(self, io, cfg):
            pass

        def run_once(self, window_target="dashboard:0"):
            return {"ok": True}

    from tmux_dashboard import __main__ as cli
    class FakeIO2:
        def list_sessions(self):
            return []
        def create_session(self, name, detached=True):
            pass
    
    monkeypatch.setattr(cli, "config", type("M", (), {"load_config": staticmethod(fake_load)}))
    monkeypatch.setattr(cli, "tmuxio", type("M", (), {"create_from_config": staticmethod(lambda _cfg: FakeIO2())}))
    monkeypatch.setattr(cli, "orchestrator", type("M", (), {"Orchestrator": FakeOrch}))

    rc = cli.main(["--once"])  # config未指定
    assert rc == 0
    assert called["path"] is None


def test_cli_handles_keyboard_interrupt(monkeypatch):
    """KeyboardInterrupt を受けたら 0 終了する。"""
    class FakeCfg:
        poll_interval_sec = 0
        
        class logging:
            dir = "~/.local/state/tmux-dashboard"
            level = "INFO"
            rotate_max_bytes = 10485760
            rotate_backup_count = 5

    from tmux_dashboard import __main__ as cli
    
    class FakeIO3:
        def list_sessions(self):
            return []
        def create_session(self, name, detached=True):
            pass

    monkeypatch.setattr(cli, "config", type("M", (), {"load_config": staticmethod(lambda p: FakeCfg())}))
    monkeypatch.setattr(cli, "tmuxio", type("M", (), {"create_from_config": staticmethod(lambda _cfg: FakeIO3())}))

    class FakeOrch:
        def __init__(self, io, cfg):
            pass

        def run_once(self, window_target="dashboard:0"):
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, "orchestrator", type("M", (), {"Orchestrator": FakeOrch}))

    rc = cli.main(["--once", "--iterations", "5"])  # 1回目でKeyboardInterrupt
    assert rc == 0


def test_cli_once_keeps_exit_zero_and_logs_create_window_failure(monkeypatch):
    """目的: --once 実行中の create-window failure でも exit 0 と error ログを維持することを確認する。"""
    import logging
    from tmux_dashboard import __main__ as cli

    class FakeCfg:
        poll_interval_sec = 0

        class logging:
            dir = "~/.local/state/tmux-dashboard"
            level = "INFO"
            rotate_max_bytes = 10485760
            rotate_backup_count = 5

    class FakeIO:
        def list_sessions(self):
            return []

        def create_session(self, name, detached=True):
            pass

    class FakeOrch:
        def __init__(self, io, cfg):
            pass

        def run_once(self, window_target="dashboard:0"):
            raise RuntimeError("create-window failed: window_target=dashboard:0 staging_target=dashboard:99")

    monkeypatch.setattr(cli, "config", type("M", (), {"load_config": staticmethod(lambda p: FakeCfg())}))
    monkeypatch.setattr(cli, "tmuxio", type("M", (), {"create_from_config": staticmethod(lambda _cfg: FakeIO())}))
    monkeypatch.setattr(cli, "orchestrator", type("M", (), {"Orchestrator": FakeOrch}))
    monkeypatch.setattr(cli, "logging_setup", type("M", (), {"setup_logging": staticmethod(lambda _cfg: None)}))
    monkeypatch.setattr(cli, "session_manager", type("M", (), {"ensure_dashboard_session": staticmethod(lambda _io: False)}))

    messages = []
    original_get_logger = logging.getLogger
    fake_logger = type(
        "L",
        (),
        {"error": lambda self, fmt, *args: messages.append(fmt % args)},
    )()
    monkeypatch.setattr(
        logging,
        "getLogger",
        lambda name=None: fake_logger if name == "tmux_dashboard.main" else original_get_logger(name),
    )

    rc = cli.main(["--once"])
    assert rc == 0
    assert any("create-window failed" in message for message in messages)


def test_cli_loop_keeps_exit_zero_and_logs_swap_window_failure(monkeypatch):
    """目的: 通常ループ中の swap-window failure でも exit 0 と error ログを維持することを確認する。"""
    import logging
    from tmux_dashboard import __main__ as cli

    class FakeCfg:
        poll_interval_sec = 0

        class logging:
            dir = "~/.local/state/tmux-dashboard"
            level = "INFO"
            rotate_max_bytes = 10485760
            rotate_backup_count = 5

    class FakeIO:
        def list_sessions(self):
            return []

        def create_session(self, name, detached=True):
            pass

    class FakeOrch:
        def __init__(self, io, cfg):
            self.calls = 0

        def run_once(self, window_target="dashboard:0"):
            raise RuntimeError("swap-window failed: window_target=dashboard:0 staging_target=dashboard:99")

    ensure_calls = {"count": 0}

    def fake_ensure(_io):
        ensure_calls["count"] += 1
        if ensure_calls["count"] >= 3:
            raise KeyboardInterrupt
        return False

    monkeypatch.setattr(cli, "config", type("M", (), {"load_config": staticmethod(lambda p: FakeCfg())}))
    monkeypatch.setattr(cli, "tmuxio", type("M", (), {"create_from_config": staticmethod(lambda _cfg: FakeIO())}))
    monkeypatch.setattr(cli, "orchestrator", type("M", (), {"Orchestrator": FakeOrch}))
    monkeypatch.setattr(cli, "logging_setup", type("M", (), {"setup_logging": staticmethod(lambda _cfg: None)}))
    monkeypatch.setattr(cli, "session_manager", type("M", (), {"ensure_dashboard_session": staticmethod(fake_ensure)}))

    messages = []
    original_get_logger = logging.getLogger
    fake_logger = type(
        "L",
        (),
        {"error": lambda self, fmt, *args: messages.append(fmt % args)},
    )()
    monkeypatch.setattr(
        logging,
        "getLogger",
        lambda name=None: fake_logger if name == "tmux_dashboard.main" else original_get_logger(name),
    )

    rc = cli.main([])
    assert rc == 0
    assert any("swap-window failed" in message for message in messages)


def test_cli_once_keeps_exit_zero_when_run_once_logs_failure_and_returns(monkeypatch):
    """目的: run_once が内部で失敗ログを出して正常 return しても CLI が exit 0 を維持し、失敗詳細が観測できることを確認する。"""
    import logging
    from tmux_dashboard import __main__ as cli

    class FakeCfg:
        poll_interval_sec = 0

        class logging:
            dir = "~/.local/state/tmux-dashboard"
            level = "INFO"
            rotate_max_bytes = 10485760
            rotate_backup_count = 5

    class FakeIO:
        def list_sessions(self):
            return []

        def create_session(self, name, detached=True):
            pass

    class FakeOrch:
        def __init__(self, io, cfg):
            pass

        def run_once(self, window_target="dashboard:0"):
            logging.getLogger("tmux_dashboard.orchestrator").error(
                "create-window failed: window_target=%s staging_target=%s error=%s",
                window_target,
                "dashboard:99",
                "forced create-window failure",
            )
            return {"columns": 0, "rows": 0, "sessions": [], "positions": []}

    monkeypatch.setattr(cli, "config", type("M", (), {"load_config": staticmethod(lambda p: FakeCfg())}))
    monkeypatch.setattr(cli, "tmuxio", type("M", (), {"create_from_config": staticmethod(lambda _cfg: FakeIO())}))
    monkeypatch.setattr(cli, "orchestrator", type("M", (), {"Orchestrator": FakeOrch}))
    monkeypatch.setattr(cli, "logging_setup", type("M", (), {"setup_logging": staticmethod(lambda _cfg: None)}))
    monkeypatch.setattr(cli, "session_manager", type("M", (), {"ensure_dashboard_session": staticmethod(lambda _io: False)}))

    messages = []
    original_get_logger = logging.getLogger
    fake_logger = type(
        "L",
        (),
        {
            "error": lambda self, fmt, *args: messages.append(fmt % args),
        },
    )()
    monkeypatch.setattr(
        logging,
        "getLogger",
        lambda name=None: fake_logger if name == "tmux_dashboard.orchestrator" else original_get_logger(name),
    )

    rc = cli.main(["--once"])
    assert rc == 0
    assert any("create-window failed" in message for message in messages)
    assert any("forced create-window failure" in message for message in messages)


def test_cli_loop_keeps_exit_zero_when_run_once_logs_failure_and_returns(monkeypatch):
    """目的: 通常ループで run_once が内部ログ後に正常 return しても CLI が exit 0 を維持することを確認する。"""
    import logging
    from tmux_dashboard import __main__ as cli

    class FakeCfg:
        poll_interval_sec = 0

        class logging:
            dir = "~/.local/state/tmux-dashboard"
            level = "INFO"
            rotate_max_bytes = 10485760
            rotate_backup_count = 5

    class FakeIO:
        def list_sessions(self):
            return []

        def create_session(self, name, detached=True):
            pass

    class FakeOrch:
        def __init__(self, io, cfg):
            pass

        def run_once(self, window_target="dashboard:0"):
            logging.getLogger("tmux_dashboard.orchestrator").error(
                "swap-window failed: window_target=%s staging_target=%s error=%s",
                window_target,
                "dashboard:99",
                "forced swap-window failure",
            )
            return {"columns": 0, "rows": 0, "sessions": [], "positions": []}

    ensure_calls = {"count": 0}

    def fake_ensure(_io):
        ensure_calls["count"] += 1
        if ensure_calls["count"] >= 3:
            raise KeyboardInterrupt
        return False

    monkeypatch.setattr(cli, "config", type("M", (), {"load_config": staticmethod(lambda p: FakeCfg())}))
    monkeypatch.setattr(cli, "tmuxio", type("M", (), {"create_from_config": staticmethod(lambda _cfg: FakeIO())}))
    monkeypatch.setattr(cli, "orchestrator", type("M", (), {"Orchestrator": FakeOrch}))
    monkeypatch.setattr(cli, "logging_setup", type("M", (), {"setup_logging": staticmethod(lambda _cfg: None)}))
    monkeypatch.setattr(cli, "session_manager", type("M", (), {"ensure_dashboard_session": staticmethod(fake_ensure)}))

    messages = []
    original_get_logger = logging.getLogger
    fake_logger = type(
        "L",
        (),
        {
            "error": lambda self, fmt, *args: messages.append(fmt % args),
        },
    )()
    monkeypatch.setattr(
        logging,
        "getLogger",
        lambda name=None: fake_logger if name == "tmux_dashboard.orchestrator" else original_get_logger(name),
    )

    rc = cli.main([])
    assert rc == 0
    assert any("swap-window failed" in message for message in messages)
    assert any("forced swap-window failure" in message for message in messages)
