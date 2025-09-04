"""dashboardセッション自動復旧のテスト。

このテストでは、dashboardセッションが削除された場合に
自動的に再作成され、処理が継続することを検証する。
"""

import pytest
from unittest.mock import MagicMock, call, patch
import subprocess

from tmux_dashboard import orchestrator, config, session_manager


def test_dashboard_recovery_on_window_size_error():
    """window_size()でエラーが発生した場合、dashboardセッションを再作成して復旧する。"""
    
    # テスト用の設定とモックIO
    cfg = config.Config()
    mock_io = MagicMock()
    
    # 初回のwindow_size()呼び出しでエラー、復旧後は成功
    mock_io.window_size.side_effect = [
        subprocess.CalledProcessError(1, "tmux display-message"),  # 初回: エラー
        (120, 40),  # 復旧後: 成功
    ]
    
    # セッション一覧とその他のメソッド
    mock_io.list_sessions.return_value = ["session1", "session2"]
    mock_io.list_panes.return_value = ["%1", "%2"]
    mock_io.list_panes_detailed.return_value = [
        ("%1", 0, 0),
        ("%2", 60, 0),
    ]
    
    # セッション作成のモック
    mock_io.create_session.return_value = None
    
    # Orchestratorを作成
    orch = orchestrator.Orchestrator(io=mock_io, cfg=cfg)
    
    # ensure_dashboard_sessionをモック
    with patch('tmux_dashboard.session_manager.ensure_dashboard_session') as mock_ensure:
        mock_ensure.return_value = True  # 新規作成したことを示す
        
        # run_onceを実行
        with patch('builtins.print') as mock_print:
            result = orch.run_once("dashboard:0")
    
    # 検証: dashboardセッションが再作成された
    mock_ensure.assert_called_once_with(mock_io)
    
    # 検証: ターミナルにメッセージが表示された
    mock_print.assert_called_with("[tmux-dashboard] Recreated dashboard session", flush=True)
    
    # 検証: window_sizeが複数回呼ばれた（初回エラー、復旧後成功、compute_plan内でも呼ばれる）
    assert mock_io.window_size.call_count >= 2
    
    # 検証: 復旧後、正常なplanが返された
    assert result["columns"] >= 0
    assert "sessions" in result


def test_dashboard_recovery_failure():
    """dashboardセッション復旧に失敗した場合、空のplanを返す。"""
    
    cfg = config.Config()
    mock_io = MagicMock()
    
    # window_size()が常にエラー
    mock_io.window_size.side_effect = subprocess.CalledProcessError(1, "tmux")
    mock_io.list_sessions.return_value = []
    mock_io.create_session.return_value = None
    
    orch = orchestrator.Orchestrator(io=mock_io, cfg=cfg)
    
    with patch('tmux_dashboard.session_manager.ensure_dashboard_session') as mock_ensure:
        mock_ensure.return_value = True
        result = orch.run_once("dashboard:0")
    
    # 検証: 空のplanが返された
    assert result == {"columns": 0, "rows": 0, "sessions": [], "positions": []}


def test_no_recovery_when_dashboard_exists():
    """dashboardセッションが存在する場合、再作成しない。"""
    
    cfg = config.Config()
    mock_io = MagicMock()
    
    # window_size()が正常に動作
    mock_io.window_size.return_value = (120, 40)
    mock_io.list_sessions.return_value = ["dashboard", "session1"]
    mock_io.list_panes.return_value = ["%1"]
    mock_io.list_panes_detailed.return_value = [("%1", 0, 0)]
    
    orch = orchestrator.Orchestrator(io=mock_io, cfg=cfg)
    
    with patch('tmux_dashboard.session_manager.ensure_dashboard_session') as mock_ensure:
        result = orch.run_once("dashboard:0")
    
    # 検証: ensure_dashboard_sessionが呼ばれなかった（エラーが発生していないため）
    mock_ensure.assert_not_called()
    
    # 検証: window_sizeが複数回呼ばれた（run_onceとcompute_plan内）
    assert mock_io.window_size.call_count >= 1
    
    # 検証: 正常なplanが返された
    assert result["columns"] >= 0
    assert "sessions" in result


def test_main_loop_continues_on_error():
    """メインループでエラーが発生しても処理が継続する。"""
    from tmux_dashboard.__main__ import main
    
    # テスト用の引数
    test_args = ["--once", "--iterations", "2"]
    
    with patch('tmux_dashboard.config.load_config') as mock_load:
        with patch('tmux_dashboard.tmuxio.create_from_config') as mock_create_io:
            with patch('tmux_dashboard.orchestrator.Orchestrator') as mock_orch_class:
                with patch('tmux_dashboard.session_manager.ensure_dashboard_session') as mock_ensure:
                    
                    # モックの設定
                    mock_cfg = MagicMock()
                    mock_cfg.poll_interval_sec = 0.0
                    mock_cfg.logging.level = "INFO"
                    mock_cfg.logging.dir = "~/.local/state/tmux-dashboard"
                    mock_cfg.logging.rotate_max_bytes = 10485760
                    mock_cfg.logging.rotate_backup_count = 5
                    mock_load.return_value = mock_cfg
                    
                    mock_io = MagicMock()
                    mock_create_io.return_value = mock_io
                    
                    mock_orch = MagicMock()
                    mock_orch_class.return_value = mock_orch
                    
                    # 1回目はエラー、2回目は成功
                    mock_orch.run_once.side_effect = [
                        Exception("Test error"),
                        {"columns": 1, "rows": 1, "sessions": [], "positions": []}
                    ]
                    
                    mock_ensure.return_value = False
                    
                    # mainを実行
                    result = main(test_args)
    
    # 検証: 正常終了（エラーで停止しなかった）
    assert result == 0
    
    # 検証: run_onceが2回呼ばれた
    assert mock_orch.run_once.call_count == 2


def test_session_manager_ensure_dashboard():
    """session_managerがdashboardセッションを正しく作成する。"""
    
    mock_io = MagicMock()
    
    # dashboardセッションが存在しない
    mock_io.list_sessions.return_value = ["session1", "session2"]
    
    # ensure_dashboard_sessionを呼び出し
    created = session_manager.ensure_dashboard_session(mock_io)
    
    # 検証: セッションが作成された
    assert created is True
    mock_io.create_session.assert_called_once_with("dashboard", detached=True)
    
    # 既に存在する場合
    mock_io.list_sessions.return_value = ["dashboard", "session1"]
    mock_io.create_session.reset_mock()
    
    created = session_manager.ensure_dashboard_session(mock_io)
    
    # 検証: セッションが作成されなかった
    assert created is False
    mock_io.create_session.assert_not_called()