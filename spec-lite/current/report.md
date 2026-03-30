---
種別: 実装報告書
機能ID: "fix-tmux-headless-layout"
機能名: "headless tmux でのレイアウト復旧"
関連Issue: ["tmux split-window headless failure analysis"]
状態: "draft"
作成者: "codex"
最終更新: "2026-03-30"
依存: ["requirement.md", "design.md", "plan.md"]
---

# fix-tmux-headless-layout headless tmux でのレイアウト復旧 — 実装報告（LOG）

## 実装サマリー (任意)
- headless tmux で `split-window -p` が失敗する問題に対し、S01 では `-l` ベースの分割長算出と split API を導入した。
- 先行して行った `planning` から `spec-lite` への運用移行も、この report に前史ログとして保持している。

## 実装記録（セッションログ） (必須)

### 2026-03-30 18:40 - 18:50

#### 対象
- Step: 移行準備
- AC/EC: 該当なし

#### 実施内容
- `spec-lite` ディレクトリ構成とガイドを確認した。
- 旧 `planning/` の調査成果を引き継ぐため、`spec-lite/current/discussions/tmux-split-window-headless-analysis.md` を新規作成した。
- 旧運用の退役とドキュメント移行は別作業として進行中。

#### 実行コマンド / 結果
```bash
sed -n '1,220p' spec-lite/docs/spec-lite-guide.md
sed -n '1,220p' spec-lite/current/discussions/_template.md

# spec-lite ガイドと discussions テンプレートを確認
```

#### 変更したファイル
- `spec-lite/current/discussions/tmux-split-window-headless-analysis.md` - 今回の調査レポートを作成
- `spec-lite/current/report.md` - spec-lite 運用開始の初回ログを記録

#### コミット
- 該当なし

#### メモ
- planning 退役とドキュメント更新の完了後、この report を継続利用する。

---

### 2026-03-30 18:43 - 18:48

#### 対象
- Step: 移行実施
- AC/EC: 該当なし

#### 実施内容
- 旧 `planning/current/` の 4 文書を `spec-lite/completed/20260330_1843_planning-migration/` へアーカイブした。
- `planning/` ディレクトリを退役させた。
- 常設ドキュメントの参照を `spec-lite` ベースへ更新した。
- `docs/planning-guide.md` は削除せず、deprecated 案内として最小化した。

#### 実行コマンド / 結果
```bash
date +%Y%m%d_%H%M
git status --short
rg -n "@planning|planning/current|planning/completed" -S AGENTS.md CLAUDE.md docs README.md spec-lite/current spec-lite/docs .github

# planning ディレクトリは存在せず、アクティブ文書上の @planning 参照は deprecated 案内のみ
```

#### 変更したファイル
- `AGENTS.md` - spec-lite ベース運用へ更新
- `CLAUDE.md` - spec-lite ベース運用へ更新
- `docs/development-workflow.md` - spec-lite / plan.md / discussions に合わせて更新
- `docs/planning-guide.md` - deprecated 案内へ置換
- `spec-lite/current/report.md` - 移行完了ログを追記
- `spec-lite/completed/20260330_1843_planning-migration/requirement.md` - 旧 planning からアーカイブ
- `spec-lite/completed/20260330_1843_planning-migration/design.md` - 旧 planning からアーカイブ
- `spec-lite/completed/20260330_1843_planning-migration/task.md` - 旧 planning からアーカイブ
- `spec-lite/completed/20260330_1843_planning-migration/report.md` - 旧 planning からアーカイブ

#### コミット
- 該当なし

#### メモ
- `docs/planning-guide.md` には移行説明のため旧 `planning/current/...` 文字列が意図的に残る。

---

### 2026-03-30 18:50 - 19:05

#### 対象
- Step: 仕様策定
- AC/EC: AC-001, AC-002, AC-003, AC-004 / EC-001, EC-002, EC-003, EC-004

