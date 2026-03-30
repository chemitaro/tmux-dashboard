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
import subprocess
import time

from . import layout
from . import config
from .tmuxio import TmuxIO
from . import session_manager


@dataclass
class LayoutApplyResult:
    """レイアウト適用結果。"""

    success: bool
    pane_ids: List[str]
    error_message: str | None = None


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

    def _sorted_panes(self, window_target: str) -> List[str]:
        """列優先（左→右、上→下）の pane_id 一覧を返す。"""
        try:
            details = self.io.list_panes_detailed(window_target)
            return [pid for pid, _, _ in sorted(details, key=lambda x: (x[1], x[2]))]
        except Exception:
            return self.io.list_panes(window_target)

    def validate_mapping(self, tiles: List[str], sessions: List[str]) -> None:
        """tile 数と session 数の整合を検証する。"""
        if len(tiles) < len(sessions):
            raise RuntimeError(
                f"pane shortage: tiles={len(tiles)} sessions={len(sessions)}"
            )

    def _pick_staging_window_index(self, session_name: str) -> int:
        """staging 用の未使用 window index を選ぶ。"""
        wins = self.io.list_windows_with_active(session_name)
        used = {idx for idx, _ in wins}
        idx = max(99, (max(used) + 1) if used else 99)
        while idx in used:
            idx += 1
        return idx

    def apply_layout(self, window_target: str, columns: int, rows: int) -> LayoutApplyResult:
        """グリッド分割を適用し、結果を返す。

        失敗は例外送出せず `LayoutApplyResult` で返す。
        """
        try:
            self.io.kill_other_panes(window_target)
            if columns <= 0:
                return LayoutApplyResult(success=True, pane_ids=self._sorted_panes(window_target))

            # 1) 列の分割（水平）
            h_perc = layout.progressive_percent_splits(columns)
            for i in range(max(0, columns - 1)):
                self.io.split_window(window_target, direction="h", percent=h_perc[i])

            # 2) 列ごとの行分割（垂直）
            sessions = self.scan_sessions()
            N = len(sessions)
            base = N // columns
            rem = N % columns
            rows_per_col = [base + (1 if c < rem else 0) for c in range(columns)]

            details = self.io.list_panes_detailed(window_target)
            left_to_top: list[tuple[int, str]] = []
            by_left: dict[int, list[tuple[str, int, int]]] = {}
            for pid, left, top in details:
                by_left.setdefault(left, []).append((pid, left, top))
            for left in sorted(by_left.keys()):
                top_pane = min(by_left[left], key=lambda x: x[2])
                left_to_top.append((left, top_pane[0]))

            for idx, (_, pane_id) in enumerate(left_to_top[:columns]):
                need = max(0, rows_per_col[idx] - 1)
                if need == 0:
                    continue
                v_perc = layout.progressive_percent_splits(rows_per_col[idx])
                for k in range(need):
                    try:
                        self.io.select_pane(pane_id)
                    except Exception:
                        pass
                    self.io.split_pane(pane_id, direction="v", percent=v_perc[k])

            return LayoutApplyResult(success=True, pane_ids=self._sorted_panes(window_target))
        except Exception as e:
            return LayoutApplyResult(success=False, pane_ids=[], error_message=str(e))

    def apply_titles(self, window_target: str, sessions: List[str]) -> None:
        """pane border を有効化し、pane_title にセッション名を割り当てる。"""
        # ボーダーを上部にし、タイトルは pane_title を表示
        self.io.set_window_option(window_target, "pane-border-status", "top")
        self.io.set_window_option(window_target, "pane-border-format", "#{pane_title}")
        panes_sorted = self._sorted_panes(window_target)
        self.validate_mapping(panes_sorted, sessions)
        for pane_id, name in zip(panes_sorted, sessions):
            self.io.set_pane_title(pane_id, name)
    
    def check_pane_integrity(self, window_target: str, *, strict: bool = False) -> bool:
        """ペインタイトルの整合性を確認し、不一致なら再レイアウトが必要。
        
        Returns:
            True: 再レイアウトが必要（不一致が検出された）
            False: 整合性が取れている
        """
        logger = logging.getLogger("tmux_dashboard.orchestrator")
        
        # 期待されるセッション名の集合
        expected_sessions = set(self.scan_sessions())
        
        # 実際のペインタイトルの集合
        try:
            panes_with_titles = self.io.list_panes_with_titles(window_target)
            actual_titles = set(title for _, title in panes_with_titles)
        except Exception as e:
            logger.warning("Failed to get pane titles: %s", e)
            # strict モードでは検証不能を不整合として扱う（fail-closed）。
            if strict:
                return True
            # 非 strict では従来どおり整合性チェックをスキップ。
            return False
        
        # 集合が一致しない場合は再レイアウトが必要
        if expected_sessions != actual_titles:
            logger.warning(
                "Pane integrity check failed. Expected: %s, Actual: %s",
                sorted(expected_sessions),
                sorted(actual_titles)
            )
            # _last_signatureをリセットして次回強制的に再レイアウト
            self._last_signature = None
            return True
        
        return False

    def run_once(self, window_target: str = "dashboard:0") -> Dict:
        """1サイクル: 計画→分割→タイトル設定→計画返却。
        
        dashboardセッションが消失している場合は自動的に再作成して復旧する。
        """
        logger = logging.getLogger("tmux_dashboard.orchestrator")
        sessions = self.scan_sessions()
        
        # dashboardセッションの存在確認とwindow_size取得を試行
        try:
            W, H = self.window_size(window_target)
            logger.info("detected: sessions=%s, window=%sx%s", sessions, W, H)
        except (subprocess.CalledProcessError, Exception) as e:
            # dashboardセッションが存在しない場合の自動復旧
            logger.warning("Failed to get window size for %s: %s", window_target, e)
            logger.info("Attempting to recreate dashboard session...")
            
            # dashboardセッションを再作成
            created = session_manager.ensure_dashboard_session(self.io)
            if created:
                print("[tmux-dashboard] Recreated dashboard session", flush=True)
                logger.info("Successfully recreated dashboard session")
            
            # 再試行
            try:
                W, H = self.window_size(window_target)
                logger.info("Retry successful: window=%sx%s", W, H)
            except Exception as retry_error:
                logger.error("Failed to recover dashboard session: %s", retry_error)
                # 復旧に失敗した場合は空の計画を返す
                return {"columns": 0, "rows": 0, "sessions": [], "positions": []}

        # 現在の計画を算出
        try:
            plan = self.compute_plan(window_target)
            logger.info("plan: columns=%s rows=%s", plan["columns"], plan["rows"])
        except Exception as e:
            logger.error("Failed to compute plan: %s", e)
            return {"columns": 0, "rows": 0, "sessions": [], "positions": []}

        # レイアウト差分判定（columns/rows/sessions のシグネチャ）
        signature = (plan["columns"], plan["rows"], tuple(plan["sessions"]))
        sessions = plan["sessions"]

        # 0セッションは正常系: 単一pane維持のみ行う
        if not sessions:
            try:
                self.io.kill_other_panes(window_target)
            except Exception as e:
                logger.warning("failed to shrink empty dashboard: %s", e)
            self._last_signature = signature
            self._last_mapping = []
            return plan

        need_layout = signature != self._last_signature
        if not need_layout:
            # signature が不変のときだけ active window で integrity を評価
            need_layout = self.check_pane_integrity(window_target)

        if need_layout:
            staging_target: str | None = None
            try:
                staging_index = self._pick_staging_window_index("dashboard")
                staging_target = self.io.create_window(
                    "dashboard",
                    staging_index,
                    detached=True,
                    width=W,
                    height=H,
                )

                result = self.apply_layout(staging_target, plan["columns"], plan["rows"])
                if not result.success:
                    raise RuntimeError(result.error_message or "layout apply failed")

                self.apply_titles(staging_target, sessions)
                if self.check_pane_integrity(staging_target, strict=True):
                    raise RuntimeError("pane integrity check failed on staging window")

                self.io.swap_window(staging_target, window_target)
                # swap 後、staging target 側に旧 dashboard:0 が来る
                self.io.kill_window(staging_target)
                self._last_signature = signature
            except Exception as e:
                logger.error("non-destructive apply failed: %s", e)
                if staging_target is not None:
                    try:
                        self.io.kill_window(staging_target)
                    except Exception as cleanup_error:
                        logger.warning(
                            "failed to cleanup staging window %s: %s",
                            staging_target,
                            cleanup_error,
                        )
                return plan

        # タイルpane（列優先）とセッションのマッピングを作成
        tiles_sorted = self._sorted_panes(window_target)
        try:
            self.validate_mapping(tiles_sorted, sessions)
        except RuntimeError as e:
            logger.error("mapping validation failed: %s", e)
            return plan

        # resolve/respawn が未実装なIO（テスト用Fakeなど）では描画起動をスキップ
        # VS Code対応: resolve_best_paneを優先、なければresolve_active_paneにフォールバック
        resolver = getattr(self.io, "resolve_best_pane", None) or getattr(self.io, "resolve_active_pane", None)
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
            # respawn で pane_title が上書きされる環境があるため、最後に再適用する。
            self.apply_titles(window_target, sessions)
            # 起動直後にタイトルが再上書きされるケースに備え、短時間待って再適用する。
            if self.check_pane_integrity(window_target, strict=True):
                time.sleep(0.05)
                self.apply_titles(window_target, sessions)
        try:
            logger.info("titles: %s", [t for t in self.io.list_panes_detailed(window_target)])
        except Exception:
            pass
        return plan
