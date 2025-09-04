"""ペイン整合性監視機能のテスト。

目的:
- tmuxioのlist_panes_with_titles()メソッド
- Orchestratorのcheck_pane_integrity()メソッド
- ペイン削除時の自動復旧
"""

from __future__ import annotations
from unittest.mock import Mock, patch, call
import subprocess


def test_cli_driver_list_panes_with_titles():
    """CliDriverがペインIDとタイトルのリストを返す。"""
    from tmux_dashboard.tmuxio import CliDriver
    
    driver = CliDriver({})
    
    # tmux list-panes の出力をモック
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = (
            b"%0 alpha\n"
            b"%1 beta\n"
            b"%2 gamma\n"
        )
        mock_run.return_value.returncode = 0
        
        result = driver.list_panes_with_titles("dashboard:0")
        
        assert result == [
            ("%0", "alpha"),
            ("%1", "beta"),
            ("%2", "gamma"),
        ]
        
        # 正しいコマンドが実行されたことを確認
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[:2] == ["tmux", "list-panes"]
        assert "-t" in args
        assert "dashboard:0" in args
        assert "-F" in args
        assert "#{pane_id} #{pane_title}" in args


def test_libtmux_driver_list_panes_with_titles():
    """LibtmuxDriverがペインIDとタイトルのリストを返す。"""
    from tmux_dashboard.tmuxio import LibtmuxDriver
    
    # モックセットアップ
    mock_server = Mock()
    mock_session = Mock()
    mock_window = Mock()
    mock_pane1 = Mock()
    mock_pane2 = Mock()
    mock_pane3 = Mock()
    
    # pane属性設定
    mock_pane1.id = "%0"
    mock_pane1.pane_title = "alpha"
    mock_pane1.cmd.return_value = Mock(stdout=["alpha"])
    mock_pane2.id = "%1"
    mock_pane2.pane_title = "beta"
    mock_pane2.cmd.return_value = Mock(stdout=["beta"])
    mock_pane3.id = "%2"
    mock_pane3.pane_title = "gamma"
    mock_pane3.cmd.return_value = Mock(stdout=["gamma"])
    
    # 関連付け
    mock_server.sessions = [mock_session]
    mock_session.session_name = "dashboard"  # session_name属性を使用
    mock_session.windows = [mock_window]
    mock_window.window_index = "0"  # window_index属性を使用
    mock_window.panes = [mock_pane1, mock_pane2, mock_pane3]
    
    driver = LibtmuxDriver({})
    driver._server = mock_server  # _serverプロパティに設定
    
    result = driver.list_panes_with_titles("dashboard:0")
    
    assert result == [
        ("%0", "alpha"),
        ("%1", "beta"),
        ("%2", "gamma"),
    ]


def test_fake_io_list_panes_with_titles():
    """FakeIOがテスト用のペインタイトル情報を返す。"""
    from test_orchestrator import FakeIO
    
    fake_io = FakeIO(
        sessions=["alpha", "beta", "gamma", "dashboard"],
        width=120,
        height=40,
        panes=["%0", "%1", "%2"]
    )
    
    result = fake_io.list_panes_with_titles("dashboard:0")
    
    # FakeIOの実装では session_0, session_1, ... を返す
    assert result == [
        ("%0", "session_0"),
        ("%1", "session_1"),
        ("%2", "session_2"),
    ]


def test_orchestrator_check_pane_integrity_match():
    """Orchestratorがペインタイトルの整合性を確認（一致時）。"""
    from tmux_dashboard.orchestrator import Orchestrator
    from tmux_dashboard.config import Config
    
    mock_io = Mock()
    mock_io.list_panes_with_titles.return_value = [
        ("%0", "alpha"),
        ("%1", "beta"),
        ("%2", "gamma"),
    ]
    
    cfg = Config()
    orch = Orchestrator(mock_io, cfg)
    orch._last_signature = ("dummy", "signature", ("alpha", "beta", "gamma"))
    
    # セッション一覧をモック
    with patch.object(orch, 'scan_sessions', return_value=["alpha", "beta", "gamma"]):
        needs_relayout = orch.check_pane_integrity("dashboard:0")
    
    # 整合性が取れているのでFalse
    assert needs_relayout is False
    # signatureは変更されない
    assert orch._last_signature is not None


