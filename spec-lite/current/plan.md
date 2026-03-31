---
種別: 実装計画書
機能ID: "dashboard-input-proxy"
機能名: "dashboard 選択ペイン入力プロキシ分析"
関連Issue: ["N/A"]
状態: "draft"
作成者: "Codex"
最終更新: "2026-04-01"
依存: ["requirement.md", "design.md"]
---

# dashboard-input-proxy dashboard 選択ペイン入力プロキシ分析 — 実装計画（TDD: Red → Green → Refactor）

## この計画で満たす要件ID (必須)
- 対象AC: AC-001, AC-002, AC-003
- 対象EC: EC-001, EC-002
- 対象制約（該当があれば）:
  - dashboard 既定は read-only
  - attach / switch-client を主方式にしない

## ステップ一覧（観測可能な振る舞い） (必須)
- active / current steps:
  - [ ] S01: tile-target binding を tmux 上で正本化し、選択 tile から target pane を安全に解決できる
  - [ ] S02: 単発送信コマンドで選択 tile の target pane へ literal text / Enter を送れる
  - [ ] S03: armed input mode を追加し、選択 tile だけへ限定的なキー転送を行える
  - [ ] S04: 既知リスクと out-of-scope を反映した README / report / 最小 E2E を整備する
- historical / superseded steps（任意）:
  - 該当なし

## 現行の実行対象スコープ (任意)
- 通常案件では `該当なし`

## ネスト運用ルール (必須)
- トップレベルステップ `Sxx` は「観測可能な成果」で分ける
- サブステップ `Bx` は「作業ブロック」とし、同じ関心事または同じ変更境界を持つ仕事の束で分ける
- サブサブステップ `Ix` は「1 つの Red → Green → Refactor」を完結できる最小単位で分ける
- Phase 1 は S01〜S02、Phase 2 は S03、Phase 3 は S04 を想定する

### 要件 ↔ ステップ対応表 (必須)
- active / current trace:
  - AC-001 → S01
  - AC-002 → S01, S02, S03
  - AC-003 → S01, S02, S03, S04
  - EC-001 → S01, S02
  - EC-002 → S02, S03, S04
  - 非交渉制約 → S01, S02, S03

## レビュー / QA ゲート方針 (必須)
- G1:
  - タイミング: S01 完了時
  - 担当: `spec_reviewer`
  - レビュー範囲:
    - `tmux_dashboard/orchestrator.py`
    - `tmux_dashboard/tmuxio.py`
  - 観点:
    - binding 正本化が stale / fail-closed を満たすか
    - attach 主方式へ逸脱していないか
- G2:
  - タイミング: S02-S03 完了時
  - 担当: `code_reviewer`
  - レビュー範囲:
    - `tmux_dashboard/tile.py`
    - `tmux_dashboard/__main__.py`
    - `tests/test_tmuxio.py`
    - `tests/test_cli_entry.py`
  - 観点:
    - 誤送信防止
    - raw input / special key の境界
- G3:
  - タイミング: 最終確認時
  - 担当: `qa_reviewer`
  - レビュー範囲:
    - `tests/`
    - `README.md`
  - 観点:
    - 回帰範囲
    - documented behavior と実装一致

---

## 実装ステップ（各ステップは“観測可能な振る舞い”を1つ） (必須)

## ネスト方針（実装者向け） (必須)
- `Sxx` は観測可能な振る舞い
- `Bx` は変更境界
- `Ix` は TDD 反復

### S01 — tile-target binding を tmux 上で正本化し、解決不能時は fail-closed にできる (必須)
- 対象: AC-001, AC-002 / EC-001 / 制約: read-only 既定維持
- 設計参照:
  - 対象IF/API: IF-002, IF-003, IF-004
  - 対象テスト:
    - `tests/test_tmuxio.py`
    - `tests/test_orchestrator.py`
- このステップで「追加しないこと（スコープ固定）」:
  - 実入力送信
  - armed mode

#### update_plan（着手時に登録） (必須)
- [ ] `update_plan` に、このステップの作業ブロックを登録した
- 登録する作業ブロック:
  - S01-B1: TmuxIO に pane option 契約を追加
  - S01-B2: Orchestrator で binding 永続化 / cleanup
  - S01-B3: 品質ゲート / 報告 / コミット

