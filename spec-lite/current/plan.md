---
種別: 実装計画書
機能ID: "fix-tmux-headless-layout"
機能名: "headless tmux でのレイアウト復旧"
関連Issue: ["tmux split-window headless failure analysis", "wrapper create window root cause analysis", "wrapper create-window acceptance review 20260331", "window-size manual resize follow-up analysis 20260331", "wrapper visible window duplication analysis 20260401"]
状態: "draft"
作成者: "codex"
最終更新: "2026-04-01"
依存: ["requirement.md", "design.md"]
---

# fix-tmux-headless-layout headless tmux でのレイアウト復旧 — 実装計画（TDD: Red → Green → Refactor）

## この計画で満たす要件ID (必須)
- 対象AC: AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007, AC-008, AC-009
- 対象EC: EC-001, EC-002, EC-003, EC-004, EC-005, EC-006, EC-007, EC-008, EC-009, EC-010, EC-011
- 対象制約（該当があれば）:
  - 依存追加なし
  - CLI 互換維持
  - dashboard 以外へ非侵襲

## ステップ一覧（観測可能な振る舞い） (必須)
- active / current steps:
  - [x] S01: `-l` ベースの分割 API と分割長算出を追加し、headless で split が通る土台を作る
  - [x] S02: orchestrator を非破壊 apply と pane 数検証に対応させ、失敗を可視化する
  - [x] S03: integrity 判定順序と E2E/回帰テストを整え、headless 復旧を保証する
  - [x] S04: wrapper 経路の `create_window` 根本原因を除去し、same-name 条件の回帰テストで固定する（code-complete。acceptance follow-up は S05）
  - [x] S05: 受け入れ検査の fail findings を解消し、default driver / 0 セッション収束の契約を完成させる
  - [x] S06: `window-size latest` を dashboard 管理契約として固定し、outer Terminal resize への追随を自動回復付きで保証する
  - [x] S07: visible dashboard window 名 invariant を固定し、wrapper 再起動で window が増殖しないようにする
- historical / superseded steps（任意）:
  - [x] 旧 `planning/current/task.md` による `-p` ベース前提の実装計画（`@spec-lite/completed/20260330_1843_planning-migration/task.md` にアーカイブ済み）

## 現行の実行対象スコープ (任意)
- S05: 完了。libtmux fail-closed の取りこぼし補完、ghost residual queue 防止、0 セッション stale title 解消、追加受け入れ回帰の自動化を実施済み
- S06: 完了。`window-size manual` 汚染の自動回復、wrapper / runner 両経路の `latest` 保証、resize 追随回帰の自動検証と手動検証記録を実施済み
- S07: 完了。staging window の一時命名、swap 後 rename、`automatic-rename off`、wrapper startup self-heal、visible dashboard window 一意性の回帰を追加した

## ネスト運用ルール (必須)
- トップレベルステップ `Sxx` は「観測可能な成果」で分ける
- サブステップ `Bx` は「作業ブロック」とし、同じ関心事または同じ変更境界を持つ仕事の束で分ける
- サブサブステップ `Ix` は「イテレーション」とし、1つの `Red → Green → Refactor` を完結できる最小単位で分ける
- 品質ゲート工程は、新規実装の TDD ではなく `検証 / 是正 / 再検証` の反復として扱ってよい

### 要件 ↔ ステップ対応表 (必須)
- active / current trace:
  - AC-001 → S01, S03
  - AC-002 → S02, S05
  - AC-003 → S02, S03
  - AC-004 → S02
  - AC-005 → S04
  - AC-006 → S04, S05
  - AC-007 → S05
  - AC-008 → S06
  - AC-009 → S07
  - EC-001 → S02, S05
  - EC-002 → S02, S03
  - EC-003 → S02
  - EC-004 → S01, S03
  - EC-005 → S04
  - EC-006 → S04
  - EC-007 → S04, S05
  - EC-008 → S05
  - EC-009 → S06
  - EC-010 → S06
  - EC-011 → S07
  - 非交渉制約 → S01, S02, S03, S04, S05, S06, S07

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
- [x] `update_plan` に、このステップの作業ブロックを登録した
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
- [x] 期待するテストと必要な品質ゲートを実施し、成功した
- [x] 必要なレビュー / QA ゲートを通過した、または不要理由を記録した
- [x] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [x] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [x] コミット境界を確定した（コミットしない場合は理由を記録した）