#### 実施内容
- `@spec-lite/current/discussions/tmux-split-window-headless-analysis.md` を根拠に、headless tmux レイアウト復旧向けの `requirement.md` を作成した。
- 同じ調査結果をもとに `design.md` を作成し、`-p` 依存解消、非破壊レイアウト適用、pane 数検証、integrity 判定順序、テスト戦略を整理した。
- TDD 実装を進められるよう `plan.md` を S01〜S03 の観測可能な成果へ分解して作成した。
- requirement / design の spec review を開始した。初回 reviewer は有効な findings を返さなかったため、fresh reviewer へ再依頼した。

#### 実行コマンド / 結果
```bash
sed -n '1,220p' spec-lite/current/requirement.md
sed -n '1,260p' spec-lite/current/design.md
sed -n '1,320p' spec-lite/current/plan.md
sed -n '1,220p' spec-lite/current/discussions/tmux-split-window-headless-analysis.md

# 調査結果を確認し、requirement / design / plan を起草
```

#### 変更したファイル
- `spec-lite/current/requirement.md` - 今回の障害修正向け要件定義を作成
- `spec-lite/current/design.md` - 実装設計とテスト戦略を作成
- `spec-lite/current/plan.md` - TDD 実装計画を作成
- `spec-lite/current/report.md` - このセッションのログを追記

#### コミット
- 該当なし

#### メモ
- spec review の findings / review_status を待っている。

### 2026-03-30 19:05 - 19:20

#### 対象
- Step: 仕様レビュー是正
- AC/EC: AC-002 / EC-002 / EC-004

#### 実施内容
- spec review で指摘された 2 点を requirement / design に反映した。
- 非破壊 apply の具体方式を「staging window を作って成功後に `dashboard:0` と入れ替える」方式へ固定した。
- `-l` の sizing ルールを「absolute-cell を既定、異常値時のみ `%` fallback」へ固定した。
- `plan.md` も同前提へ合わせて整合を取った。

#### 実行コマンド / 結果
```bash
sed -n '90,220p' spec-lite/current/requirement.md
sed -n '90,260p' spec-lite/current/design.md

# spec review 指摘を確認し、requirement / design / plan を更新
```

#### 変更したファイル
- `spec-lite/current/requirement.md` - AC-002 と TBD を具体化
- `spec-lite/current/design.md` - staging window 方式と absolute-cell 既定を明文化
- `spec-lite/current/plan.md` - 実装計画を更新設計へ同期
- `spec-lite/current/report.md` - 是正ログを追記

#### コミット
- 該当なし

#### メモ
- 有効な `review_status` を返す spec reviewer 応答を回収中。

---

### 2026-03-30 19:20 - 19:55

#### 対象
- Step: S01
- AC/EC: AC-001 / EC-004

#### 実施内容
- `layout.py` に `build_split_lengths()` を追加し、headless 向け split 長算出を absolute-cell 既定、`length <= 0` 時のみ `%` fallback として実装した。
- `tmuxio.py` の CLI / libtmux 両経路で `split-window -l` を使うように変更し、公開 IF では `length` を主契約としつつ `percent` 互換も維持した。
- `tests/test_layout.py` と `tests/test_tmuxio.py` を Red → Green で更新し、正常系に加えて `length` / `percent` 未指定時の `ValueError` 失敗系も追加した。
- `code_reviewer` と `qa_reviewer` のレビューを実施し、初回 QA 指摘だった失敗系テスト不足を是正後、fresh review で両方 `pass` を確認した。

#### 実行コマンド / 結果
```bash
uv run pytest tests/test_layout.py tests/test_tmuxio.py -q
# 16 passed in 0.03s

uv run pytest tests/test_tmuxio.py -q
# 10 passed in 0.03s

uv run pytest tests/test_layout.py tests/test_tmuxio.py -q
# 18 passed in 0.03s
```

