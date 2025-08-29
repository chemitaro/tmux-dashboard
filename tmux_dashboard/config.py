"""設定管理モジュール。

役割:
- YAML設定の読み込みと既定値適用
- 除外パターンの評価（re.fullmatch）
- パスの展開と既定パス解決
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import typing as t


def expanduser_path(p: str | os.PathLike[str]) -> Path:
    """`~` を含むパスを HOME に展開した Path を返す。"""
    return Path(os.path.expanduser(str(p))).resolve()


def default_config_path() -> Path:
    """既定の設定ファイルパス (~/.config/tmux-dashboard/config.yaml)。"""
    return expanduser_path("~/.config/tmux-dashboard/config.yaml")


@dataclass
class ViewerConfig:
    """ビューアの描画/更新に関する設定。"""
    mode: str = "capture-only"
    pipe_stream: bool = False
    join_wrapped_lines: bool = True
    max_fps: int = 30
    drop_stale_frames: bool = True
    wrap_mode: str = "clip-right"
    truecolor: bool = True
    # キャプチャバッファ設定
    capture_buffer_multiplier: float = 2.0  # タイル高さの何倍を取得するか
    capture_buffer_max: int = 200           # 最大取得行数
    capture_buffer_min_extra: int = 20      # 最小追加行数


@dataclass
class TmuxConfig:
    """tmux への接続・制御に関する設定。"""
    driver: str = "libtmux"  # or "cli"
    socket_name: t.Optional[str] = None
    socket_path: t.Optional[str] = None


@dataclass
class LoggingConfig:
    """ログ出力に関する設定。"""
    level: str = "INFO"
    dir: str = "~/.local/state/tmux-dashboard"
    rotate_max_bytes: int = 10 * 1024 * 1024
    rotate_backup_count: int = 5


@dataclass
class Config:
    """ダッシュボード全体の設定。ネスト設定を含む。"""
    min_tile_width: int = 40
    poll_interval_sec: int = 2
    exclude_patterns: list[str] = field(default_factory=lambda: [r"^dashboard$"])
    pane_border_enabled: bool = True
    pane_border_format: str = "#{pane_title}"
    viewer: ViewerConfig = field(default_factory=ViewerConfig)
    tmux: TmuxConfig = field(default_factory=TmuxConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # 内部用: コンパイル済みパターンキャッシュ
    _exclude_compiled: list[re.Pattern[str]] = field(default_factory=list, init=False, repr=False)


def _deep_update(base: dict, updates: dict) -> dict:
    """ネスト辞書を上書きマージする。"""
    out = dict(base)
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_update(out[k], v)
        else:
            out[k] = v
    return out


def _to_dict(cfg: Config) -> dict:
    return {
        "min_tile_width": cfg.min_tile_width,
        "poll_interval_sec": cfg.poll_interval_sec,
        "exclude_patterns": list(cfg.exclude_patterns),
        "pane_border_enabled": cfg.pane_border_enabled,
        "pane_border_format": cfg.pane_border_format,
        "viewer": cfg.viewer.__dict__.copy(),
        "tmux": cfg.tmux.__dict__.copy(),
        "logging": cfg.logging.__dict__.copy(),
    }


def _from_dict(d: dict) -> Config:
    c = Config()
    c.min_tile_width = int(d.get("min_tile_width", c.min_tile_width))
    c.poll_interval_sec = int(d.get("poll_interval_sec", c.poll_interval_sec))
    c.exclude_patterns = list(d.get("exclude_patterns", c.exclude_patterns))
    c.pane_border_enabled = bool(d.get("pane_border_enabled", c.pane_border_enabled))
    c.pane_border_format = str(d.get("pane_border_format", c.pane_border_format))

    v = d.get("viewer", {})
    c.viewer = ViewerConfig(
        mode=v.get("mode", c.viewer.mode),
        pipe_stream=bool(v.get("pipe_stream", c.viewer.pipe_stream)),
        join_wrapped_lines=bool(v.get("join_wrapped_lines", c.viewer.join_wrapped_lines)),
        max_fps=int(v.get("max_fps", c.viewer.max_fps)),
        drop_stale_frames=bool(v.get("drop_stale_frames", c.viewer.drop_stale_frames)),
        wrap_mode=v.get("wrap_mode", c.viewer.wrap_mode),
        truecolor=bool(v.get("truecolor", c.viewer.truecolor)),
    )

    tcfg = d.get("tmux", {})
    c.tmux = TmuxConfig(
        driver=str(tcfg.get("driver", c.tmux.driver)),
        socket_name=tcfg.get("socket_name", c.tmux.socket_name),
        socket_path=tcfg.get("socket_path", c.tmux.socket_path),
    )

    l = d.get("logging", {})
    c.logging = LoggingConfig(
        level=str(l.get("level", c.logging.level)),
        dir=str(l.get("dir", c.logging.dir)),
        rotate_max_bytes=int(l.get("rotate_max_bytes", c.logging.rotate_max_bytes)),
        rotate_backup_count=int(l.get("rotate_backup_count", c.logging.rotate_backup_count)),
    )

    return c


def load_config(config_path: t.Optional[str]) -> Config:
    """設定をロードして `Config` を返す。

    優先順位:
    1) 明示パス
    2) 既定パス (~/.config/tmux-dashboard/config.yaml)
    3) 組込既定
    """
    data: dict = {}
    path: t.Optional[Path] = None

    if config_path:
        p = Path(config_path)
        if p.exists():
            path = p
    if path is None:
        p = default_config_path()
        if p.exists():
            path = p

    if path is not None:
        # PyYAML は依存に含め済み
        import yaml  # type: ignore

        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
            if not isinstance(loaded, dict):
                loaded = {}
            data = loaded

    # 既定値をベースにユーザ設定を上書き
    base = _to_dict(Config())
    merged = _deep_update(base, data)
    cfg = _from_dict(merged)

    # 除外パターンをコンパイル
    cfg._exclude_compiled = [re.compile(p) for p in cfg.exclude_patterns]
    return cfg


def is_session_excluded(cfg: Config, session_name: str) -> bool:
    """セッション名が除外パターンに完全一致するか判定する。"""
    # exclude_patterns が変更されている可能性もあるため、都度コンパイルする。
    patterns = cfg.exclude_patterns
    compiled = [re.compile(p) for p in patterns]
    for pat in compiled:
        if pat.fullmatch(session_name):
            return True
    return False
