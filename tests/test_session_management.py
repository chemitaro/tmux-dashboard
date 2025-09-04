"""dashboardセッション自動管理のテスト。

目的:
- dashboardセッションの存在チェック
- dashboardセッションの自動作成
- 既存セッションがある場合はスキップ
"""

from __future__ import annotations
from unittest.mock import Mock, patch, call


def test_create_dashboard_session_if_not_exists():
    """dashboardセッションが存在しない場合、作成する。"""
    from tmux_dashboard import session_manager
    
    mock_io = Mock()
    mock_io.list_sessions.return_value = ["alpha", "beta"]  # dashboardなし
    
    # dashboardセッションを作成
    created = session_manager.ensure_dashboard_session(mock_io)
    
    assert created is True
    mock_io.create_session.assert_called_once_with("dashboard", detached=True)


def test_skip_if_dashboard_session_exists():
    """dashboardセッションが既に存在する場合、何もしない。"""
    from tmux_dashboard import session_manager
    
    mock_io = Mock()
    mock_io.list_sessions.return_value = ["alpha", "dashboard", "beta"]
    
    # 既に存在するのでスキップ
    created = session_manager.ensure_dashboard_session(mock_io)
    
    assert created is False
    mock_io.create_session.assert_not_called()


def test_main_ensures_dashboard_session(monkeypatch):
    """メイン関数がdashboardセッションを確保する。"""
    from tmux_dashboard import __main__ as cli
    
    # モック設定
    mock_ensure = Mock(return_value=False)
    monkeypatch.setattr("tmux_dashboard.session_manager.ensure_dashboard_session", mock_ensure)
    
    # その他のモック
    mock_config = Mock()
    mock_config.poll_interval_sec = 0
    monkeypatch.setattr(cli.config, "load_config", lambda _: mock_config)
    
    mock_io = Mock()
    monkeypatch.setattr(cli.tmuxio, "create_from_config", lambda _: mock_io)
    
    mock_logger = Mock()
    monkeypatch.setattr(cli.logging_setup, "setup_logging", lambda _: mock_logger)
    
    # Orchestratorのモック
    class MockOrch:
        def __init__(self, io, cfg):
            pass
        def run_once(self, window_target="dashboard:0"):
            return {"ok": True}
    
    monkeypatch.setattr(cli.orchestrator, "Orchestrator", MockOrch)
    
    # 実行
    rc = cli.main(["--once"])
    
    # dashboardセッション確保が呼ばれたことを確認
    # 起動時と1回、--onceモードでも1回の計2回呼ばれる
    assert mock_ensure.call_count == 2
    mock_ensure.assert_called_with(mock_io)
    assert rc == 0