#### 期待する振る舞い（テストケース） (必須)
- Given: layout 後に tile-target mapping が存在する
- When: tile pane から target pane を解決する
- Then: 正しい target が得られ、binding 不在や stale 時は fail-closed になる
- 観測点（UI/HTTP/DB/Log など）: pane user option、unit test、orchestrator log
- 追加/更新するテスト:
  - `tests/test_tmuxio.py`
  - `tests/test_orchestrator.py`

#### 作業ブロック（必須）
- S01-B1: pane option 契約
  - S01-B1-I1:
    - Red: pane option get/set テストを追加
    - Green: CLI / libtmux 両 driver に契約を実装
    - Refactor: option 名と fail-closed を整理
- S01-B2: binding 永続化 / cleanup
  - S01-B2-I1:
    - Red: relayout 後に binding が更新されるテストを追加
    - Green: `Orchestrator` で mapping を pane option に保存
    - Refactor: 0 session / swap failure cleanup と整合させる
- S01-B3: 品質ゲート / 報告 / コミット
  - S01-B3-I1:
    - Red: 該当なし
    - Green: `uv run pytest`
    - Refactor: `report.md` 更新、レビュー依頼

#### ステップ末尾（省略しない） (必須)
- [ ] 期待するテストと必要な品質ゲートを実施し、成功した
- [ ] 必要なレビュー / QA ゲートを通過した、または不要理由を記録した
- [ ] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [ ] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [ ] コミット境界を確定した

### S02 — 単発送信コマンドで選択 tile の target pane へ安全に 1 行送信できる (任意)
- 対象: AC-002, AC-003 / EC-001, EC-002 / 制約: attach 主方式禁止
- 設計参照:
  - 対象IF/API: IF-001, IF-003, IF-005
  - 対象テスト:
    - `tests/test_tmuxio.py`
    - `tests/test_cli_entry.py`
- このステップで「追加しないこと（スコープ固定）」:
  - raw input 常時転送
  - 高速 TUI 最適化

#### update_plan（着手時に登録） (必須)
- [ ] `update_plan` に、このステップの作業ブロックを登録した
- 登録する作業ブロック:
  - S02-B1: `send_keys` 契約と特殊キー最小集合
  - S02-B2: CLI 単発送信導線
  - S02-B3: 品質ゲート / 報告 / コミット

#### 期待する振る舞い（テストケース） (必須)
- Given: tile-target binding が保存済み
- When: `--tile-pane ... --send-text ... --enter` を実行する
- Then: その target pane にだけ text / Enter が送信される
- 観測点（UI/HTTP/DB/Log など）: tmux send-keys 呼び出し、CLI exit code
- 追加/更新するテスト:
  - `tests/test_tmuxio.py`
  - `tests/test_cli_entry.py`

#### 作業ブロック（必須）
- S02-B1: send-keys 契約
  - S02-B1-I1:
    - Red: literal text / Enter の送信テストを追加
    - Green: `TmuxIO.send_keys()` を実装
    - Refactor: named key / literal の境界を整理
- S02-B2: CLI 導線
  - S02-B2-I1:
    - Red: `--tile-pane` 正常系 / binding 不在異常系テストを追加
    - Green: 単発送信 CLI を追加
    - Refactor: `--selected` 補助導線の扱いを整理
- S02-B3: 品質ゲート / 報告 / コミット
  - S02-B3-I1:
    - Red: 該当なし
    - Green: `uv run pytest`
    - Refactor: `report.md` 更新、レビュー依頼

#### ステップ末尾（省略しない） (必須)
- [ ] 期待するテストと必要な品質ゲートを実施し、成功した
- [ ] 必要なレビュー / QA ゲートを通過した、または不要理由を記録した
- [ ] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [ ] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [ ] コミット境界を確定した

### S03 — armed input mode により選択 tile だけへ限定的なキー転送ができる (任意)
- 対象: AC-002, AC-003 / EC-002 / 制約: 非 armed 時は read-only
- 設計参照:
  - 対象IF/API: IF-001, IF-004
  - 対象テスト:
    - `tests/test_tmuxio.py`
    - `tests/test_orchestrator.py`
    - `tests/test_cli_entry.py`
- このステップで「追加しないこと（スコープ固定）」:
  - full terminal emulation
  - attach fallback 主方式

#### update_plan（着手時に登録） (必須)
- [ ] `update_plan` に、このステップの作業ブロックを登録した
- 登録する作業ブロック:
  - S03-B1: armed state 管理
  - S03-B2: tile raw input -> target forward
  - S03-B3: 品質ゲート / 報告 / コミット

