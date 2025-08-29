"""VS Code ターミナル対応のためのインテリジェント全Paneスキャンのテスト。

目的:
- VS Codeターミナルでセッションが非アクティブでも正しくキャプチャできる。
- 段階的フォールバック（従来→全スキャン→内容優先）が動作する。
"""

from __future__ import annotations
import types


def _fake_completed(stdout: str):
    c = types.SimpleNamespace()
    c.returncode = 0
    c.stdout = stdout.encode()
    c.stderr = b""
    return c


def test_resolve_best_pane_traditional_active():
    """アクティブなwindow/paneがある場合は従来の方法で決定される。"""
    from tmux_dashboard import tmuxio
    
    calls = []
    
    def fake_run(args, capture_output=True, check=True):
        cmd = " ".join(args)
        calls.append(cmd)
        
        # window一覧: window 0がアクティブ
        if "list-windows" in cmd:
            return _fake_completed("0 1\n1 0\n")  # window_index window_active
        
        # pane一覧: pane 0がアクティブ
        if "list-panes" in cmd and ":0" in cmd:
            return _fake_completed("0 1 %1\n1 0 %2\n")  # pane_index pane_active pane_id
        
        # capture-pane
        if "capture-pane" in cmd and "%1" in cmd:
            return _fake_completed("active pane content\nwith multiple lines\n")
        
        return _fake_completed("")
    
    monkeypatch = __import__('pytest').MonkeyPatch()
    monkeypatch.setattr(tmuxio, "_run_subprocess", fake_run)
    
    try:
        driver = tmuxio.CliDriver()
        pane_id = driver.resolve_best_pane("session1")
        
        assert pane_id == "%1"
        # 従来のresolve_active_paneが使われることを確認
        assert any("list-windows" in c for c in calls)
        assert any("list-panes" in c for c in calls)
    finally:
        monkeypatch.undo()


def test_resolve_best_pane_vscode_all_inactive():
    """VS Code環境: 全window/pane非アクティブ時は全スキャンして内容があるpaneを選択。"""
    from tmux_dashboard import tmuxio
    
    calls = []
    scan_count = 0
    
    def fake_run(args, capture_output=True, check=True):
        nonlocal scan_count
        cmd = " ".join(args)
        calls.append(cmd)
        
        # window一覧: 全て非アクティブ（VS Code状態）
        if "list-windows" in cmd:
            return _fake_completed("0 0\n1 0\n")  # 全てwindow_active=0
        
        # window 0のpane一覧: 全て非アクティブ
        if "list-panes" in cmd and ":0" in cmd:
            return _fake_completed("0 0 %1\n1 0 %2\n")  # 全てpane_active=0
        
        # window 1のpane一覧
        if "list-panes" in cmd and ":1" in cmd:
            return _fake_completed("0 0 %3\n")
        
        # capture-pane: %1と%2は空、%3に内容あり（VS Codeで実行中）
        if "capture-pane" in cmd:
            scan_count += 1
            if "%1" in cmd or "%2" in cmd:
                return _fake_completed("")  # 空
            if "%3" in cmd:
                return _fake_completed("VS Code terminal output\n$ command running\n")
        
        return _fake_completed("")
    
    monkeypatch = __import__('pytest').MonkeyPatch()
    monkeypatch.setattr(tmuxio, "_run_subprocess", fake_run)
    
    try:
        driver = tmuxio.CliDriver()
        pane_id = driver.resolve_best_pane("session1")
        
        # 内容があるpane %3が選択される
        assert pane_id == "%3"
        # 複数のpaneをスキャンしたことを確認
        assert scan_count >= 2
    finally:
        monkeypatch.undo()


def test_resolve_best_pane_content_freshness():
    """複数のpaneに内容がある場合、より新鮮な内容を持つpaneを優先する。"""
    from tmux_dashboard import tmuxio
    
    calls = []
    
    def fake_run(args, capture_output=True, check=True):
        cmd = " ".join(args)
        calls.append(cmd)
        
        # 全て非アクティブ
        if "list-windows" in cmd:
            return _fake_completed("0 0\n")
        
        if "list-panes" in cmd:
            return _fake_completed("0 0 %1\n1 0 %2\n2 0 %3\n")
        
        # capture-pane: 異なる新鮮度の内容
        if "capture-pane" in cmd:
            if "%1" in cmd:
                # 古い出力（プロンプトなし）
                return _fake_completed("old output\nno prompt here\n")
            if "%2" in cmd:
                # 新しい出力（プロンプトあり、ANSIカラーあり）
                return _fake_completed("recent output\n\x1b[32m$ \x1b[0m")
            if "%3" in cmd:
                # 中程度の新鮮度
                return _fake_completed("some output\n> ")
        
        return _fake_completed("")
    
    monkeypatch = __import__('pytest').MonkeyPatch()
    monkeypatch.setattr(tmuxio, "_run_subprocess", fake_run)
    
    try:
        driver = tmuxio.CliDriver()
        pane_id = driver.resolve_best_pane("session1")
        
        # より新鮮な内容（プロンプト+ANSI）を持つ%2が選択される
        assert pane_id == "%2"
    finally:
        monkeypatch.undo()


def test_resolve_best_pane_fallback_to_default():
    """全paneが空の場合はデフォルト（session:0.0）にフォールバック。"""
    from tmux_dashboard import tmuxio
    
    calls = []
    
    def fake_run(args, capture_output=True, check=True):
        cmd = " ".join(args)
        calls.append(cmd)
        
        if "list-windows" in cmd:
            return _fake_completed("0 0\n")
        
        if "list-panes" in cmd:
            return _fake_completed("0 0 %1\n")
        
        # 全て空
        if "capture-pane" in cmd:
            return _fake_completed("")
        
        return _fake_completed("")
    
    monkeypatch = __import__('pytest').MonkeyPatch()
    monkeypatch.setattr(tmuxio, "_run_subprocess", fake_run)
    
    try:
        driver = tmuxio.CliDriver()
        pane_id = driver.resolve_best_pane("session1")
        
        # デフォルトにフォールバック
        assert pane_id == "session1:0.0"
    finally:
        monkeypatch.undo()


def test_libtmux_resolve_best_pane():
    """LibtmuxDriverでもresolve_best_paneが動作する。"""
    from tmux_dashboard import tmuxio
    
    class FakeCmdResult:
        def __init__(self, stdout):
            self.stdout = stdout if isinstance(stdout, list) else [stdout]
    
    class FakeServer:
        def __init__(self):
            self.calls = []
        
        def cmd(self, *args):
            self.calls.append(list(args))
            
            # list-windows
            if args[0] == "list-windows":
                return FakeCmdResult(["0 0", "1 0"])  # 全て非アクティブ
            
            # list-panes
            if args[0] == "list-panes":
                if ":0" in str(args):
                    return FakeCmdResult(["0 0 %1", "1 0 %2"])
                if ":1" in str(args):
                    return FakeCmdResult(["0 0 %3"])
            
            # capture-pane
            if args[0] == "capture-pane":
                if "%1" in str(args) or "%2" in str(args):
                    return FakeCmdResult([""])  # 空
                if "%3" in str(args):
                    return FakeCmdResult(["content in %3"])
            
            return FakeCmdResult([""])
    
    driver = tmuxio.LibtmuxDriver()
    driver._server = FakeServer()
    
    pane_id = driver.resolve_best_pane("session1")
    
    # 内容がある%3が選択される
    assert pane_id == "%3"