### S02 — レイアウト適用を非破壊にし、pane 数不足を黙殺しない (必須)
- 対象: AC-002 / AC-003 / AC-004 / EC-001 / EC-002 / EC-003 / 制約: dashboard 非侵襲
- 設計参照:
  - 対象IF/API: IF-004, IF-005
  - 対象テスト:
    - `tests/test_tmuxio.py`
    - `tests/test_orchestrator.py`
    - `tests/test_pane_integrity.py`
- このステップで「追加しないこと（スコープ固定）」:
  - headless E2E の本格追加

#### update_plan（着手時に登録） (必須)
- [x] `update_plan` に、このステップの作業ブロックを登録した
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
  - `tests/test_tmuxio.py`
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
    - Green: `uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_pane_integrity.py -q` を実行し、成功を確認する
    - Refactor: `spec-lite/current/report.md` を更新し、コミット境界を確定する

#### ステップ末尾（省略しない） (必須)
- [x] 期待するテストと必要な品質ゲートを実施し、成功した
- [x] 必要なレビュー / QA ゲートを通過した、または不要理由を記録した
- [x] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [x] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [x] コミット境界を確定した（コミットしない場合は理由を記録した）

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
- [x] `update_plan` に、このステップの作業ブロックを登録した
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
  - `tests/test_e2e_tmux.py`（actual wrapper path を優先）
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
- [x] 期待するテストと必要な品質ゲートを実施し、成功した
- [x] 必要なレビュー / QA ゲートを通過した、または不要理由を記録した
- [x] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [x] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [x] コミット境界を確定した（コミットしない場合は理由を記録した）

### S04 — wrapper 経路の create_window 根本原因を除去し、same-name 条件を固定する (必須)
- 対象: AC-005 / AC-006 / EC-005 / EC-006 / EC-007 / 制約: CLI 互換維持, wrapper visible window 名維持
- 設計参照:
  - 対象IF/API: IF-006, IF-008
- 対象テスト:
    - `tests/test_tmuxio.py`
    - `tests/test_orchestrator.py`
    - `tests/test_e2e_tmux.py`
    - `tests/test_cli_entry.py`
    - CLI entrypoint failure test
- このステップで「追加しないこと（スコープ固定）」:
  - wrapper の visible window 名変更
  - 新規 CLI オプション追加
  - renderer / tile 表示仕様変更

#### update_plan（着手時に登録） (必須)
- [x] `update_plan` に、このステップの作業ブロックを登録した
- 登録する作業ブロック:
  - S04-B1: `create_window()` 契約の Red/Green
  - S04-B2: wrapper same-name regression の Red/Green
  - S04-B3: 品質ゲート / 報告 / コミット

#### 期待する振る舞い（テストケース） (必須)
- Given: wrapper と同じ `dashboard` session / visible window `dashboard` 条件、または `new-window` が失敗する driver 条件
- When: staging window を作成し、wrapper または direct runner を 1 サイクル実行する
- Then: `create_window()` は `_pick_staging_window_index()` が選んだ未使用 index に対して `session:window_index` target で window を実在作成するか、失敗時は driver 例外 / `run_once()` 明示ログ / CLI exit 0 として観測できる。wrapper 経路でも `dashboard:0` に期待 pane が作成される
- 観測点（UI/HTTP/DB/Log など）: `tmux list-windows`, `tmux list-panes`, driver 例外, `run_once()` / CLI ログ, wrapper runner ログ
- 追加/更新するテスト:
  - `tests/test_tmuxio.py`
  - `tests/test_orchestrator.py`
  - `tests/test_e2e_tmux.py`
  - `tests/test_cli_entry.py`
  - CLI entrypoint failure test

