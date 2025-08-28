"""ログ設定モジュール。

RotatingFileHandler によるローテーション設定を提供する。
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import Config, expanduser_path


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def setup_logging(cfg: Config) -> logging.Logger:
    """ロガーを初期化し返す。

    - 既定ディレクトリ配下に `tmux-dashboard.log` を出力
    - ローテーション: maxBytes/backupCount は設定値に従う
    """
    log_dir = expanduser_path(cfg.logging.dir)
    _ensure_dir(log_dir)

    logger = logging.getLogger("tmux_dashboard")
    logger.setLevel(getattr(logging, cfg.logging.level.upper(), logging.INFO))

    # 同一プロセスで重複設定されないよう初期化
    logger.handlers.clear()

    log_file = log_dir / "tmux-dashboard.log"
    handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=cfg.logging.rotate_max_bytes,
        backupCount=cfg.logging.rotate_backup_count,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

