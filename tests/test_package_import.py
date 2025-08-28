"""パッケージの import とバージョン属性の存在を検証するテスト。"""


def test_package_import_and_version():
    """`tmux_dashboard` が import 可能で、`__version__` が妥当であることを確認する。"""
    import tmux_dashboard as pkg  # noqa: F401

    assert hasattr(pkg, "__version__")
    assert isinstance(pkg.__version__, str)
    assert len(pkg.__version__) > 0