#### 作業ブロック（必須）
- S04-B1: `create_window()` 契約修正
  - S04-B1-I1:
    - Red: CLI / libtmux の `create_window()` が `-t session_name` を使い、same-name 条件で失敗または phantom target を返すテストを追加する
    - Green: `create_window()` は呼び出し元から渡された `window_index` をそのまま `session:window_index` target として使い、libtmux は `returncode` / `stderr` / 実在確認で fail-closed にする
    - Refactor: created target 解決と実在確認を helper 化し、CLI / libtmux で契約を揃える
- S04-B2: wrapper / orchestrator 経路固定
  - S04-B2-I1:
    - Red: wrapper と同じ same-name 条件で `dashboard:0` が 1 pane のまま残る integration test を追加する
    - Green: wrapper 経路でも staging window 作成と non-destructive apply が通るよう実装を調整する
    - Refactor: エラーログを `pane shortage` ではなく create/swap failure が分かる形へ整理する
  - S04-B2-I2:
    - Red: staging window 作成失敗時に orchestrator が phantom target を前提に進んでしまうテストを追加する
    - Green: orchestrator が create failure を explicit に扱い、既存 dashboard と runner window を保持するようにする
    - Refactor: create failure path のログ / cleanup を簡潔に整理する
  - S04-B2-I3:
    - Red: `swap-window` 失敗時に `dashboard:0` が変化する、または error ログが不足するテストを追加する
    - Green: orchestrator が swap failure を explicit に扱い、既存 dashboard と runner window を保持するようにする
    - Refactor: swap failure path の invariant 確認を明確にする
  - S04-B2-I4:
    - Red: cleanup warning で残置した旧 window が次サイクルで再cleanupされない、または再失敗で新規 staging を妨げるテストを追加する
    - Green: residual window の best-effort cleanup retry を実装し、成功でも失敗でも新規レイアウト進行を妨げないようにする
    - Refactor: residual target の保持 / クリア条件を明確にする
- S04-B3: CLI observability
  - S04-B3-I1:
    - Red: create failure または swap failure で CLI が非 0 終了する、または明示ログを残さないテストを追加する
    - Green: `--once` / 通常ループとも exit 0 と error ログ、dashboard 不変を満たすようにする
    - Refactor: CLI entrypoint の failure logging を helper 化する
- S04-B4: 品質ゲート / 報告 / コミット
  - S04-B4-I1:
    - Red: 該当なし
    - Green: `uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_e2e_tmux.py tests/test_cli_entry.py -q` と `uv run pytest -q` を実行し、成功を確認する
    - Refactor: `spec-lite/current/report.md` を更新し、review スコープでコミット境界を確定する

#### ステップ末尾（省略しない） (必須)
- [x] 期待するテストと必要な品質ゲートを実施し、成功した
- [x] 必要なレビュー / QA ゲートを通過した、または不要理由を記録した（コミット前レビューはユーザー対応待ち）
- [x] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [x] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [x] コミット境界を確定した（コミットは未実施。ユーザーレビュー待ち）

### S05 — 受け入れ検査の fail findings を解消し、default driver と 0 セッション収束を完成させる (必須)
- 対象: AC-002 / AC-006 / AC-007 / EC-007 / EC-008 / 制約: CLI 互換維持, dashboard 非侵襲
- 設計参照:
  - 対象IF/API: IF-006a, IF-006b, IF-007, IF-008
- 対象テスト:
    - `tests/test_tmuxio.py`
    - `tests/test_orchestrator.py`
    - `tests/test_e2e_tmux.py`
- このステップで「追加しないこと（スコープ固定）」:
  - wrapper の attach/TTY 振る舞い変更
  - renderer / tile 表示仕様変更
  - 新規 CLI オプション追加

#### update_plan（着手時に登録） (必須)
- [x] `update_plan` に、このステップの作業ブロックを登録した
- 登録する作業ブロック:
  - S05-B1: libtmux fail-closed 補完の Red/Green
  - S05-B2: ghost residual queue 防止の Red/Green
  - S05-B3: 0 セッション stale title 解消の Red/Green
  - S05-B4: 受け入れ回帰 / QA / 報告 / コミット

