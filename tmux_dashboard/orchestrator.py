"""オーケストレータ。

役割:
- セッション検出/除外/ソート
- ウィンドウ寸法取得→レイアウト計算
- 分割（簡易）とタイトル設定
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import logging

from . import layout
from . import config
from .tmuxio import TmuxIO


@dataclass
class Orchestrator:
    """ダッシュボード1ウィンドウの編成を司るクラス。"""

    io: TmuxIO
    cfg: config.Config
    _last_signature: Tuple[int, int, Tuple[str, ...]] | None = field(default=None, init=False, repr=False)
    _last_mapping: List[Tuple[str, str, str]] = field(default_factory=list, init=False, repr=False)  # (tile_pane_id, target_pane_id, session)

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
        """グリッド分割: 列→行の順で分割し、空セルは生成しない。

        既存の pane 数が目標と一致する場合は分割処理を行わず、フリッカーを抑制する。
        """
        # 既存の pane 数が目標と一致する場合は分割処理を行わず、フリッカーを抑制
        self.io.kill_other_panes(window_target)
        if columns <= 0:
            return
        # 1) 列の分割（水平）
        h_perc = layout.progressive_percent_splits(columns)
        for i in range(max(0, columns - 1)):
            self.io.split_window(window_target, direction="h", percent=h_perc[i])
        # 2) 列ごとの行分割（垂直）: セッション配分に応じて分割
        #    rows_per_col[c] = base + (c < remainder)
        plan = self.compute_plan(window_target)
        N = len(plan["sessions"])
        base = N // columns
        rem = N % columns
        rows_per_col = [base + (1 if c < rem else 0) for c in range(columns)]
        # 列の左座標で top pane を特定
        details = self.io.list_panes_detailed(window_target)
        # left 昇順で列の top pane を抽出
        # group by left
        left_to_top: list[tuple[int, str]] = []
        by_left: dict[int, list[tuple[str, int, int]]] = {}
        for pid, left, top in details:
            by_left.setdefault(left, []).append((pid, left, top))
        for left in sorted(by_left.keys()):
            top_pane = min(by_left[left], key=lambda x: x[2])
            left_to_top.append((left, top_pane[0]))
        # 列ごとに必要な行数-1だけ分割
        for idx, (_, pane_id) in enumerate(left_to_top[:columns]):
            need = max(0, rows_per_col[idx] - 1)
            if need == 0:
                continue
            v_perc = layout.progressive_percent_splits(rows_per_col[idx])
            for k in range(need):
                # 対象列の top pane を選択して分割
                try:
                    self.io.select_pane(pane_id)
                except Exception:
                    pass
                self.io.split_pane(pane_id, direction="v", percent=v_perc[k])

    def apply_titles(self, window_target: str, sessions: List[str]) -> None:
        """pane border を有効化し、pane_title にセッション名を割り当てる。"""
        # ボーダーを上部にし、タイトルは pane_title を表示
        self.io.set_window_option(window_target, "pane-border-status", "top")
        self.io.set_window_option(window_target, "pane-border-format", "#{pane_title}")
        # 行優先（上→下、左→右）で pane を並べ替え
        try:
            details = self.io.list_panes_detailed(window_target)
            panes_sorted = [pid for pid, _, _ in sorted(details, key=lambda x: (x[2], x[1]))]
        except Exception:
            panes_sorted = self.io.list_panes(window_target)
        for pane_id, name in zip(panes_sorted, sessions):
            self.io.set_pane_title(pane_id, name)

    def run_once(self, window_target: str = "dashboard:0") -> Dict:
        """1サイクル: 計画→分割→タイトル設定→計画返却。"""
        logger = logging.getLogger("tmux_dashboard.orchestrator")
        sessions = self.scan_sessions()
        W, H = self.window_size(window_target)
        logger.info("detected: sessions=%s, window=%sx%s", sessions, W, H)

        # 現在の計画を算出
        plan = self.compute_plan(window_target)
        logger.info("plan: columns=%s rows=%s", plan["columns"], plan["rows"])

        # レイアウト差分判定（columns/rows/sessions のシグネチャ）
        signature = (plan["columns"], plan["rows"], tuple(plan["sessions"]))
        need_layout = signature != self._last_signature
        if need_layout:
            # 分割とタイトル設定（ログは tmuxio 側で DEBUG 出力）
            self.apply_layout(window_target, plan["columns"], plan["rows"])
            self.apply_titles(window_target, plan["sessions"])
            self._last_signature = signature

        # タイルpane（行優先）とセッションのマッピングを作成
        try:
            details = self.io.list_panes_detailed(window_target)
            tiles_sorted = [pid for pid, _, _ in sorted(details, key=lambda x: (x[2], x[1]))]
        except Exception:
            tiles_sorted = self.io.list_panes(window_target)

        sessions = plan["sessions"]
        # resolve/respawn が未実装なIO（テスト用Fakeなど）では描画起動をスキップ
        resolver = getattr(self.io, "resolve_active_pane", None)
        respawner = getattr(self.io, "respawn_pane", None)
        mapping: List[Tuple[str, str, str]] = []
        if callable(resolver) and callable(respawner):
            for tile_pane, sess in zip(tiles_sorted, sessions):
                target = resolver(sess)
                if target is None:
                    continue
                mapping.append((tile_pane, target, sess))

        # マッピングが前回と同じなら再起動は不要
        if mapping and mapping != self._last_mapping and callable(respawner):
            # 各タイルpaneでレンダラー（tile.py）を起動
            import sys as _sys
            py = _sys.executable or "python"
            argv_base = [py, "-m", "tmux_dashboard.tile"]
            for tile_pane, target, sess in mapping:
                argv = argv_base + [
                    "--target-pane",
                    str(target),
                ]
                # 下端の完全一致を優先するため、ここでは -J を使わず取得（wrap結合なし）
                # 軽めのポーリング
                argv += ["--poll", "0.5"]
                try:
                    respawner(tile_pane, argv)  # type: ignore[misc]
                    logger.info("spawned renderer: tile=%s <- %s (sess=%s)", tile_pane, target, sess)
                except Exception as e:  # pragma: no cover - 実行環境依存
                    logger.error("failed to respawn renderer on %s: %s", tile_pane, e)
            self._last_mapping = mapping
        try:
            logger.info("titles: %s", [t for t in self.io.list_panes_detailed(window_target)])
        except Exception:
            pass
        return plan
