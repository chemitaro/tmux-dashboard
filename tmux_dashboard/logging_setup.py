"""ログ設定モジュール。

RotatingFileHandler によるローテーション設定を提供する。
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path

from .config import Config, expanduser_path


def _ensure_dir(p: Path) -> None:
    """ディレクトリ `p` を再帰的に作成（既にある場合は何もしない）。"""
    p.mkdir(parents=True, exist_ok=True)


def setup_logging(cfg: Config) -> logging.Logger:
    """ロガーを初期化し返す。

    - 出力ファイル: `~/.local/state/tmux-dashboard/tmux-dashboard.log`
    - ローテーション: `rotate_max_bytes` / `rotate_backup_count` 準拠
    - ログレベル: `cfg.logging.level`
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

    # ターミナル出力（StreamHandler）を追加（常時可視化）
    sh = logging.StreamHandler(stream=sys.stdout)
    sh.setLevel(logger.level)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    # 祖先ロガーへ伝搬しない
    logger.propagate = False
    return logger
