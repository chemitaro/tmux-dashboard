"""タイル内で動作する簡易レンダラー（capture-only）。

各タイルpane内で常駐し、対象セッションの対象paneを `capture-pane` して
W×Hに整形してANSIで直描画する。環境非侵襲（read-only）。
"""

from __future__ import annotations

import argparse
import sys
import time
import subprocess
from typing import Tuple
import os

from .renderer import format_lines


def _tmux_display(fmt: str, target: str | None = None) -> str:
    args = ["tmux", "display-message", "-p"]
    if target:
        args += ["-t", target]
    args.append(fmt)
    cp = subprocess.run(args, capture_output=True, check=True)
    return cp.stdout.decode().strip()


def _pane_size_self() -> Tuple[int, int]:
    # 自ペインIDを明示して正確なサイズを取得（TMUX_PANE が無ければフォールバック）
    target = os.environ.get("TMUX_PANE")
    wh = _tmux_display("#{pane_width} #{pane_height}", target=target)
    w, h = wh.split()
    return int(w), int(h)


def _capture_target(pane_id: str, H: int, join_wrapped: bool) -> str:
    """対象paneから適切な量の履歴を含めて取得。
    
    ダッシュボードのタイル高さに応じて、履歴バッファから
    十分な行数を取得し、format_linesで最後のH行を表示。
    """
    # スマートな取得行数の計算
    # - デフォルト: H * 2（タイル高さの2倍）
    # - 最大: 200行（メモリ使用量を考慮）
    # - 最小: H + 20行（少なくとも履歴を含める）
    capture_lines = min(max(H * 2, H + 20), 200)
    
    args = ["tmux", "capture-pane", "-p", "-e"]
    if join_wrapped:
        args.append("-J")
    # 履歴バッファの終端からcapture_lines行を取得
    # -S -N: 履歴バッファの最後からN行前から開始
    # -E を省略: バッファの最後まで取得
    args += ["-S", f"-{capture_lines}", "-t", pane_id]
    cp = subprocess.run(args, capture_output=True, check=True)
    return cp.stdout.decode()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tmux_dashboard.tile", description="Tile renderer (capture-only)")
    p.add_argument("--target-pane", required=True, help="Target pane id to mirror (e.g. %3)")
    p.add_argument("--join-wrapped", action="store_true", help="Use -J to join wrapped lines")
    p.add_argument("--poll", type=float, default=0.5, help="Polling interval seconds (capture period)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = args.target_pane
    # 描画ループ
    while True:
        try:
            w, h = _pane_size_self()
            # 一部環境で -E -1 の終端解釈により最終行が欠ける事例があるため、
            # 安全側にキャプチャ行数を +1 して下端H行を確実に含める。
            cap_H = max(1, h + 1)
            captured = _capture_target(target, H=cap_H, join_wrapped=bool(args.join_wrapped))
            lines = format_lines(captured, width=max(1, w), height=max(1, h))
            # 画面クリア→ホーム→内容→下端固定
            sys.stdout.write("\x1b[2J\x1b[H")
            sys.stdout.write("\n".join(lines))
            # 念のためカーソルを最下段左端へ移動（描画の最終行が明示的に可視化される）
            sys.stdout.write(f"\x1b[{max(1, h)};1H")
            sys.stdout.flush()
        except KeyboardInterrupt:
            return 0
        except Exception:
            # エラー時は短い待ちの後に継続
            time.sleep(0.5)
        time.sleep(max(0.05, float(args.poll)))
    # not reached
    # return 0


if __name__ == "__main__":
    raise SystemExit(main())
