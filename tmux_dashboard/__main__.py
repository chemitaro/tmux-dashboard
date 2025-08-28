"""tmux-dashboard のエントリポイント。

CLI引数を解釈し、将来的に Orchestrator の起動を担う。
現段階ではスケルトンとして `--config` の受理のみ行う。
"""

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    """コマンドライン引数パーサを構築して返す。"""
    p = argparse.ArgumentParser(
        prog="tmux_dashboard",
        description="Tmux dashboard: capture-and-render overview of sessions",
    )
    p.add_argument(
        "--config",
        help="Path to YAML config (default: ~/.config/tmux-dashboard/config.yaml)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """メイン関数。

    現状は引数のパースのみを行い、0 を返す。
    将来的に Orchestrator 初期化・起動処理を追加する。
    """
    parser = build_parser()
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
