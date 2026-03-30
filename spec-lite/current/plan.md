---
種別: 実装計画書
機能ID: "fix-tmux-headless-layout"
機能名: "headless tmux でのレイアウト復旧"
関連Issue: ["tmux split-window headless failure analysis"]
状態: "draft"
作成者: "codex"
最終更新: "2026-03-30"
依存: ["requirement.md", "design.md"]
---

# fix-tmux-headless-layout headless tmux でのレイアウト復旧 — 実装計画（TDD: Red → Green → Refactor）

## この計画で満たす要件ID (必須)
- 対象AC: AC-001, AC-002, AC-003, AC-004
- 対象EC: EC-001, EC-002, EC-003, EC-004
- 対象制約（該当があれば）:
  - 依存追加なし
  - CLI 互換維持
  - dashboard 以外へ非侵襲

## ステップ一覧（観測可能な振る舞い） (必須)
- active / current steps:
  - [ ] S01: `-l` ベースの分割 API と分割長算出を追加し、headless で split が通る土台を作る
  - [ ] S02: orchestrator を非破壊 apply と pane 数検証に対応させ、失敗を可視化する
  - [ ] S03: integrity 判定順序と E2E/回帰テストを整え、headless 復旧を保証する
- historical / superseded steps（任意）:
  - [x] 旧 `planning/current/task.md` による `-p` ベース前提の実装計画（`@spec-lite/completed/20260330_1843_planning-migration/task.md` にアーカイブ済み）

## 現行の実行対象スコープ (任意)
- 該当なし

## ネスト運用ルール (必須)
- トップレベルステップ `Sxx` は「観測可能な成果」で分ける
- サブステップ `Bx` は「作業ブロック」とし、同じ関心事または同じ変更境界を持つ仕事の束で分ける
- サブサブステップ `Ix` は「イテレーション」とし、1つの `Red → Green → Refactor` を完結できる最小単位で分ける
- 品質ゲート工程は、新規実装の TDD ではなく `検証 / 是正 / 再検証` の反復として扱ってよい

### 要件 ↔ ステップ対応表 (必須)
- active / current trace:
  - AC-001 → S01, S03
  - AC-002 → S02
  - AC-003 → S02, S03
  - AC-004 → S02
  - EC-001 → S02
  - EC-002 → S02, S03
  - EC-003 → S02
  - EC-004 → S01, S03
  - 非交渉制約 → S01, S02, S03

## レビュー / QA ゲート方針 (必須)
- G1:
  - タイミング: requirement / design 作成後
  - 担当: `spec_reviewer`
  - レビュー範囲:
    - `spec-lite/current/requirement.md`
    - `spec-lite/current/design.md`
  - 観点:
    - AC/EC と設計の整合
    - スコープ逸脱や未確定事項の妥当性
- G2:
  - タイミング: plan 作成後
  - 担当: `spec_reviewer`
  - レビュー範囲:
    - `spec-lite/current/plan.md`
  - 観点:
    - TDD で実行可能な粒度
    - requirements / design とのトレーサビリティ
- G3:
  - タイミング: 各 Sxx 完了時
  - 担当: `qa_reviewer` または `code_reviewer`
  - レビュー範囲:
    - 実装対象コードと対応テスト
  - 観点:
    - 回帰
    - headless 条件の担保

---

## 実装ステップ（各ステップは“観測可能な振る舞い”を1つ） (必須)

## ネスト方針（実装者向け） (必須)
- `Sxx` は成果物または観測可能な振る舞いの到達点を書く
- `Bx` はその成果に至るまでの作業ブロックを書く
- `Ix` は小さな TDD 反復または品質ゲート反復を書く
- `Red / Green / Refactor` は、独立セクションではなく各イテレーションの中に書く
- `update_plan` は、そのステップ専用の作業ブロック名で同期する

### S01 — headless で通る `-l` ベース分割 API を用意する (必須)
- 対象: AC-001 / EC-004 / 制約: 依存追加なし, CLI 互換維持
- 設計参照:
  - 対象IF/API: IF-001, IF-002, IF-003
  - 対象テスト:
    - `tests/test_layout.py`
    - `tests/test_tmuxio.py`
- このステップで「追加しないこと（スコープ固定）」:
  - orchestrator の失敗処理変更
  - integrity 順序変更

#### update_plan（着手時に登録） (必須)
- [ ] `update_plan` に、このステップの作業ブロックを登録した
- 登録する作業ブロック:
  - S01-B1: 分割長算出テストと実装
  - S01-B2: tmuxio split API の `-l` 化
  - S01-B3: 品質ゲート / 報告 / コミット

