import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
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
    parser = build_parser()
    parser.parse_args(argv)
    # Phase 0: skeleton only (orchestrator wiring will be added later)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

