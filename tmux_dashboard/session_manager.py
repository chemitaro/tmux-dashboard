"""tmuxセッション管理モジュール。

役割:
- dashboardセッションの存在確認
- dashboardセッションの自動作成
- セッション管理のヘルパー関数
"""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tmuxio import TmuxIO

logger = logging.getLogger("tmux_dashboard.session_manager")


def ensure_dashboard_session(io: TmuxIO) -> bool:
    """dashboardセッションを確保する。
    
    Args:
        io: TmuxIOインスタンス
    
    Returns:
        bool: 新規作成した場合True、既存の場合False
    """
    sessions = io.list_sessions()
    
    if "dashboard" in sessions:
        logger.info("Dashboard session already exists")
        return False
    
    logger.info("Creating dashboard session")
    io.create_session("dashboard", detached=True)
    return True