#### 期待する振る舞い（テストケース） (必須)
- Given: tmux / libtmux が `swap-window` または `kill-window` failure を返す条件、または create failure で staging target が未作成の条件、または直前サイクルの pane title が残ったまま表示対象セッションが 0 件になる条件
- When: `run_once()` または wrapper/direct runner を実行する
- Then: default driver でも swap / cleanup failure は例外化され、missing staging target は residual queue に積まれず、0 セッション時は単一 pane かつ stale でない title に収束する。create/swap 系 failure を再度触っても CLI entrypoint は exit 0 と明示ログ契約を維持する
- 観測点（UI/HTTP/DB/Log など）: driver 例外、orchestrator ログ、`tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}'`, residual queue 状態、E2E テスト結果
- 追加/更新するテスト:
  - `tests/test_tmuxio.py`
  - `tests/test_orchestrator.py`
  - `tests/test_e2e_tmux.py`

#### 作業ブロック（必須）
- S05-B1: libtmux fail-closed 補完
  - S05-B1-I1:
    - Red: libtmux `swap_window()` / `kill_window()` が tmux failure を silent success にしてしまうテストを追加する
    - Green: `swap_window()` / `kill_window()` でも `_raise_if_cmd_failed()` 相当の失敗検知を適用する
    - Refactor: driver の tmux command result 検査 helper を整理し、create/swap/kill の契約を揃える
- S05-B2: ghost residual queue 防止
  - S05-B2-I1:
    - Red: create failure で missing staging target が residual queue に積まれ、後続 retry を塞ぐテストを追加する
    - Green: create failure path で target 実在確認を行い、missing target は cleanup warning の補足のみに留めて queue へ積まない
    - Refactor: residual target の enqueue 条件を helper 化し、swap 後 cleanup 失敗との分岐を明確にする
- S05-B3: 0 セッション stale title 解消
  - S05-B3-I1:
    - Red: 直前サイクルの pane title が 0 セッション short-circuit 後も残るテストを追加する
    - Green: 0 セッション時に単一 pane へ収束させたあと、pane title を空文字または設計で定めた中立値へ更新する
    - Refactor: 0 セッション path の title policy を helper 化し、integrity / respawn ロジックとの境界を整理する
- S05-B4: 受け入れ回帰 / QA / 報告 / コミット
  - S05-B4-I1:
    - Red: 受け入れ検査で観測した 3 つの fail findings を再現する回帰テスト群を揃える
    - Green: `uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_e2e_tmux.py tests/test_cli_entry.py -q` と `uv run pytest -q` を実行し、成功を確認する。加えて `qa_reviewer` または同等の受け入れ再判定で `acceptance-review-wrapper-fix-20260331.md` の 3 findings が閉じたことを確認する
    - Refactor: `spec-lite/current/report.md` と受け入れ検査レポートを更新し、レビュー境界とコミット境界を一致させる

#### ステップ末尾（省略しない） (必須)
- [x] 期待するテストと必要な品質ゲートを実施し、成功した
- [x] 必要なレビュー / QA ゲートを通過した。少なくとも `qa_reviewer` または同等の受け入れ再判定で 3 つの fail findings が解消済みと確認した
- [x] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [x] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [x] コミット境界を確定した（コミットしない場合は理由を記録した）
  - follow-up: `spec-lite/current/discussions/acceptance-review-wrapper-fix-20260331-s05-rereview.md` を authoritative な再判定記録として追加し、wrapper path の zero-session title cleanup E2E を補完した

### S06 — `window-size latest` を管理契約として固定し、resize 追随を保証する (必須)
- 対象: AC-008 / EC-009 / EC-010 / 制約: CLI 互換維持, dashboard 以外の tmux 設定非侵襲
- 設計参照:
  - 対象IF/API: IF-009, IF-010, IF-011
- 対象テスト:
    - `tests/test_tmuxio.py`
    - `tests/test_orchestrator.py`
    - `tests/test_e2e_tmux.py`
- このステップで「追加しないこと（スコープ固定）」:
  - `dashboard` 以外の session / global tmux option の変更
  - 新規 CLI オプション追加
  - pane 表示仕様やセッション選定仕様の変更

