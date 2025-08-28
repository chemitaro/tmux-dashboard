"""pyproject.toml の存在と基本メタデータを検証するテスト。

目的:
- プロジェクトのメタデータ（name, requires-python など）が定義されていること。
- ランタイム依存と開発依存の記述が含まれること。
"""

from pathlib import Path


def test_pyproject_exists_and_has_basic_metadata():
    """pyproject.toml が存在し、基本メタデータが含まれることを確認する。"""
    py = Path("pyproject.toml")
    assert py.exists(), "pyproject.toml should exist"
    text = py.read_text(encoding="utf-8")

    assert "[project]" in text
    assert 'name = "tmux-dashboard"' in text
    assert 'requires-python = ">=3.10"' in text


def test_pyproject_dependencies_marked():
    """ランタイム依存と開発依存が適切に記述されていることを確認する。"""
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    # runtime deps (uv sync 対象)
    assert "PyYAML" in text
    assert "wcwidth" in text
    assert "libtmux" in text
    # dev deps (uv dependency-groups)
    assert "[dependency-groups]" in text
    assert "dev" in text
    assert "pytest" in text
    assert "pytest-mock" in text