#### 期待する振る舞い（テストケース） (必須)
- Given: headless 条件を想定した layout 入力と tmux driver モック
- When: 分割長を算出し split コマンドを発行する
- Then: `-p` ではなく `layout.py` が absolute-cell 既定の `-l` を返し、算出長が 0 以下のときだけ `%` fallback を返せる
- 観測点（UI/HTTP/DB/Log など）: tmux コマンド引数、layout 算出結果
- 追加/更新するテスト:
  - `tests/test_layout.py`
  - `tests/test_tmuxio.py`

#### 作業ブロック（必須）
- S01-B1: 分割長算出
  - S01-B1-I1:
    - Red: `-l` 用の分割長算出テストを追加し、現状失敗を確認する
    - Green: `layout.py` に分割長算出関数を追加する
    - Refactor: 端数配分ロジックを整理し、命名を明確にする
- S01-B2: tmuxio split API 変更
  - S01-B2-I1:
    - Red: CLI driver の split コマンド期待値を `-l` ベースへ更新し、失敗を確認する
    - Green: `CliDriver.split_window` / `split_pane` を `length` 指定へ変更する
    - Refactor: 共通 helper が必要なら抽出する
  - S01-B2-I2:
    - Red: libtmux driver の split コマンド期待値を `-l` ベースへ更新し、失敗を確認する
    - Green: `LibtmuxDriver.split_window` / `split_pane` を `length` 指定へ変更する
    - Refactor: `TmuxIO` の公開 IF を揃える
- S01-B3: 品質ゲート / 報告 / コミット
  - S01-B3-I1:
    - Red: 該当なし
    - Green: `uv run pytest tests/test_layout.py tests/test_tmuxio.py -q` を実行し、成功を確認する
    - Refactor: `spec-lite/current/report.md` を更新し、コミット境界を確定する

#### ステップ末尾（省略しない） (必須)
- [ ] 期待するテストと必要な品質ゲートを実施し、成功した
- [ ] 必要なレビュー / QA ゲートを通過した、または不要理由を記録した
- [ ] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [ ] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [ ] コミット境界を確定した（コミットしない場合は理由を記録した）

### S02 — レイアウト適用を非破壊にし、pane 数不足を黙殺しない (必須)
- 対象: AC-002 / AC-003 / AC-004 / EC-001 / EC-002 / EC-003 / 制約: dashboard 非侵襲
- 設計参照:
  - 対象IF/API: IF-004, IF-005
  - 対象テスト:
    - `tests/test_orchestrator.py`
    - `tests/test_pane_integrity.py`
- このステップで「追加しないこと（スコープ固定）」:
  - headless E2E の本格追加

#### update_plan（着手時に登録） (必須)
- [ ] `update_plan` に、このステップの作業ブロックを登録した
- 登録する作業ブロック:
  - S02-B1: 非破壊 apply のテストと実装
  - S02-B2: pane 数検証と integrity 順序見直し
  - S02-B3: 品質ゲート / 報告 / コミット

#### 期待する振る舞い（テストケース） (必須)
- Given: split 失敗または pane 数不足が起こる orchestrator 条件
- When: `run_once()` または `apply_layout()` を実行する
- Then: staging window 上での適用成功時のみ `dashboard:0` を切り替え、pane 数不足や失敗は明示的に観測できる
- 観測点（UI/HTTP/DB/Log など）: pane 一覧、ログ、例外/結果オブジェクト
- 追加/更新するテスト:
  - `tests/test_orchestrator.py`
  - `tests/test_pane_integrity.py`
  - 0 セッション時に単一 pane を維持してエラーにしないケースを含む

#### 作業ブロック（必須）
- S02-B1: 非破壊 apply
  - S02-B1-I1:
    - Red: split failure 時に dashboard が先行破壊されることを示すテストを追加する
    - Green: staging window を使う `apply_layout()` へ変更し、失敗時に既存 `dashboard:0` を保持する
    - Refactor: success/error と staging cleanup の扱いを `run_once()` から見やすく整える
- S02-B2: mapping / integrity
  - S02-B2-I1:
    - Red: pane 数不足が `zip()` で黙殺されるテストを追加する
    - Green: `validate_mapping()` 相当の検証を追加し、pane 数不足を明示失敗にする
    - Refactor: ログ文言と例外境界を整理する
  - S02-B2-I2:
    - Red: 初回 integrity ノイズを再現するテストを追加する
    - Green: title 適用と integrity チェックの順序を見直す
    - Refactor: 初回/復旧直後の判定条件を明示する
  - S02-B2-I3:
    - Red: 表示対象 0 件で不要な split やエラー扱いになるテストを追加する
    - Green: 0 セッション時は単一 pane 維持で正常終了するよう調整する
    - Refactor: 0 セッション分岐を通常失敗経路と混同しないよう整理する
