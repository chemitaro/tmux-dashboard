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
    monkeypatch.setattr(cli, "config", type("M", (), {"load_config": staticmethod(fake_load)}))
    monkeypatch.setattr(cli, "tmuxio", type("M", (), {"create_from_config": staticmethod(lambda _cfg: object())}))
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

    monkeypatch.setattr(cli, "config", type("M", (), {"load_config": staticmethod(lambda p: FakeCfg())}))
    monkeypatch.setattr(cli, "tmuxio", type("M", (), {"create_from_config": staticmethod(lambda _cfg: object())}))

    class FakeOrch:
        def __init__(self, io, cfg):
            pass

        def run_once(self, window_target="dashboard:0"):
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, "orchestrator", type("M", (), {"Orchestrator": FakeOrch}))

    rc = cli.main(["--once", "--iterations", "5"])  # 1回目でKeyboardInterrupt
    assert rc == 0

