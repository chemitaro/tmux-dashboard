# 実装計画（TDD・テストファースト / uv準拠）

参照: @planning/current/requirement.md, @planning/current/design.md

## TDDサイクル（Kent Beck / t-wada 準拠）
- Red: まず失敗するテストを書く
- Green: 最小限の実装でパスさせる
- Refactor: 意味を変えずに設計を改善

各フェーズは複数の小さなTDDイテレーションで構成し、フェーズ末に必ず「テスト検証（全グリーン）→提出（レビュー依頼）」を行う。

検証コマンド（共通）:
- 依存同期: `uv sync --locked`（初回は `uv sync`）
- テスト実行: `uv run pytest -q`

---

## 実装タスク（フェーズ分割）

- [x] Phase 0. プロジェクト初期化（uv/構成）
  - TDD-0.1: pyproject雛形のテスト（pyproject存在検知）→ `pyproject.toml` 追加（[project], [dependency-groups]）
    - 依存: `pyyaml`, `wcwidth`, `libtmux`
    - 開発依存: `pytest`, `pytest-mock`
  - TDD-0.2: 最小パッケージ構成テスト → `tmux_dashboard/__init__.py`/`__main__.py` 追加
  - TDD-0.3: `uv sync` が .venv を生成できることを確認するテスト（シェル統合はスキップし、存在チェックをモック）
  - フェーズ終了検証: `uv run pytest -q` 全グリーン → 提出
  - _要件: 2/12.1_

- [x] Phase 1. 設定/ログ基盤（config.py, logging_setup.py）
  - TDD-1.1: 既定値ロードのテスト（組込既定）
  - TDD-1.2: `--config` 優先・`~/.config/...` のフォールバックのテスト
  - TDD-1.3: `exclude_patterns` を `re.fullmatch` で判定するテスト（大文字小文字区別）
  - TDD-1.4: ログローテーション設定（10MB×5）とディレクトリ既定パスのテスト
  - 実装: `config.py`, `logging_setup.py`
  - フェーズ終了検証: テスト全グリーン → 提出
  - _要件: 5.1/6/8/8.1/8.2_

- [x] Phase 2. ANSI幅/描画ユーティリティ（utils_wcwidth.py）
  - 完了: テスト追加・実装・全テストGreen（13 passed）
  - _要件: 4/7.4_

- [x] Phase 3. レイアウト計算（layout.py）
  - TDD-3.1: `columns = floor(W/min_tile_width)` の検証
  - TDD-3.2: `columns = max(1, min(N, floor(W/min_tile_width)))` の検証
  - TDD-3.3: `rows = ceil(N/columns)` の検証
  - TDD-3.4: 分割比率計画（列→行の順、端数の末尾吸収、行優先マッピング）
  - TDD-3.5: 代表ケース（A〜H）の算出結果が期待どおり（columns/rows/配分）
  - 実装: `layout.py`
  - フェーズ終了検証: テスト全グリーン → 提出
  - 命名: モジュール短縮名（例: `as L`）は可読性低下のため禁止
  - _要件: 5.3/6_

- [x] Phase 4. tmux I/O ラッパ（tmuxio.py）
  - 完了: ドライバ（libtmux/cli）、委譲IF、テストGreen（20 passed）

 
 - [x] Phase 5. レンダラー中核（renderer.py）
  - 完了: 実装・テスト・全Green（24 passed）
  - _要件: 4/5.5/7.3/7.4_

- [x] Phase 6. オーケストレータ（orchestrator.py）
  - 完了: セッション検出/除外/ソート、レイアウト計算、分割適用、タイトル設定（27 passed）
  - _要件: 4/5/7/9/12.3_

 
- [x] Phase 7. CLI/エントリポイント（`python -m tmux_dashboard`）
  - 完了: `--config`/`--once`/`--iterations`/`--window-target` 実装、Ctrl-C 安全終了
  - テスト: test_cli_entry.py（3件）

- [ ] Phase 8. 統合（libtmux TestServer / 軽量E2E）
  - 前提（完了済を確認）: LibtmuxDriver の target解決・socket指定・list/capture/set/split/kill の各API（設計3.1準拠）
  - TDD-8.1: FakeIO での拡充分統合（増→減→増、除外境界、リサイズ境界）
  - TDD-8.2: 実tmux E2E（kill-server→新規作成）
    - ケース群:
      - 初期セッション3件でタイトル反映（dashboard除外）
      - セッション削除で再実行時にタイトルから消える
      - リサイズ（79/120/160）でpane数（列×行）が再計算
      - 多セッション（8件, W=160, min_tile_width=40 → 4×2=8）
      - 動的追加（+gamma）/動的削除（-alpha）→再実行で反映
  - TDD-8.3: `libtmux` TestServer による最小E2E（tmux無環境はskip）
  - TDD-8.4: 非侵襲検証（`set-option -w` のみ、`set -g` 不使用）
  - TDD-8.5: ログ/メトリクス（再レイアウト回数・エラー）検証
  - 実装: Orchestrator+Renderer の相互作用を実サーバに近い形で検証（既存tmuxを汚染しない）
  - フェーズ終了検証: テスト全グリーン → 提出
  - _要件: 3/4/5/6/9/10_

- [ ] Phase 9. 設定テンプレート/ドキュメント
  - TDD-9.1: `configs/dashboard.example.yaml` の既定フィールド充足テスト
  - ドキュメント更新: READMEに使用方法/uv手順/既定パス/制約を追記
  - フェーズ終了検証: テスト全グリーン → 提出
  - _要件: 8/12.1_

---

## 見積もり時間（目安）

| フェーズ | 見積もり時間 |
|---------|------------|
| Phase 0 | 1.5h |
| Phase 1 | 2.0h |
| Phase 2 | 2.0h |
| Phase 3 | 1.5h |
| Phase 4 | 2.5h |
| Phase 5 | 3.0h |
| Phase 6 | 3.0h |
| Phase 7 | 1.5h |
| Phase 8 | 2.5h |
| Phase 9 | 1.0h |
| **合計** | **20.5h** |

---

## リスクと対策

| リスク | 影響度 | 対策 |
|-------|-------|------|
| ANSI/全角の幅計算誤差 | 中 | `wcwidth` に準拠、ユニットテストで多ケース検証、行末SGRリセット徹底 |
| 高スループット時の描画負荷 | 中 | 行差分描画＋`max_fps=30`＋最新優先ドロップ、ベンチ指標をログ出力 |
| tmux コマンド失敗 | 中 | 指数バックオフ＋失敗ログ、回復時の再同期 |
| 侵襲的操作の混入 | 低 | `set -g` をCI/テストで検出（コマンド監視のモック） |
| uv 仕様変更 | 低 | 公式Docs準拠で本計画を適宜更新、CIで`uv run pytest`を常用 |

---

## フェーズ完了条件（共通）
- すべての新規・既存テストがローカルでグリーン（`uv run pytest -q`）。
- 仕様逸脱がない（要件/設計の該当項目と突合）。
- 上記状態でコードを提出（レビュー依頼）。