#### 期待する振る舞い（テストケース） (必須)
- Given: 選択 tile が armed 状態
- When: printable text や最小キー集合を入力する
- Then: その target pane にだけ forward され、解除後は送信されない
- 観測点（UI/HTTP/DB/Log など）: pane option / input mode state / send-keys 呼び出し
- 追加/更新するテスト:
  - `tests/test_tmuxio.py`
  - `tests/test_cli_entry.py`

#### 作業ブロック（必須）
- S03-B1: armed state
  - S03-B1-I1:
    - Red: armed / disarmed の状態遷移テストを追加
    - Green: pane option または pane-local state を導入
    - Refactor: timeout / visual indicator を整理
- S03-B2: raw input forward
  - S03-B2-I1:
    - Red: printable text と escape 解除のテストを追加
    - Green: tile input proxy を追加
    - Refactor: polling boost と immediate refresh を整理
- S03-B3: 品質ゲート / 報告 / コミット
  - S03-B3-I1:
    - Red: 該当なし
    - Green: `uv run pytest`
    - Refactor: `report.md` 更新、レビュー依頼

#### ステップ末尾（省略しない） (必須)
- [ ] 期待するテストと必要な品質ゲートを実施し、成功した
- [ ] 必要なレビュー / QA ゲートを通過した、または不要理由を記録した
- [ ] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [ ] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [ ] コミット境界を確定した

### S04 — 文書と最小 E2E が新しい操作モデルを説明・保証する (任意)
- 対象: AC-003 / EC-002
- 設計参照:
  - 対象テスト:
    - `tests/test_e2e_tmux.py`
    - `README.md`
- このステップで「追加しないこと（スコープ固定）」:
  - 高度な TUI 互換の約束

#### update_plan（着手時に登録） (必須)
- [ ] `update_plan` に、このステップの作業ブロックを登録した
- 登録する作業ブロック:
  - S04-B1: README / troubleshooting 更新
  - S04-B2: 最小 E2E
  - S04-B3: 品質ゲート / 報告 / コミット

#### 期待する振る舞い（テストケース） (必須)
- Given: 入力プロキシ機能が有効
- When: README と最小 E2E を確認する
- Then: 実行手順、制約、out-of-scope、既知制限が一致している
- 観測点（UI/HTTP/DB/Log など）: README、E2E、report
- 追加/更新するテスト:
  - `tests/test_e2e_tmux.py`

#### 作業ブロック（必須）
- S04-B1: ドキュメント
  - S04-B1-I1:
    - Red: 該当なし
    - Green: README と troubleshooting に操作モデルを追記
    - Refactor: report / spec-lite との表現差を解消
- S04-B2: 最小 E2E
  - S04-B2-I1:
    - Red: 選択 tile -> target 送信の E2E を追加
    - Green: 必要最小限で通す
    - Refactor: flaky 要因を隔離
- S04-B3: 品質ゲート / 報告 / コミット
  - S04-B3-I1:
    - Red: 該当なし
    - Green: `uv run pytest`
    - Refactor: `report.md` 更新、レビュー依頼

#### ステップ末尾（省略しない） (必須)
- [ ] 期待するテストと必要な品質ゲートを実施し、成功した
- [ ] 必要なレビュー / QA ゲートを通過した、または不要理由を記録した
- [ ] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [ ] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [ ] コミット境界を確定した

## 未確定事項（TBD） (必須)
- Q-001:
  - 質問: `--selected` 自動解決を初期フェーズで入れるか
  - 選択肢:
    - A: 先に `--tile-pane` 明示指定だけにする
    - B: 最初から `--selected` も入れる
  - 推奨案（暫定）: A
  - 影響範囲: S02 / EC-001 / CLI UX
- Q-002:
  - 質問: armed mode の UI を pane title だけで表すか、status line まで使うか
  - 選択肢:
    - A: pane title の `[input]`
    - B: pane title + status
  - 推奨案（暫定）: A
  - 影響範囲: S03 / UI 影響

## 完了条件（Definition of Done） (必須)
- 対象AC/ECがすべて満たされ、テストまたは文書化された検証で保証されている
- 必要なレビュー / QA ゲートを通過している
- MUST NOT / OUT OF SCOPE を破っていない
- `report.md` と plan の進捗が一致している

## 省略/例外メモ (必須)
- 今回は分析タスクなので、上記 plan は将来実装のための提案計画である