- S02-B3: 品質ゲート / 報告 / コミット
  - S02-B3-I1:
    - Red: 該当なし
    - Green: `uv run pytest tests/test_orchestrator.py tests/test_pane_integrity.py -q` を実行し、成功を確認する
    - Refactor: `spec-lite/current/report.md` を更新し、コミット境界を確定する

#### ステップ末尾（省略しない） (必須)
- [ ] 期待するテストと必要な品質ゲートを実施し、成功した
- [ ] 必要なレビュー / QA ゲートを通過した、または不要理由を記録した
- [ ] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [ ] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [ ] コミット境界を確定した（コミットしない場合は理由を記録した）

### S03 — headless E2E と回帰テストで復旧を保証する (必須)
- 対象: AC-001 / AC-003 / EC-002 / EC-004 / 制約: CLI 互換維持
- 設計参照:
  - 対象IF/API: IF-001, IF-004, IF-005
  - 対象テスト:
    - `tests/test_e2e_tmux.py`
    - 既存 CLI / session management テスト
- このステップで「追加しないこと（スコープ固定）」:
  - renderer 機能追加
  - 新規 CLI オプション

#### update_plan（着手時に登録） (必須)
- [ ] `update_plan` に、このステップの作業ブロックを登録した
- 登録する作業ブロック:
  - S03-B1: headless E2E の Red/Green
  - S03-B2: 全体回帰と spec/report 整合
  - S03-B3: 品質ゲート / 報告 / コミット

#### 期待する振る舞い（テストケース） (必須)
- Given: headless 条件で dashboard と複数セッションを作成済み
- When: dashboard を 1 サイクル実行する
- Then: pane が増え、pane title が対象セッションに一致し、既存 `xfail` の一部を通常検証へ置き換えられる
- 観測点（UI/HTTP/DB/Log など）: `tmux list-panes`, E2E テスト結果, CLI ログ
- 追加/更新するテスト:
  - `tests/test_e2e_tmux.py`
  - `tests/test_cli_entry.py` または既存 CLI 回帰テストの確認

#### 作業ブロック（必須）
- S03-B1: headless E2E
  - S03-B1-I1:
    - Red: `-l` 経路なら headless で pane が増えることを示す E2E を追加し、現状失敗を確認する
    - Green: 実装を調整して E2E を通す
    - Refactor: 旧 `xfail` 条件を見直し、必要最小限にする
- S03-B2: 全体回帰
  - S03-B2-I1:
    - Red: 該当なし
    - Green: `uv run pytest -q` を実行し、全体グリーンを確認する
    - Refactor: docs / report / plan の進捗整合を確認する
- S03-B3: 品質ゲート / 報告 / コミット
  - S03-B3-I1:
    - Red: 該当なし
    - Green: `qa_reviewer` または `code_reviewer` の観点に備えて実行ログを整理する
    - Refactor: `spec-lite/current/report.md` を更新し、コミット境界を確定する

#### ステップ末尾（省略しない） (必須)
- [ ] 期待するテストと必要な品質ゲートを実施し、成功した
- [ ] 必要なレビュー / QA ゲートを通過した、または不要理由を記録した
- [ ] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [ ] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [ ] コミット境界を確定した（コミットしない場合は理由を記録した）

## 未確定事項（TBD） (必須)
- Q-001:
  - 質問: staging window の一時名称を固定 prefix にするか、ランダム suffix を付与するか
  - 選択肢:
    - A: 固定 prefix のみで十分とする
    - B: 固定 prefix + ランダム suffix で衝突回避する
  - 推奨案（暫定）: B
  - 影響範囲: S02 / `design.md` / `tests/test_orchestrator.py`, `tests/test_e2e_tmux.py`
- Q-002:
  - 質問: headless E2E で残る `xfail` をどこまで通常テストへ昇格するか
  - 選択肢:
    - A: 今回の修正に直接関係するケースだけ昇格
    - B: headless 系 `xfail` を可能な限り全部見直す
  - 推奨案（暫定）: A
  - 影響範囲: S03 / `tests/test_e2e_tmux.py`

## 完了条件（Definition of Done） (必須)
- 対象AC/ECがすべて満たされ、テストまたは文書化された検証で保証されている
- `uv run pytest -q` がグリーンである
- headless 回帰を再現するテストが追加され、今回の障害モードを自動検証できる
- 必要なレビュー / QA ゲートを通過している
- MUST NOT / OUT OF SCOPE を破っていない
- `report.md` と plan の進捗が一致している

## 省略/例外メモ (必須)
- 該当なし