#### 変更したファイル
- `tmux_dashboard/layout.py` - `-l` 向けの分割長算出 helper を追加
- `tmux_dashboard/tmuxio.py` - CLI / libtmux の split API を `length` 契約へ移行し `-l` を使用
- `tests/test_layout.py` - 分割長算出の正常系 / fallback 系テストを追加
- `tests/test_tmuxio.py` - CLI / libtmux 両経路の `-l` 呼び出しと未指定失敗系を検証
- `spec-lite/current/report.md` - S01 の実装 / 検証 / レビュー結果を追記
- `spec-lite/current/plan.md` - S01 進行状態を更新

#### コミット
- `9f30c345e1bbd1b409daa27240a51fbb8e6443a2`
- `fix(tmux): headless split を -l ベースに移行`

#### メモ
- 初回 QA は `review_status: pass` だったが non-blocking finding として失敗系テスト不足を指摘したため、ユーザー指示に従って是正後に fresh review を再実施した。

---

### 2026-03-30 20:00 - 23:40

#### 対象
- Step: S02
- AC/EC: AC-002, AC-003, AC-004 / EC-001, EC-002, EC-003

#### 実施内容
- `tmuxio.py` に window lifecycle API（`create_window`, `swap_window`, `kill_window`）を CLI / libtmux / TmuxIO 全体で追加し、staging window を扱えるようにした。
- `orchestrator.py` に `LayoutApplyResult`、`validate_mapping()`、staging window ベースの non-destructive apply、0 セッション早期 return、signature 変化時の integrity 順序見直しを実装した。
- staging integrity が fail-open になる blocker を是正し、strict モードの integrity 判定と回帰テストを追加した。
- staging 作成時のサイズ継承と respawn 後の pane title 再適用を追加し、E2E で見つかったサイズ巻き戻り・title 上書き回帰を是正した。
- cleanup 再失敗時の warning ログも追加し、最後の non-blocking 指摘まで解消した。
- `code_reviewer` / `qa_reviewer` を複数回回し、blocker 2 件と non-blocking 1 件を是正後、最終的に両 review を `pass` にした。

#### 実行コマンド / 結果
```bash
uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_pane_integrity.py -q
# 25 passed in 0.04s

uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_pane_integrity.py -q
# 27 passed in 0.04s

uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_pane_integrity.py -q
# 28 passed in 0.04s

uv run pytest tests/test_orchestrator.py -q
# 9 passed in 0.02s

uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_pane_integrity.py -q
# 29 passed in 0.04s

uv run pytest -q
# 81 passed, 1 xfailed in 1.39s
```

#### 変更したファイル
- `tmux_dashboard/orchestrator.py` - staging window による非破壊 apply、mapping 検証、strict integrity、0 セッション分岐、title 再適用、cleanup warning を実装
- `tmux_dashboard/tmuxio.py` - window lifecycle API と staging サイズ継承、libtmux の staging 関連挙動補正を実装
- `tests/test_tmuxio.py` - window lifecycle API とサイズ継承の unit test を追加
- `tests/test_orchestrator.py` - non-destructive apply、pane 不足、strict integrity、cleanup warning の回帰テストを追加
- `tests/test_pane_integrity.py` - strict integrity と run_once 順序の回帰テストを追加
- `spec-lite/current/plan.md` - S02 の対象テスト明示と進捗状態を更新
- `spec-lite/current/report.md` - S02 の実装 / 検証 / レビュー結果を追記

#### コミット
- `b711add3027d5dc0ef7dfeb2bffa69c055ac42e2`
- `fix(tmux): 非破壊レイアウト適用と整合性検証を強化`

#### メモ
- QA の最終確認では `uv run pytest -q -rxX` で既知 headless ケースが `xfailed` として残ることを確認しており、これは S03 の E2E 整理対象とする。

---

### 2026-03-30 23:40 - 2026-03-31 00:30