#### update_plan（着手時に登録） (必須)
- [x] `update_plan` に、このステップの作業ブロックを登録した
- 登録する作業ブロック:
  - S06-B1: tmuxio window option API の Red/Green
  - S06-B2: wrapper / orchestrator の `latest` 保証 Red/Green
  - S06-B3: resize 追随 E2E と手動検証
  - S06-B4: 品質ゲート / 報告 / コミット

#### 期待する振る舞い（テストケース） (必須)
- Given: 既存の `dashboard` target が `window-size manual` または `latest` 以外で残っている条件、または outer Terminal 相当のサイズ変更がある条件
- When: wrapper または direct runner の 1 サイクル以上を実行する
- Then: `dashboard` target は `window-size latest` へ収束し、以後の resize で `dashboard:0` の `window_width` と pane 幅/高さが追随して更新される
- 観測点（UI/HTTP/DB/Log など）: `tmux show-options -t dashboard:0 -w`, `tmux display-message -p -t dashboard:0 '#{window_width} #{window_height}'`, `tmux list-panes -t dashboard:0 ...`, E2E テスト結果, 手動検証記録
- 追加/更新するテスト:
  - `tests/test_tmuxio.py`
  - `tests/test_orchestrator.py`
  - `tests/test_e2e_tmux.py`

#### 作業ブロック（必須）
- S06-B1: tmuxio window option API
  - S06-B1-I1:
    - Red: CLI / libtmux driver が window-local option の取得/設定契約を持たないことを示すテストを追加する
    - Green: `get_window_option()` / `set_window_option()` を追加し、`window-size` の取得と更新を両 driver で扱えるようにする
    - Refactor: tmux command helper を整理し、window option 系のエラーメッセージ契約を揃える
- S06-B2: wrapper / orchestrator での `latest` 保証
  - S06-B2-I1:
    - Red: wrapper 起動時に `dashboard` target が `window-size manual` のまま残るテストを追加する
    - Green: visible dashboard window 確定後に wrapper が `window-size latest` を設定する
    - Refactor: wrapper 内の preflight 順序を整理し、既存 runner respawn 条件と干渉しない形にする
  - S06-B2-I2:
    - Red: runner preflight が `window-size manual` を検出しても回復しないテストを追加する
    - Green: `run_once()` 前に `ensure_dashboard_window_policy(window_target)` を実行し、`latest` 以外なら是正する
    - Refactor: option drift のログ方針を整理し、正常是正と失敗ログを分ける
- S06-B3: resize 追随検証
  - S06-B3-I1:
    - Red: `window-size manual` の既存 dashboard が outer resize 後も `window_width` を更新しない E2E を追加する
    - Green: `latest` 保証後に `display-message` と `list-panes` が追随を示すことを確認する
    - Refactor: headless E2E と wrapper E2E のセットアップ重複を整理する
  - S06-B3-I2:
    - Red: 該当なし
    - Green: 手動検証で `show-options`, `display-message`, `list-panes` を使って `latest` 収束と resize 追随を確認し、独立レポートへ記録する
    - Refactor: 手動検証の再利用可能な確認コマンドを整理する
- S06-B4: 品質ゲート / 報告 / コミット
  - S06-B4-I1:
    - Red: 該当なし
    - Green: `uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_e2e_tmux.py -q` と `uv run pytest -q` を実行し、成功を確認する
    - Refactor: `spec-lite/current/report.md` と手動検証レポートを更新し、レビュー境界とコミット境界を一致させる

#### ステップ末尾（省略しない） (必須)
- [x] 期待するテストと必要な品質ゲートを実施し、成功した
- [x] 必要なレビュー / QA ゲートを通過した、または不要理由を記録した
- [x] `spec-lite/current/report.md` に実行コマンド / 結果 / 変更ファイル / 判断を記録した
- [x] `update_plan` を更新し、このステップの作業ブロックを完了にした
- [x] コミット境界を確定した（コミットしない場合は理由を記録した）

