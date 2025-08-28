"""設定ロードとログ設定の挙動を検証するテスト。

目的:
- 既定値ロード、パス優先順位、除外パターン判定、ログローテーション設定を確認する。
"""

from __future__ import annotations

from pathlib import Path
import textwrap
import logging


def test_default_config_values(tmp_path, monkeypatch):
    """config_path未指定かつ既定パスにファイルがない場合、既定値が採用される。"""
    # HOME を一時ディレクトリに
    monkeypatch.setenv("HOME", str(tmp_path))

    from tmux_dashboard import config

    c = config.load_config(None)
    assert c.min_tile_width == 40
    assert c.poll_interval_sec == 2
    assert c.pane_border_enabled is True
    assert c.pane_border_format == "#{pane_title}"
    assert c.tmux.driver == "libtmux"
    assert c.viewer.max_fps == 30
    assert c.viewer.wrap_mode == "clip-right"
    assert c.logging.rotate_max_bytes == 10 * 1024 * 1024
    assert c.logging.rotate_backup_count == 5


def test_config_path_precedence(tmp_path, monkeypatch):
    """--configで指定したパスが最優先で読み込まれる。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg_file = tmp_path / "my.yaml"
    cfg_file.write_text(textwrap.dedent(
        """
        min_tile_width: 55
        viewer:
          max_fps: 20
        """
    ), encoding="utf-8")

    from tmux_dashboard import config

    c = config.load_config(str(cfg_file))
    assert c.min_tile_width == 55
    assert c.viewer.max_fps == 20


def test_home_config_fallback(tmp_path, monkeypatch):
    """--config未指定時は ~/.config/tmux-dashboard/config.yaml があれば読み込む。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    default_dir = tmp_path / ".config" / "tmux-dashboard"
    default_dir.mkdir(parents=True, exist_ok=True)
    default_file = default_dir / "config.yaml"
    default_file.write_text("min_tile_width: 41\n", encoding="utf-8")

    from tmux_dashboard import config

    c = config.load_config(None)
    assert c.min_tile_width == 41


def test_exclude_patterns_fullmatch(monkeypatch, tmp_path):
    """exclude_patterns は re.fullmatch で評価され、完全一致で除外される。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    from tmux_dashboard import config

    c = config.load_config(None)
    # 既定: ^dashboard$ は除外
    assert config.is_session_excluded(c, "dashboard") is True
    assert config.is_session_excluded(c, "dashboard2") is False

    # カスタムパターン
    c.exclude_patterns = [r"^foo$", r"bar.*"]
    assert config.is_session_excluded(c, "foo") is True
    assert config.is_session_excluded(c, "barbaz") is True
    assert config.is_session_excluded(c, "xbarbaz") is False


def test_logging_setup_rotating(tmp_path, monkeypatch):
    """ログはローテーション（10MB×5）で、既定ディレクトリ配下に出力される。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    from tmux_dashboard import config
    from tmux_dashboard import logging_setup

    c = config.load_config(None)
    logger = logging_setup.setup_logging(c)

    # ハンドラの検証
    rh_found = False
    for h in logger.handlers:
        # RotatingFileHandler の maxBytes / backupCount を確認
        if h.__class__.__name__ == "RotatingFileHandler":
            rh_found = True
            assert getattr(h, "maxBytes") == c.logging.rotate_max_bytes
            assert getattr(h, "backupCount") == c.logging.rotate_backup_count
            # 出力ディレクトリが既定パス配下
            log_path = Path(getattr(h, "baseFilename"))
            assert str(log_path).startswith(str(Path(config.expanduser_path(c.logging.dir))))
    assert rh_found, "RotatingFileHandler should be configured"
