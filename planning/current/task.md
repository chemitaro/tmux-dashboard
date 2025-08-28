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

- [ ] Phase 2. ANSI幅/描画ユーティリティ（utils_wcwidth.py）
  - TDD-2.1: ASCII/日本語/絵文字/合成文字の見かけ幅テスト（`wcwidth` 準拠）
  - TDD-2.2: ANSI SGR を保持したまま幅算出・右端クリップ（wrap_mode="clip-right"）のテスト
  - TDD-2.3: 各行末 `\x1b[0m` 付与のテスト
  - 実装: `utils_wcwidth.py`
  - フェーズ終了検証: テスト全グリーン → 提出
  
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

- [ ] Phase 4. tmux I/O ラッパ（tmuxio.py）
  - TDD-4.1: ドライバ切替（`config.tmux.driver`=libtmux/cli）で同一インターフェースが満たされること
  - TDD-4.2: `list_sessions()` がセッション名を列挙し `^dashboard$` を除外する（ドライバ別）
  - TDD-4.3: `window_size()` が `window_width/height` を取得（libtmux: プロパティ、cli: display-message）
  - TDD-4.4: `capture_pane()` が `-p -e (-J) -S -<H> -E -1` を構築（libtmux: `pane.cmd`、cli: サブプロセス）
  - TDD-4.5: `set_window_option` が `set-option -w` のみを用いる（`set -g` 禁止）
  - 実装: `tmuxio.py`（`LibtmuxDriver`／`CliDriver`、指数バックオフ）
  - フェーズ終了検証: テスト全グリーン → 提出
  - _要件: 5.1/5.2/7.1/7.2/セキュリティ・非侵襲_

- [ ] Phase 5. レンダラー中核（renderer.py）
  - TDD-5.1: `capture` テキストを W×H に成形（左基準×下端H行、右端クリップ）
  - TDD-5.2: 行ハッシュによる差分検出（変更行のみ更新）
  - TDD-5.3: `max_fps=30` 上限と「古いフレーム破棄（最新優先）」のテスト（時間依存を抽象化）
  - TDD-5.4: `truecolor` 設定と ANSI リセットの健全性
  - TDD-5.5: `pane_height` と `capture-pane` の行数突合（オフバイワン時の安全調整）
  - 実装: `renderer.py`（`loop_once`/`format_frame`/`diff_lines` を分離しテスタブルに）
  - フェーズ終了検証: テスト全グリーン → 提出
  - _要件: 4/5.5/7.3/7.4_

- [ ] Phase 6. オーケストレータ（orchestrator.py）
  - TDD-6.1: セッション検出→ASCII昇順→`dashboard` 除外のテスト
  - TDD-6.2: 対象 pane 選定（window/pane の active 優先→最小 index）
  - TDD-6.3: `window_width/height` 変化・セッション増減でレイアウト再計算（全面再構成）のテスト
  - TDD-6.4: pane タイトル設定（`pane-border-status top`/`pane-border-format '#{pane_title}'`/`select-pane -T`）
  - 実装: `orchestrator.py`（ポーリング: 既定2s、再試行: 指数バックオフ）
  - フェーズ終了検証: テスト全グリーン → 提出
  - _要件: 4/5/7/9/12.3_

- [ ] Phase 7. CLI/エントリポイント（`python -m tmux_dashboard`）
  - TDD-7.1: `--config` 引数のパースと既定パス解決
  - TDD-7.2: Orchestrator 起動・終了シグナル処理（Ctrl-Cで安全停止）
  - 実装: `__main__.py`（argparse）
  - フェーズ終了検証: テスト全グリーン → 提出
  - _要件: 9/12.1_

- [ ] Phase 8. 統合（libtmux TestServer / 軽量E2E）
  - TDD-8.1: `libtmux` の `TestServer` で独立サーバを立上げ、テスト用セッションを生成
  - TDD-8.2: セッション追加→レイアウト拡張→タイル増加
  - TDD-8.3: セッション削除→タイル削除→再配置
  - TDD-8.4: リサイズで列数変動（`min_tile_width` 厳守）
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