### S07 — visible dashboard window 名 invariant を固定し、wrapper 再起動で window が増殖しないようにする (必須)
- 対象: AC-009 / EC-011 / 制約: CLI 互換維持, dashboard 以外の tmux 設定非侵襲
- 設計参照:
  - 対象IF/API: `TmuxIO.create_window(..., window_name=...)`, `TmuxIO.rename_window(...)`
  - 対象テスト:
    - `tests/test_tmuxio.py`
    - `tests/test_orchestrator.py`
    - `tests/test_wrapper_runtime.py`
    - `tests/test_e2e_tmux.py`
- このステップで「追加しないこと（スコープ固定）」:
  - pane 表示仕様やセッション選定仕様の変更
  - runner の描画アルゴリズム変更

#### update_plan（着手時に登録） (必須)
- [x] `update_plan` に、このステップの作業ブロックを登録した
- 登録する作業ブロック:
  - S07-B1: tmuxio window rename API の Red/Green
  - S07-B2: orchestrator の post-swap rename invariant
  - S07-B3: wrapper startup self-heal と duplicate cleanup
  - S07-B4: E2E / 手動確認 / 報告 / コミット

#### 期待する振る舞い（テストケース） (必須)
- Given: `swap-window` で staging 由来の既定名 window が visible target に昇格する条件、または wrapper 起動時に duplicate non-runner windows が残っている条件
- When: orchestrator がレイアウト適用を完了する、または wrapper を起動する
- Then: visible target は必ず `dashboard` 名へ戻り、`dashboard` session 内の tool-managed window は visible dashboard 1 枚と runner 1 枚へ収束する
- 観測点（UI/HTTP/DB/Log など）: `tmux list-windows -t dashboard -F '#{window_index}|#{window_name}|#{window_active}'`, runner `pane_start_command`, unit/E2E/手動確認結果

#### 作業ブロック（必須）
- S07-B1: tmuxio window naming API
  - S07-B1-I1:
    - Red: create/rename lifecycle テストを追加し、window 名を制御できない現状を失敗で固定する
    - Green: CLI / libtmux driver に `window_name` 付き `create_window()` と `rename_window()` を追加する
    - Refactor: lifecycle command helper と fail-closed 契約を整理する
- S07-B2: orchestrator の post-swap invariant
  - S07-B2-I1:
    - Red: swap 後に visible window 名が `dashboard` に戻らないテストを追加する
    - Green: staging 一時名、old window 退避名、visible target の `dashboard` rename を実装する
    - Refactor: staging / retired window 名の helper を導入し、命名契約を固定する
- S07-B3: wrapper startup self-heal
  - S07-B3-I1:
    - Red: duplicate visible windows があると wrapper が stale target を温存するテストを追加する
    - Green: canonical visible window 選定、`dashboard` rename、duplicate non-runner cleanup を実装する
    - Refactor: visible window 探索と cleanup helper を shell 関数へ抽出する
- S07-B4: E2E / 手動確認 / 報告 / コミット
  - S07-B4-I1:
    - Red: wrapper E2E に visible dashboard window 一意性の検証を追加する
    - Green: wrapper path / zero-session / resize 回帰で window 名集合が `{"dashboard", "__tmux_dashboard_runner__"}` に収束することを確認する
    - Refactor: `spec-lite/current/report.md` に手動確認ログと判断を追記し、コミット境界を確定する

## 未確定事項（TBD） (必須)
- 該当なし

## 完了条件（Definition of Done） (必須)
- 対象AC/ECがすべて満たされ、テストまたは文書化された検証で保証されている
- `uv run pytest -q` がグリーンである
- headless 回帰と wrapper same-name 回帰を再現するテストが追加され、今回の障害モードを自動検証できる
- 現行スコープである S05 について、`acceptance-review-wrapper-fix-20260331.md` の 3 findings が再判定で closed と確認されている
- 現行スコープが S06 の場合、`window-size latest` 収束と resize 追随の回帰テスト、および独立した手動検証レポートが記録されている
- 必要なレビュー / QA ゲートを通過している
- MUST NOT / OUT OF SCOPE を破っていない
- `report.md` と plan の進捗が一致している

## 省略/例外メモ (必須)
- 該当なし