def test_orchestrator_check_pane_integrity_mismatch():
    """Orchestratorがペインタイトルの不一致を検出（再レイアウト必要）。"""
    from tmux_dashboard.orchestrator import Orchestrator
    from tmux_dashboard.config import Config
    import logging
    
    mock_io = Mock()
    # ペインが1つ少ない（betaが削除された）
    mock_io.list_panes_with_titles.return_value = [
        ("%0", "alpha"),
        ("%2", "gamma"),
    ]
    
    cfg = Config()
    orch = Orchestrator(mock_io, cfg)
    orch._last_signature = ("dummy", "signature", ("alpha", "beta", "gamma"))
    
    # ロガーをモック
    with patch.object(logging, 'getLogger') as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # セッション一覧をモック
        with patch.object(orch, 'scan_sessions', return_value=["alpha", "beta", "gamma"]):
            needs_relayout = orch.check_pane_integrity("dashboard:0")
    
    # 不一致なのでTrue
    assert needs_relayout is True
    # signatureがリセットされる
    assert orch._last_signature is None
    # 警告ログが出力される
    mock_logger.warning.assert_called()


def test_orchestrator_check_pane_integrity_wrong_titles():
    """ペイン数は同じだがタイトルが異なる場合を検出。"""
    from tmux_dashboard.orchestrator import Orchestrator
    from tmux_dashboard.config import Config
    import logging
    
    mock_io = Mock()
    # ペイン数は3つだが、タイトルが異なる
    mock_io.list_panes_with_titles.return_value = [
        ("%0", "alpha"),
        ("%1", "delta"),  # betaではなくdelta
        ("%2", "gamma"),
    ]
    
    cfg = Config()
    orch = Orchestrator(mock_io, cfg)
    orch._last_signature = ("dummy", "signature", ("alpha", "beta", "gamma"))
    
    # ロガーをモック
    with patch.object(logging, 'getLogger') as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # セッション一覧をモック
        with patch.object(orch, 'scan_sessions', return_value=["alpha", "beta", "gamma"]):
            needs_relayout = orch.check_pane_integrity("dashboard:0")
    
    # タイトルが不一致なのでTrue
    assert needs_relayout is True
    # signatureがリセットされる
    assert orch._last_signature is None
    # 警告ログが出力される
    mock_logger.warning.assert_called()


def test_orchestrator_run_once_with_pane_integrity_check():
    """run_once()がペイン整合性チェックを実行する。"""
    from tmux_dashboard.orchestrator import Orchestrator
    from tmux_dashboard.config import Config
    
    mock_io = Mock()
    mock_io.list_sessions.return_value = ["alpha", "beta"]
    mock_io.window_size.return_value = (120, 40)
    mock_io.list_panes_detailed.return_value = [
        ("%0", 0, 0),
        ("%1", 60, 0),
    ]
    mock_io.list_panes_with_titles.return_value = [
        ("%0", "alpha"),
        ("%1", "beta"),
    ]
    
    cfg = Config()
    cfg.min_tile_width = 40
    
    orch = Orchestrator(mock_io, cfg)
    
    # check_pane_integrityをモック
    with patch.object(orch, 'check_pane_integrity', return_value=False) as mock_check:
        plan = orch.run_once()
    
    # ペイン整合性チェックが呼ばれる
    mock_check.assert_called_once_with("dashboard:0")
    
    # 計画が返される
    assert plan["columns"] == 2
    assert plan["rows"] == 1
    assert plan["sessions"] == ["alpha", "beta"]