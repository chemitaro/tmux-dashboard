"""オーケストレータ。

役割:
- セッション検出/除外/ソート
- ウィンドウ寸法取得→レイアウト計算
- 分割（簡易）とタイトル設定
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from . import layout
from . import config
from .tmuxio import TmuxIO


@dataclass
class Orchestrator:
    """ダッシュボード1ウィンドウの編成を司るクラス。"""

    io: TmuxIO
    cfg: config.Config

    def scan_sessions(self) -> List[str]:
        """セッション一覧を取得し、除外/ASCII昇順で返す。"""
        names = [s for s in self.io.list_sessions() if s != "dashboard"]
        out = [s for s in names if not config.is_session_excluded(self.cfg, s)]
        out.sort()
        return out

    def window_size(self, window_target: str) -> Tuple[int, int]:
        """対象ウィンドウの (W, H) を返す。"""
        return self.io.window_size(window_target)

    def compute_plan(self, window_target: str) -> Dict:
        """現在の構成からレイアウト計画を返す。"""
        sessions = self.scan_sessions()
        W, _ = self.window_size(window_target)
        Cn = layout.calc_columns(W, self.cfg.min_tile_width, len(sessions))
        Rn = layout.calc_rows(len(sessions), Cn)
        pos = layout.tile_positions(len(sessions), Cn, Rn)
        plan = {
            "columns": Cn,
            "rows": Rn,
            "sessions": sessions,
            "positions": [(r, c, s) for (r, c), s in zip(pos, sessions)],
        }
        return plan

    def apply_layout(self, window_target: str, columns: int, rows: int) -> None:
        """簡易適用: 現状は縦方向に `rows*columns-1` 回分割して枚数を揃える。

        将来的にグリッド分割（列→行）へ拡張する。
        """
        self.io.kill_other_panes(window_target)
        target_total = max(1, rows * columns)
        for _ in range(max(0, target_total - 1)):
            self.io.split_window(window_target, direction="v", percent=50)

    def apply_titles(self, window_target: str, sessions: List[str]) -> None:
        """pane border を有効化し、pane_title にセッション名を割り当てる。"""
        self.io.set_window_option(window_target, "pane-border-status", "top")
        self.io.set_window_option(window_target, "pane-border-format", "#{pane_title}")
        panes = self.io.list_panes(window_target)
        for pane_id, name in zip(panes, sessions):
            self.io.set_pane_title(pane_id, name)

    def run_once(self, window_target: str = "dashboard:0") -> Dict:
        """1サイクル: 計画→分割→タイトル設定→計画返却。"""
        plan = self.compute_plan(window_target)
        self.apply_layout(window_target, plan["columns"], plan["rows"])
        self.apply_titles(window_target, plan["sessions"])
        return plan
