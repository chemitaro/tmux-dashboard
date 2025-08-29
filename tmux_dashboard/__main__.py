"""tmux-dashboard のエントリポイント。

CLI引数を解釈し、将来的に Orchestrator の起動を担う。
現段階ではスケルトンとして `--config` の受理のみ行う。
"""

import argparse
import sys
import time
from datetime import datetime
from . import logging_setup
from . import config  # noqa: WPS347
from . import tmuxio  # noqa: WPS347
from . import orchestrator  # noqa: WPS347


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
    # テスト容易性のための実行制御フラグ（通常運用では未指定）
    p.add_argument("--once", action="store_true", help="Run limited iterations and exit")
    p.add_argument("--iterations", type=int, default=1, help="Iterations when --once is set")
    p.add_argument("--window-target", default="dashboard:0", help="Target window e.g. dashboard:0")
    return p


def main(argv: list[str] | None = None) -> int:
    """メイン関数。

    現状は引数のパースのみを行い、0 を返す。
    将来的に Orchestrator 初期化・起動処理を追加する。
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        cfg = config.load_config(args.config if getattr(args, "config", None) else None)
        # ログ初期化（ファイル + ターミナル）
        logging_setup.setup_logging(cfg)
        io = tmuxio.create_from_config(cfg)
        orch = orchestrator.Orchestrator(io=io, cfg=cfg)

        if args.once:
            n = max(1, int(args.iterations))
            for i in range(n):
                # ループ検出用の時刻出力
                print(f"[tmux-dashboard] loop={i+1}/{n} at {datetime.now().isoformat()}", flush=True)
                orch.run_once(window_target=args.window_target)
                if cfg.poll_interval_sec:
                    time.sleep(0)
            return 0

        # 通常の無限ループ（Ctrl-Cで終了）
        i = 0
        while True:
            i += 1
            # ループ検出用の時刻出力
            print(f"[tmux-dashboard] loop={i} at {datetime.now().isoformat()}", flush=True)
            orch.run_once(window_target=args.window_target)
            time.sleep(max(0.0, float(cfg.poll_interval_sec)))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