#### 対象
- Step: S03
- AC/EC: AC-001, AC-003 / EC-002, EC-004

#### 実施内容
- `orchestrator.py` の staging 昇格前判定を title 完全一致依存から切り離し、pane 構造と件数整合を確認する `validate_staging_structure()` ベースへ寄せた。
- `apply_layout()` が同一サイクル中に `scan_sessions()` し直さないよう `sessions` 引数を受け取る形へ変更し、`run_once()` で確定した session 集合を固定化した。
- `validate_mapping()` に exact 条件を追加し、staging 側の pane 構造が E2E の期待と一致する場合のみ昇格するようにした。
- `tests/test_e2e_tmux.py` の `test_e2e_many_sessions_grid_exact` と `test_e2e_resize_up_and_down` を通常検証へ戻し、headless でも `xfail` なしで通る状態にした。
- code review の non-blocking 指摘に対応し、post-respawn の一時的不整合が解消された後に `_last_signature` が不要に無効化されないよう `invalidate_signature` 制御と回帰テストを追加した。
- 最終的に `code_reviewer` / `qa_reviewer` とも `pass`、全体回帰 `84 passed` → 最終確認で `85 passed` を確認した。

#### 実行コマンド / 結果
```bash
uv run pytest tests/test_orchestrator.py tests/test_pane_integrity.py -q
# 18 passed in 0.02s

uv run pytest tests/test_orchestrator.py tests/test_e2e_tmux.py -q -rxX
# 16 passed in 1.87s

uv run pytest -q
# 84 passed in 1.84s

uv run pytest tests/test_orchestrator.py -q
# 11 passed in 0.08s

uv run pytest tests/test_orchestrator.py tests/test_pane_integrity.py tests/test_e2e_tmux.py -q
# 25 passed in 1.70s

uv run pytest -q
# 85 passed
```

#### 変更したファイル
- `tmux_dashboard/orchestrator.py` - staging 構造検証、sessions 固定化、exact mapping、post-respawn signature 保持を実装
- `tests/test_e2e_tmux.py` - 2つの E2E ケースを通常検証へ戻し、`xfail` 分岐を削除/縮小
- `tests/test_orchestrator.py` - staging 構造検証と post-respawn signature 保持の回帰テストを追加
- `tests/test_pane_integrity.py` - S03 の整合性判定仕様に合わせて期待値を更新
- `spec-lite/current/report.md` - S02/S03 のコミット情報と検証結果を追記
- `spec-lite/current/plan.md` - S03 の進捗状態を更新

#### コミット
- `af191807638d2192f0551200d24e3074eb4ae24f`
- `fix(tmux): headless e2e を通常検証へ移行`

#### メモ
- `dynamic_add_then_remove` には headless 条件での動的 `xfail` 分岐がまだ残るが、今回の S03 受け入れ条件で対象としていた 2 ケースの通常検証化は達成した。

---

## 遭遇した問題と解決 (任意)
- 問題: headless tmux で `split-window -p` が `size missing` で失敗し、dashboard が 1 pane のまま復旧しない
  - 解決: `-l` ベースの split へ移行し、staging window による non-destructive apply と E2E 回帰テストまで通して復旧した

## 学んだこと (任意)
- detached/headless tmux では pane title や window size の扱いがクライアント接続時と揺れやすく、split 成功だけでなく昇格条件の設計が重要だった
- staging 昇格前に title 完全一致まで要求すると fail-closed が過剰になりやすく、構造検証と最終 title 整合を分ける方が安定した
- ...

## 今後の推奨事項 (任意)
- `test_e2e_dynamic_add_then_remove` に残る headless 条件の動的 `xfail` 分岐は、必要なら次の改善対象として通常検証化を検討する
- title を継続的に上書きする特殊端末があるなら、pane title 再適用の再試行戦略を設定化してもよい
- ...

## 省略/例外メモ (必須)
- 該当なし
