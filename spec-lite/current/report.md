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

### 2026-03-31 00:00 - 00:25

#### 対象
- Step: wrapper 障害調査
- AC/EC: 調査タスクのため該当なし

#### 実施内容
- `./tmux-dashboard` 経由では依然として `dashboard:0` が 1 pane のまま残ることを実環境で再現した。
- runner log の `pane shortage: tiles=0 sessions=3` を起点に、staging window 作成から pane 列挙までを切り分けた。
- `LibtmuxDriver.create_window()` を独立ソケットで直接観測し、`dashboard:99` を返すのに実際には window が作成されていないことを確認した。
- raw tmux 実験により、`tmux new-window -t dashboard` は session 名と window 名がどちらも `dashboard` の場合に `create window failed: index 0 in use` で失敗し、`-t dashboard:99` なら成功することを確認した。
- 以上から、本質原因は `create_window()` が `-t session_name` を使っていること、および wrapper が visible window を `dashboard` と命名して session/window 同名条件を作っていることだと特定した。
- 調査結果は `spec-lite/current/discussions/wrapper-create-window-root-cause-20260331.md` にまとめた。

#### 実行コマンド / 結果
```bash
./tmux-dashboard
# wrapper 経由で runner log に以下を確認:
# non-destructive apply failed: pane shortage: tiles=0 sessions=3

---

### 2026-03-31 16:20 - 17:10

#### 対象
- Step: リサイズ追随不良の追加分析
- AC/EC: 調査タスクのため該当なし

#### 実施内容
- ユーザー提供の `tmux list-sessions` / `tmux list-panes` / `tmux list-windows` / `tmux display-message` 出力を分析し、`dashboard:0` が実際に `dashboard` 以外の全 session を pane 化していることを確認した。
- ユーザーから「dashboard 以外の全 session を表示する」は仕様であることを確認したため、session 数過多は主因候補から外した。
- `configs/dashboard.yaml` の `min_tile_width: 65` を再確認し、幅 `191`・session 数 `3` では 2 列レイアウトが正しいことを整理した。
- そのうえで、スクリーンショット `spec-lite/current/discussions/スクリーンショット 2026-03-31 16.39.34.png` を確認し、「外側 Terminal は広いのに内側 tmux window は狭いままで、右側がドット状の unused space になる」症状を確認した。
- `dashboard|2|2` という実機出力と tmux の `window-size` / multi-client policy を照合し、現在の本命は「`dashboard` session に 2 client が attached しており、tmux が現在の visible client ではない別 client のサイズで window を維持している」ことだと判断した。
- 調査結果を `spec-lite/current/discussions/resize-follow-up-analysis-20260331.md` に追記し、tmux wiki と man page を参考資料として追加した。

#### 実行コマンド / 結果
```bash
sed -n '1,260p' spec-lite/current/discussions/resize-follow-up-analysis-20260331.md
sed -n '1,220p' spec-lite/current/report.md

# 既存の分析レポートと実装報告を確認し、追加分析を追記
```

#### 変更したファイル
- `spec-lite/current/discussions/resize-follow-up-analysis-20260331.md` - スクリーンショットと multi-client window-size 仮説を追記
- `spec-lite/current/report.md` - 今回の追加分析ログを追記

#### コミット
- 該当なし

#### メモ
- 次に本質原因を完全確定するには、ユーザー実機で `tmux show-options -t dashboard -w | rg 'window-size|aggressive-resize'` と `tmux list-clients -t dashboard -F '#{client_tty}|#{client_width}x#{client_height}|#{session_name}'` の取得が必要。

---

### 2026-03-31 17:10 - 17:20

#### 対象
- Step: リサイズ追随不良の原因確定
- AC/EC: 調査タスクのため該当なし

#### 実施内容
- ユーザー実機から `window-size manual` と `dashboard` に attach している 2 client のサイズ情報を取得した。
- `266x99` と `278x99` の client が attach しているにもかかわらず、`dashboard:0` の実効幅が以前の `191` のまま固定されていることから、client サイズ不足ではなく `manual` 固定が主因だと確定した。
- これにより、「外側 Terminal を広げても中の dashboard window が追随しない」症状のクリティカルな本質原因を tmux 側の `window-size manual` と判断した。
- 調査レポートを更新し、今後の修正論点として `window-size` の明示設定または `resize-window` の明示更新が必要であることを記録した。

#### 実行コマンド / 結果
```bash
# ユーザー実機で取得された証跡
tmux show-options -t dashboard -w | rg 'window-size|aggressive-resize'
# => window-size manual

tmux list-clients -t dashboard -F '#{client_tty}|#{client_width}x#{client_height}|#{session_name}'
# => /dev/ttys019|266x99|dashboard
# => /dev/ttys026|278x99|dashboard
```

#### 変更したファイル
- `spec-lite/current/discussions/resize-follow-up-analysis-20260331.md` - `window-size manual` を根本原因として追記
- `spec-lite/current/report.md` - 原因確定ログを追記

#### コミット
- 該当なし

#### メモ
- 次フェーズでは、manual 固定をどの責務で解消するかを requirement / design に落とし込む必要がある。

---

### 2026-03-31 17:20 - 17:35

#### 対象
- Step: `window-size manual` 解消策の比較整理
- AC/EC: 調査タスクのため該当なし

#### 実施内容
- 原因確定済みの `window-size manual` を前提に、解決方法の比較とベストプラクティスを独立資料へ整理した。
- 比較対象は `latest` / `smallest` / `largest` / `manual + resize-window` / 起動時のみ変更 / 毎ループ保証とした。
- 評価の結果、最有力案は「wrapper / runner が `dashboard` target の `window-size` を `latest` に明示設定し、起動時だけでなく preflight でも保証し、既存 `manual` を自動移行する」方針だと整理した。
- `smallest`、`manual + resize-window`、手動移行のみは非推奨として理由を明記した。

#### 実行コマンド / 結果
```bash
sed -n '1,260p' spec-lite/current/discussions/window-size-manual-remediation-options-20260331.md
rg -n "window-size|aggressive-resize|resize-window" -S .

# 比較資料の内容確認と repo 内の関連参照を再確認
```

#### 変更したファイル
- `spec-lite/current/discussions/window-size-manual-remediation-options-20260331.md` - 解決方法の比較とベストプラクティスを作成
- `spec-lite/current/report.md` - 今回の比較整理ログを追記

#### コミット
- 該当なし

#### メモ
- 次に仕様化する場合は、この資料を根拠に `requirement.md` / `design.md` / `plan.md` を更新する。

---

### 2026-03-31 17:35 - 17:45

#### 対象
- Step: `window-size latest` 切り替え説明資料の作成
- AC/EC: 調査タスクのため該当なし

#### 実施内容
- `window-size latest` へ具体的にどう切り替えるかを、手動手順とプロダクト実装方針に分けて説明する独立資料を作成した。
- 手動コマンドとして `tmux set-window-option -t dashboard:0 window-size latest` を明記し、確認コマンドと期待結果も整理した。
- 併せて、製品側では wrapper 起動時と runner preflight の両方で `latest` を保証するのが推奨であることを文書化した。

#### 実行コマンド / 結果
```bash
tmux set-window-option -t dashboard:0 window-size latest
tmux show-options -t dashboard:0 -w | rg '^window-size'

# 説明資料に掲載する切り替え手順と確認手順を整理
```

#### 変更したファイル
- `spec-lite/current/discussions/window-size-latest-switch-guide-20260331.md` - `latest` への切り替え方を説明する資料を新規作成
- `spec-lite/current/report.md` - 今回の資料作成ログを追記

#### コミット
- 該当なし

#### メモ
- 次に仕様化する場合は、この資料と比較資料をセットで requirement / design / plan の根拠に使える。

---

### 2026-03-31 17:45 - 18:15

#### 対象
- Step: `window-size latest` 対応の仕様更新
- AC/EC: AC-008 / EC-009 / EC-010

#### 実施内容
- `window-size manual` が resize 追随不良の根本原因であることを前提に、要件定義書・設計書・実装計画書を更新した。
- 要件定義書には `window-size latest` を `dashboard` 管理契約として追加し、`AC-008`、`EC-009`、`EC-010`、および window-local option のみ変更する非侵襲制約を追記した。
- 設計書には `get_window_option()`、`set_window_option()`、`ensure_dashboard_window_policy()` の新規 IF を定義し、wrapper 起動時と runner preflight の両方で `latest` を保証する方針を追加した。
- 実装計画書では既存の完了済み `S01` から `S05` は変更せず維持し、追加作業として `S06` を末尾に追加した。
- `S06` は TDD 前提で、window option API、wrapper/orchestrator の `latest` 保証、resize 追随 E2E と手動検証、品質ゲート / コミットに分解した。

#### 実行コマンド / 結果
```bash
sed -n '1,260p' spec-lite/current/requirement.md
sed -n '1,320p' spec-lite/current/design.md
sed -n '1,360p' spec-lite/current/plan.md

# 仕様更新後の requirement / design / plan を確認
```

#### 変更したファイル
- `spec-lite/current/requirement.md` - `window-size latest` 契約と AC-008 / EC-009 / EC-010 を追加
- `spec-lite/current/design.md` - window option API と `latest` 保証方針を追加
- `spec-lite/current/plan.md` - 完了済み S01-S05 を維持したまま S06 を追加
- `spec-lite/current/report.md` - 今回の仕様更新ログを追記

#### コミット
- 該当なし

#### メモ
- 次に実装する場合は `S06` を起点に TDD で進める。

---

### 2026-03-31 17:45 - 18:10

#### 対象
- Step: `window-size latest` 方針の仕様反映
- AC/EC: AC-008 / EC-009 / EC-010

#### 実施内容
- `window-size manual` による resize 追随不良を追加スコープとして requirement / design / plan に反映した。
- 要件定義書では `dashboard` target の `window-size latest` 管理契約、`AC-008`、`EC-009`、`EC-010`、window-local option のみ変更する非侵襲制約を追加した。
- 設計書では `get_window_option()`、`set_window_option()`、`ensure_dashboard_window_policy()` を追加 IF として定義し、wrapper 起動時と runner preflight の両方で `latest` を保証する方針を固定した。
- 実装計画書では既存の完了済み `S01` から `S05` を変更せず維持し、追加ステップ `S06` として `window-size latest` 収束、resize 追随 E2E、手動検証までを追記した。
- 初回の spec reviewer は要約のみで `pass/fail` を返さなかったため、判定を明示する reviewer へ再レビューを依頼した。

#### 実行コマンド / 結果
```bash
sed -n '1,260p' spec-lite/current/requirement.md
sed -n '1,320p' spec-lite/current/design.md
sed -n '1,360p' spec-lite/current/plan.md

# 既存仕様との整合を確認しながら AC-008 / EC-009 / EC-010 と S06 を追記
```

#### 変更したファイル
- `spec-lite/current/requirement.md` - `window-size latest` 契約と AC/EC を追加
- `spec-lite/current/design.md` - window option 管理 IF と preflight 方針を追加
- `spec-lite/current/plan.md` - 完了済み S01-S05 を維持したまま S06 を追加
- `spec-lite/current/report.md` - 今回の仕様反映ログを追記

#### コミット
- 該当なし

#### メモ
- `spec_reviewer` の `review_status` が返り次第、必要なら findings を反映して再レビューする。

---

### 2026-03-31 17:45 - 18:05

#### 対象
- Step: `window-size latest` 対応の仕様更新
- AC/EC: AC-008 / EC-009 / EC-010

#### 実施内容
- `window-size manual` による resize 追随不良への追加対応として、`requirement.md` / `design.md` / `plan.md` を更新した。
- 要件定義では `window-size latest` の管理契約、自動回復、dashboard window-local option 限定の非侵襲制約、AC-008 と EC-009/EC-010 を追加した。
- 設計書では `get_window_option()` / `set_window_option()` / `ensure_dashboard_window_policy()` を新規 IF として定義し、wrapper 起動時と runner preflight の両方で `latest` を保証する方針を固定した。
- 実装計画書では既存の完了済み S01-S05 を保持したまま、新規作業として S06 を追加し、TDD の Red → Green → Refactor で進められる作業ブロックへ分解した。
- spec reviewer へ requirement / design / plan の整合レビューを依頼した。

#### 実行コマンド / 結果
```bash
sed -n '1,260p' spec-lite/current/requirement.md
sed -n '1,320p' spec-lite/current/design.md
sed -n '1,360p' spec-lite/current/plan.md

# `window-size latest` 対応の差分を確認し、spec review を依頼
```

#### 変更したファイル
- `spec-lite/current/requirement.md` - AC-008 / EC-009 / EC-010 と `window-size latest` 管理契約を追加
- `spec-lite/current/design.md` - window option API、preflight 保証、`latest` 方針を追加
- `spec-lite/current/plan.md` - 完了済み S01-S05 を保持したまま S06 を追加
- `spec-lite/current/report.md` - 今回の仕様更新ログを追記

#### コミット
- 該当なし

#### メモ
- spec review の findings に応じて requirement / design / plan を是正する。

---

### 2026-03-31 17:20 - 17:35

#### 対象
- Step: 解決策比較とベストプラクティス整理
- AC/EC: 調査タスクのため該当なし

#### 実施内容
- `window-size manual` を根本原因としたうえで、解決策候補を比較した。
- 比較対象は `latest` / `smallest` / `largest` / `manual + resize-window` / 起動時のみ / 毎ループ保証 / 既存 manual session の移行戦略とした。
- 比較結果として、`dashboard` target の `window-size` を `latest` に明示し、起動時だけでなく preflight でも保証し、既存 `manual` を自動移行する案を推奨と整理した。
- 検討結果を独立資料 `spec-lite/current/discussions/window-size-manual-remediation-options-20260331.md` に作成した。

#### 実行コマンド / 結果
```bash
sed -n '1,260p' spec-lite/current/discussions/resize-follow-up-analysis-20260331.md

# 根本原因レポートを参照し、比較資料を起草
```

#### 変更したファイル
- `spec-lite/current/discussions/window-size-manual-remediation-options-20260331.md` - 解決策比較とベストプラクティスを新規作成
- `spec-lite/current/report.md` - 今回の比較整理ログを追記

#### コミット
- 該当なし

#### メモ
- 次の設計更新では、「dashboard window の window-size policy はツールが `latest` に維持する」を requirement / design 契約へ昇格させるのが自然。

tmux -L "$sock" new-session -d -s dashboard -n dashboard
tmux -L "$sock" new-window -d -P -F '#{session_name}:#{window_index}' -t dashboard
# status=1
# out=create window failed: index 0 in use

tmux -L "$sock" new-session -d -s dashboard
tmux -L "$sock" new-window -d -P -F '#{session_name}:#{window_index}' -t dashboard
# status=0
# out=dashboard:1
```

#### 変更したファイル
- `spec-lite/current/discussions/wrapper-create-window-root-cause-20260331.md` - wrapper 経路の一次原因と再現条件を整理した調査レポート
- `spec-lite/current/report.md` - 本調査ログを追記

#### コミット
- 該当なし

#### メモ
- 既存の direct runner E2E は `tmux new-session -d -s dashboard` を使っており、window 名が既定の `zsh` のため wrapper 固有の同名条件を再現していなかった。

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

### 2026-03-31 00:30 - 01:10

#### 対象
- Step: wrapper 根本原因反映の spec 更新
- AC/EC: AC-002, AC-004, AC-005, AC-006 / EC-001, EC-005, EC-006, EC-007

#### 実施内容
- wrapper 経路の調査結果を反映し、`requirement.md` に wrapper 回帰、`create_window()` の fail-closed 契約、cleanup warning と residual retry の受け入れ条件を追加した。
- `design.md` には `IF-006` / `IF-007` / `IF-008`、0 セッション時の 1 pane 収束、swap failure と cleanup warning の分離、log contract、residual window retry を明文化した。
- `plan.md` は既存の完了済み S01-S03 を維持したまま、追加作業として S04 を定義し、`create_window` 修正、swap failure、cleanup retry、CLI exit 0 / log 契約まで含む TDD イテレーションへ分解した。
- spec review を requirement/design → plan の順で実施し、fail を複数回是正したのち、最終的に requirement/design は `pass`、plan も `pass` を確認した。

#### 実行コマンド / 結果
```bash
# spec review cycles
spec_reviewer (requirement/design)
# fail -> zero-session branch, staging identifier contract, failure observability, swap cleanup semantics を是正

spec_reviewer (requirement/design re-review)
# fail -> cleanup-warning contract を LayoutApplyResult / test strategy に反映

spec_reviewer (requirement/design re-review)
# pass (non-blocking: residual retry を acceptance/test へ閉じるとさらに良い)

spec_reviewer (plan)
# fail -> swap failure の専用 Red/Green と CLI exit 0 / log 契約の TDD 追加が必要

spec_reviewer (plan re-review)
# pass
```

#### 変更したファイル
- `spec-lite/current/requirement.md` - wrapper same-name 条件、`create_window` fail-closed、cleanup warning / residual retry の受け入れ条件を追加
- `spec-lite/current/design.md` - IF 契約、0 セッション分岐、swap failure / cleanup warning / residual retry / log contract を追加
- `spec-lite/current/plan.md` - S04 を追加し、swap failure / CLI observability / residual retry を含む TDD 計画へ更新
- `spec-lite/current/report.md` - 本レビューサイクルと判断を追記

#### コミット
- このログ記録時点では未実施

#### メモ
- requirement/design は final review で `pass`、plan も final review で `pass`。
- 実装は未着手で、次の工程は S04 の TDD 実装開始。

---

### 2026-03-31 08:20 - 08:28

#### 対象
- Step: S04
- AC/EC: AC-005, AC-006 / EC-005, EC-006, EC-007

#### 実施内容
- `tmuxio.py` の CLI / libtmux 両経路で `create_window()` が `session_name:window_index` を `new-window -t` にそのまま渡すよう修正した。
- `create_window()` に作成後 `list-panes` による実在確認を追加し、CLI/libtmux とも phantom target を返さず fail-closed で例外化するようにした。
- libtmux 側は `returncode` / `stderr` 異常も検出して例外化するよう修正し、size 指定時の `resize-window` 挙動は維持した。
- `orchestrator.py` は create failure / layout apply failure / swap failure を分離して `ERROR` ログ化し、swap 後 cleanup failure は `WARNING` と residual window retry へ分離した。
- residual window target を次サイクル冒頭で best-effort cleanup retry する状態管理を追加し、retry 成否にかかわらず新規 staging 試行を継続できるようにした。
- `tests/test_tmuxio.py`, `tests/test_orchestrator.py`, `tests/test_cli_entry.py`, `tests/test_e2e_tmux.py` を TDD で更新し、same-name 条件・fail-closed・create/swap failure observability・residual cleanup retry・CLI exit 0 を固定した。

#### 実行コマンド / 結果
```bash
uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_cli_entry.py -q
# 33 passed in 0.10s

uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_e2e_tmux.py tests/test_cli_entry.py -q
# 40 passed in 1.91s

uv run pytest -q
# 94 passed in 1.79s
```

#### 変更したファイル
- `tmux_dashboard/tmuxio.py` - `create_window()` の exact target / fail-closed / 実在確認を実装
- `tmux_dashboard/orchestrator.py` - create/swap failure の明示ログ、cleanup warning、residual cleanup retry を実装
- `tests/test_tmuxio.py` - CLI / libtmux の create_window exact target / fail-closed テストを追加
- `tests/test_orchestrator.py` - create failure / swap failure / residual cleanup retry の回帰テストを追加
- `tests/test_cli_entry.py` - create/swap failure 時の exit 0 / logging テストを追加
- `tests/test_e2e_tmux.py` - session/window same-name 条件の E2E 回帰を追加
- `spec-lite/current/plan.md` - S04 完了状態へ更新
- `spec-lite/current/report.md` - S04 実装ログを追記

#### コミット
- 未実施（ユーザーレビュー待ち）

#### メモ
- wrapper の visible window 名 `dashboard` は変更していない。
- CLI / 通常ループとも個別サイクル failure で exit 0 を維持する方針は現行のまま、明示ログを強化した。

---

### 2026-03-31 08:30 - 08:38

#### 対象
- Step: S04 follow-up review findings
- AC/EC: AC-005, AC-006 / EC-005, EC-006, EC-007

#### 実施内容
- `tests/test_orchestrator.py` に residual cleanup retry の再失敗 branch を追加し、warning を出しつつ別 index の staging window で再レイアウト継続することを固定した。
- `tmux_dashboard/orchestrator.py` は residual retry が失敗したまま後続 staging cleanup が成功しても、未解消の residual target を消さないよう補正した。
- `tests/test_cli_entry.py` に `run_once()` が内部で explicit failure をログして正常 return する経路の coverage を追加し、CLI exit 0 と failure detail の観測可能性を確認した。
- `tests/test_e2e_tmux.py` に actual wrapper path (`./tmux-dashboard`) を起動する回帰テストを追加し、visible dashboard window と runner window が作成され、`dashboard:0` に複数 pane / titles が得られることを検証した。
- `spec-lite/current/plan.md` は S04 スコープ説明を actual wrapper path / residual retry failure branch まで含む表現へ更新した。

#### 実行コマンド / 結果
```bash
uv run pytest tests/test_orchestrator.py tests/test_cli_entry.py tests/test_e2e_tmux.py -q
# 29 passed in 1.83s

uv run pytest -q
# 97 passed in 2.11s
```

#### 変更したファイル
- `tmux_dashboard/orchestrator.py` - residual retry failure 後も既存 residual target を保持するよう補正
- `tests/test_orchestrator.py` - residual cleanup retry failure branch の回帰テストを追加
- `tests/test_cli_entry.py` - run_once がログして正常 return する CLI observability テストを追加
- `tests/test_e2e_tmux.py` - actual wrapper path regression test を追加
- `spec-lite/current/plan.md` - S04 follow-up coverage を反映
- `spec-lite/current/report.md` - follow-up review findings 対応ログを追記

#### コミット
- 未実施（ユーザーレビュー待ち）

#### メモ
- actual wrapper path test は detached control session 内から `./tmux-dashboard` を起動する方式で実装した。
- wrapper 最終段の `switch-client` 成否には依存せず、runner window 起動後の dashboard state を観測する。

---

### 2026-03-31 08:40 - 08:46

#### 対象
- Step: S04 follow-up review findings (追加)
- AC/EC: AC-006 / EC-006, EC-007

#### 実施内容
- `orchestrator.py` の residual 管理を単一 target から FIFO 的な pending list へ拡張し、古い residual を優先して retry しつつ、新しい cleanup failure も失わないよう補正した。
- create-window failure が post-create verification / resize failure のような部分失敗でも、予測済み `staging_target` を best-effort cleanup するよう `run_once()` を補強した。
- `tests/test_orchestrator.py` に partial create failure cleanup テストと、古い residual を保持したまま新しい residual も後続 retry 対象として保持するテストを追加した。

#### 実行コマンド / 結果
```bash
uv run pytest tests/test_orchestrator.py tests/test_cli_entry.py tests/test_e2e_tmux.py -q
# 31 passed in 1.85s

uv run pytest -q
# 99 passed in 2.02s
```

#### 変更したファイル
- `tmux_dashboard/orchestrator.py` - partial-create cleanup と複数 residual pending 管理を補強
- `tests/test_orchestrator.py` - partial create failure / multi-residual preservation の回帰テストを追加
- `spec-lite/current/plan.md` - S04 スコープ表現を補足
- `spec-lite/current/report.md` - 追加 findings 対応ログを追記

#### コミット
- 未実施（ユーザーレビュー待ち）

#### メモ
- 後方互換のため、`_residual_window_target` は最古 pending residual を返す property として維持した。

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

---

## 2026-03-31 受け入れ検査

### 概要
- 実装担当者が完了させた `69dec89 fix(tmux): wrapper経路のcreate-window失敗をfail-closedにする` を対象に、Git 差分確認、コードレビュー、`uv run pytest -q`、手動テストによる受け入れ検査を実施した。
- 検査の独立レポートは `spec-lite/current/discussions/acceptance-review-wrapper-fix-20260331.md` に記録した。

### 結果
- 自動テスト: `100 passed`
- code review: `fail`
- 受け入れ判定: `fail`

### 主な理由
- `tmux_dashboard/tmuxio.py` の `LibtmuxDriver.swap_window()` / `kill_window()` が tmux command failure を例外化しておらず、fail-closed 契約が default driver で崩れる。
- `tmux_dashboard/orchestrator.py` の create failure path が、存在しない staging target を residual cleanup queue に積みうる。
- 手動テストで、0 セッション収束後に `dashboard:0` の pane title が古い session 名のまま残る観測を確認した。

### 次アクション
- 上記 3 点を追加修正スコープとして requirement / design / plan に反映するか、既存 S04 の追補として次の実装修正に進む。

---

## 2026-03-31 追加仕様整備

### 概要
- 受け入れ検査で fail となった 3 点に対する解決方針を docs に反映した。
- 独立資料として `spec-lite/current/discussions/wrapper-fix-best-practices-20260331.md` を作成した。
- `requirement.md`, `design.md`, `plan.md` を更新し、追加修正ステップ `S05` を定義した。

### 更新内容
- `spec-lite/current/requirement.md`
  - `swap-window` / `kill-window` fail-closed
  - ghost residual target 防止
  - 0 セッション stale title 解消
  - AC-007 / EC-008 追記
- `spec-lite/current/design.md`
  - IF-006a / IF-006b の契約固定
  - 0 セッション title クリアと ghost residual 回避フロー追加
  - mapping / test trace を受け入れ findings に合わせて補強
- `spec-lite/current/plan.md`
  - 既存 S01-S04 は完了済みのまま保持
  - 追加修正ステップ S05 を定義
  - acceptance 再判定を S05 と plan DoD に組み込んだ

### レビュー結果
- requirement + design:
  - `spec_reviewer`: `pass`
  - 非 blocking 指摘: 設計内のトレーサビリティ表現を一部補強済み
- plan:
  - `spec_reviewer`: `pass`
  - 非 blocking 指摘: CLI entrypoint 回帰の必須証跡を S04/S05 で統一する件を反映済み

---

## 2026-03-31 S05 最終受け入れ

### 概要
- 実装担当者の S05 修正完了後、最終受け入れ検査を再実施した。
- 正本レポートは `spec-lite/current/discussions/acceptance-review-wrapper-fix-20260331-final.md`。

### 実行コマンド / 結果
```bash
uv run pytest -q
# 104 passed in 4.95s
```

### 手動検証要点
- direct runner same-name 条件で `dashboard:0` が 3 pane に復旧した
- wrapper 経路で全対象セッション削除後、`dashboard:0` が `1 pane + empty title` に収束した

### レビュー
- `qa_reviewer`: `pass`
- main-agent 差分レビュー: blocking issue なし

### 判定
- 最終受け入れ: `pass`

---

## 2026-03-31 リサイズ追随不良の追加調査

### 概要
- ユーザーから「ローカルでは幅変更に追随しない」との報告を受け、追加調査を開始した。
- `spec-lite/current/discussions/resize-follow-up-analysis-20260331.md` に分析レポートを作成した。

### わかったこと
- repo 現行コードでは、direct runner / wrapper の両方で `resize-window` に対するレイアウト追随を再現できた。
- 一方で `scan_sessions()` は attached / detached を区別せず、`dashboard` 以外の全 session を pane 対象として数えている。
- このため、ローカルに detached session が多く残っていると「幅監視不良」ではなく「対象数過多」によって見え方が悪化している可能性が高い。

### 次の観測候補
- `tmux list-sessions -F '#{session_name}|#{session_attached}|#{session_windows}'`
- `which tmux-dashboard`
- runner pane の `ps` 出力

### 追加で確定したこと
- ユーザー実機の `tmux list-sessions` と `tmux list-panes -t dashboard:0` により、pane title がそのまま sandbox 系 session 名になっていることを確認した。
- このため、少なくとも今回の主因は「幅監視不良」より「session 選定が広すぎる」可能性が高い。
- さらに `configs/dashboard.yaml` の `min_tile_width: 65` を確認した。幅 `191` で 3 session の場合、列数は `floor(191 / 65) = 2` となり、ユーザー実機の `95|95` 幅観測と一致する。

---

## 2026-03-31 S05 実装

### 概要
- 受け入れ検査で fail となっていた 3 findings を S05 スコープ内で解消した。
- `swap-window` / `kill-window` の default driver fail-closed、create failure 時の ghost residual queue 防止、0 セッション収束時の stale title クリアを TDD で実装した。
- failure path を触った後も、CLI `main()` の `--once` / 通常ループの exit 0 と explicit logging 契約が既存回帰テストで維持されることを再確認した。

### 実施内容
- `tmux_dashboard/tmuxio.py`
  - `LibtmuxDriver.swap_window()` / `kill_window()` に `_raise_if_cmd_failed()` を適用し、tmux command failure を silent success にしないよう補完した。
- `tmux_dashboard/orchestrator.py`
  - create failure path に staging target 実在確認 helper を追加し、未作成 target では cleanup / residual enqueue を行わないよう補正した。
  - 0 セッション short-circuit 後に残る単一 pane の title を空文字へ戻す helper を追加した。
- `tests/test_tmuxio.py`
  - libtmux `swap_window()` / `kill_window()` の fail-closed 回帰テストを追加した。
- `tests/test_orchestrator.py`
  - missing staging target を cleanup / residual retry 対象にしない回帰へ更新した。
  - 0 セッション short-circuit 後の stale title 解消テストを追加した。
- `tests/test_e2e_tmux.py`
  - 実 tmux 上で、全対象セッション削除後に `dashboard:0` が 1 pane かつ空 title へ収束する E2E を追加した。
- `tests/test_cli_entry.py`
  - 既存の create/swap failure 時 exit 0 / explicit logging 回帰を再実行し、契約維持を確認した（追加修正なし）。
- `spec-lite/current/plan.md`
  - S05 完了として進捗と品質ゲートを更新した。

### 実行コマンド / 結果
```bash
uv run pytest tests/test_tmuxio.py -q
# 15 passed in 0.03s

uv run pytest tests/test_orchestrator.py -q
# 17 passed in 0.07s

uv run pytest tests/test_orchestrator.py tests/test_e2e_tmux.py -q
# 27 passed in 1.92s

uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_e2e_tmux.py tests/test_cli_entry.py -q
# 49 passed in 2.20s

uv run pytest -q
# 103 passed in 2.12s
```

### 変更したファイル
- `tmux_dashboard/tmuxio.py` - libtmux `swap-window` / `kill-window` を fail-closed 化
- `tmux_dashboard/orchestrator.py` - missing staging target の ghost residual 防止、0 セッション title クリア
- `tests/test_tmuxio.py` - libtmux lifecycle failure の回帰テストを追加
- `tests/test_orchestrator.py` - create failure / zero-session title 収束の回帰を追加
- `tests/test_e2e_tmux.py` - zero-session stale title の E2E 回帰を追加
- `spec-lite/current/plan.md` - S05 完了へ更新
- `spec-lite/current/report.md` - S05 実装ログを追記

### 判断
- `acceptance-review-wrapper-fix-20260331.md` で指摘された 3 findings に対して、S05 の自動回帰で closed 相当の証跡を追加できた。
- wrapper の visible window 名、attach/TTY 振る舞い、CLI の exit code 方針は変更していない。

### コミット
- 未実施（ユーザーがレビュー / コミットを担当するため）

---

## 2026-03-31 S06 実装（window-size latest 自動回復）

### 概要
- `window-size manual` 汚染により outer Terminal resize へ追随しない問題に対して、S06 を実装した。
- `dashboard` target の window-local option を `latest` に収束させる API / preflight を追加し、wrapper / runner 両経路で自動回復を実装した。
- review findings に対応し、orchestrator 側の policy 是正は `dashboard:` target のみに限定した（non-dashboard 非侵襲）。

### 実施内容
- `tmux_dashboard/tmuxio.py`
  - `CliDriver` / `LibtmuxDriver` に `get_window_option()` を追加した。
  - `TmuxIO` に `get_window_option()` 委譲 API を追加した。
  - `show-options -w` が空出力のケースに対して `show-options -w -g -v` を fallback し、`window-size` の有効値を取得できるようにした。
  - libtmux 経路は fail-closed（`_raise_if_cmd_failed`）を維持した。
- `tmux_dashboard/orchestrator.py`
  - `ensure_dashboard_window_policy(window_target)` を追加した。
  - `run_once()` preflight と cycle end で `window-size latest` を保証するようにした。
  - review finding 対応として、`window_target.startswith(\"dashboard:\")` の場合のみ policy 是正するガードを追加した。
- `tmux-dashboard`
  - visible dashboard window 確定後に `tmux set-option -w -t \"$dashboard_window_target\" window-size latest` を実行する preflight を追加した。

### テスト（Red → Green）
- 追加/更新:
  - `tests/test_tmuxio.py`
    - CLI/libtmux の `get_window_option` / `set_window_option` 契約
    - libtmux get の fail-closed
  - `tests/test_orchestrator.py`
    - `window-size manual` を `latest` へ是正する回帰
    - non-dashboard target では `window-size` の get/set を呼ばない非侵襲回帰
  - `tests/test_e2e_tmux.py`
    - direct runner の manual → latest 自動回復
    - wrapper の manual → latest 自動回復 + resize 追随

### 実行コマンド / 結果
```bash
uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_e2e_tmux.py -q
# 50 passed in 4.54s

uv run pytest -q
# 111 passed in 4.46s
```

### 手動検証
- 独立レポート:
  - `spec-lite/current/discussions/window-size-latest-manual-validation-20260331.md`
- 追記内容:
  - direct runner / wrapper の manual → latest 回復
  - resize 79 / 191 の追随
  - EC-010 補強として multi-client 観測（`tmux list-clients -t dashboard`）を追加

### review findings への対応
- Code review (Major): `ensure_dashboard_window_policy()` の強制対象を `dashboard:` に限定
  - 対応: `tmux_dashboard/orchestrator.py` に target ガードを追加
  - 回帰: `tests/test_orchestrator.py::test_ensure_dashboard_window_policy_is_non_intrusive_for_non_dashboard_target`
- QA (High/Medium): multi-client 条件の説明力不足
  - 対応: 手動検証レポートへ `tmux list-clients -t dashboard` 観測を追加し、EC-010 の根拠を明記
  - 自動担保: wrapper/direct の latest 収束 + resize 追随 E2E を維持

### 変更したファイル
- `tmux_dashboard/tmuxio.py`
- `tmux_dashboard/orchestrator.py`
- `tmux-dashboard`
- `tests/test_tmuxio.py`
- `tests/test_orchestrator.py`
- `tests/test_e2e_tmux.py`
- `spec-lite/current/discussions/window-size-latest-manual-validation-20260331.md`
- `spec-lite/current/report.md`
- `spec-lite/current/plan.md`

### コミット
- 未実施（ユーザーがレビュー / コミットを担当するため）

### QA follow-up
- QA reviewer から「`resize-window` 直接操作では outer Terminal resize の証明として弱い」「EC-010 の修正後 multi-client 証跡が足りない」という指摘を受けた。
- 対応として control-mode client を 2 つ attach し、`refresh-client -C` で client 側サイズを更新したときに `dashboard:0` の `window_width` が `79x40` → `191x98` へ追随する手動証跡を追加した。
- 追加証跡は `spec-lite/current/discussions/window-size-latest-manual-validation-20260331.md` のシナリオ 4 に記録した。

## 2026-03-31 S05 follow-up（spec review findings 対応）

### 概要
- spec review の pass-with-findings に対応し、S05 の acceptance trail を監査可能な形で補完した。
- 既存の direct runner zero-session E2E に加えて、wrapper path での zero-session title cleanup regression を追加した。

### 実施内容
- `tests/test_e2e_tmux.py`
  - `./tmux-dashboard` 起動後に全対象セッションを削除し、`dashboard:0` が `1 pane + empty title` へ収束する wrapper path E2E を追加した。
- `spec-lite/current/discussions/acceptance-review-wrapper-fix-20260331-s05-rereview.md`
  - 既存受け入れレポートを supersede する S05 再判定レコードを追加し、3 findings が closed / 判定 pass になったことを明示した。
- `spec-lite/current/plan.md`
  - S05 完了の follow-up と authoritative acceptance artifact を追記した。

### 実行コマンド / 結果
```bash
uv run pytest tests/test_e2e_tmux.py -q
# 10 passed in 4.51s

uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_e2e_tmux.py tests/test_cli_entry.py -q
# 50 passed in 4.88s

uv run pytest -q
# 104 passed in 4.79s
```

### 変更したファイル
- `tests/test_e2e_tmux.py` - wrapper path zero-session stale title regression を追加
- `spec-lite/current/discussions/acceptance-review-wrapper-fix-20260331-s05-rereview.md` - S05 再判定の authoritative acceptance artifact を追加
- `spec-lite/current/plan.md` - S05 follow-up と acceptance artifact を同期
- `spec-lite/current/report.md` - follow-up 実施ログを追記

### 判断
- authoritative acceptance verdict は追加した再判定 artifact により `pass` として記録された。
- wrapper path の zero-session title cleanup も direct runner と同様に自動検証できる状態になった。

### コミット
- 未実施（ユーザーがレビュー / コミットを担当するため）

## 省略/例外メモ (必須)
- 該当なし

---

## 2026-03-31 live wrapper 表示不良の現物調査

### 概要
- ユーザー実機で `dashboard`, `hoge`, `kkk` session が存在する状態で `./tmux-dashboard` が正しく表示されない件を現物調査した。
- 結果として、表示不良は「レイアウト不良」単体ではなく、「依存欠落で新しい runner が起動できない状態」と「古い runner が残留して dashboard を再適用し続ける状態」の複合障害だった。

### 実施内容
- `tmux list-windows` / `tmux list-panes` で、`dashboard:0` が plain shell 1 pane のままであることを確認した。
- `./tmux-dashboard` を direct に実行し、非 TTY では `open terminal failed: not a terminal` で終わる一方、その前段で runner 起動処理までは進んでいることを確認した。
- `uv run --no-sync python -m tmux_dashboard --window-target dashboard:0 --once --iterations 1` を直接実行し、`ModuleNotFoundError: No module named 'yaml'` で新しい runner が即死していることを確認した。
- `uv sync --locked` で依存を同期し、direct runner が `hoge`, `kkk` を検出して renderer を spawn できるところまで復旧させた。
- `ps` と `tmux-dashboard.log` を確認し、別系統の古い常駐 runner が `alpha`, `beta`, `gamma` を継続適用しており、新しい表示を直後に上書きしていることを確認した。
- 調査結果を `spec-lite/current/discussions/live-wrapper-misdisplay-analysis-20260331.md` に整理した。

### 実行コマンド / 結果
```bash
tmux list-windows -t dashboard -F '#{window_index}|#{window_name}|#{window_active}|#{window_width}x#{window_height}'
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_width}x#{pane_height}|#{pane_current_command}'
cd /srv/mount/tmux-dashboard && ./tmux-dashboard
cd /srv/mount/tmux-dashboard && uv run --no-sync python -m tmux_dashboard --window-target dashboard:0 --once --iterations 1
cd /srv/mount/tmux-dashboard && uv sync --locked
ps -ef | rg 'tmux_dashboard|uv run --no-sync python -m tmux_dashboard'
tail -n 200 ~/.local/state/tmux-dashboard/tmux-dashboard.log

# 主要結果:
# - 初回 direct runner は ModuleNotFoundError: yaml
# - uv sync 後は direct runner 起動成功
# - ただし 17:29 開始の古い常駐 runner が alpha/beta/gamma を再適用し続けていた
```

### 変更したファイル
- `spec-lite/current/discussions/live-wrapper-misdisplay-analysis-20260331.md`
- `spec-lite/current/report.md`

### コミット
- 該当なし

### 判断
- いまの実機障害の主因は、最新のレイアウト修正そのものではない。
- 一次原因は依存同期崩れ、二次原因は stale runner 干渉である。
- 今後の修正論点は「critical import preflight」と「同一 target 管理 runner の重複検知」に整理できる。

### 追加証跡
```bash
ps -ef | grep 'tmux_dashboard --window-target dashboard:0' | grep -v grep
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_width}x#{pane_height}|#{pane_current_command}'
cd /srv/mount/tmux-dashboard && uv run --no-sync python -c 'import yaml'

# ユーザー実機結果:
# - 17:29 開始の stale runner が 1 系統残存
# - dashboard:0 はなお plain shell 1 pane
# - その後 stale runner は消えたが、yaml import は依然失敗
# - `uv sync --locked` の Checked だけでは broken `.venv` が直っていない
```

### 復旧実施
```bash
cd /srv/mount/tmux-dashboard
rm -rf .venv
uv sync --locked
uv run --no-sync python -c 'import yaml; print("ok")'
uv run --no-sync python -m tmux_dashboard --window-target dashboard:0 --once --iterations 1
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_width}x#{pane_height}|#{pane_current_command}'
tmux list-sessions -F '#{session_name}|#{session_windows}|#{session_attached}'

# 結果:
# - yaml import は ok
# - direct runner は 0 で完走
# - dashboard:0 は shell から dashboard 表示へ遷移
# - 最終状態は 0|hhh|122x4|python3
# - 非 dashboard session はこの時点で hhh のみ
```

---

## 2026-04-01 local runtime hardening 実装

### 概要
- ローカル環境で `uv` cache / `.venv` 崩壊により wrapper が runner を即死させる問題に対し、runtime hardening を実装した。
- 方針は「runtime で `uv` を使わない」「`.venv` import health を attach 前に fail-fast」「runner pane の即死を明示診断する」の 3 点に固定した。

### 実施内容
- `tmux-dashboard` wrapper を `uv run --no-sync ...` から `.venv/bin/python -m tmux_dashboard ...` 起動へ変更した。
- wrapper 起動前に `import yaml, libtmux, tmux_dashboard` を実行し、broken `.venv` なら attach 前に停止して修復手順を出すようにした。
- runner window を空で作成してから `respawn-pane` で起動する方式へ変え、`remain-on-exit on` と短い grace period 後の `pane_dead` 確認で bootstrap failure を検出できるようにした。
- `Makefile` の `doctor` に `.venv` import health check を追加し、存在だけでなく runtime 健全性を判定するようにした。
- `README.md` に runtime が `.venv/bin/python` 前提であること、`UV_CACHE_DIR` を使った復旧手順、`broken virtualenv` / `runner bootstrap failed before attach` の対処を追加した。
- wrapper 用の subprocess テスト `tests/test_wrapper_runtime.py` を追加し、broken `.venv` の fail-fast、runner 即死検知、正常起動を固定した。

### 実行コマンド / 結果
```bash
bash -n tmux-dashboard
.venv/bin/python -m pytest tests/test_wrapper_runtime.py tests/test_wrapper_help.py -q
make doctor
.venv/bin/python -m pytest tests/test_e2e_tmux.py -q -k 'wrapper_path_builds_layout_and_runner_window or wrapper_path_zero_sessions_clear_stale_title or wrapper_recovers_manual_and_follows_resize'

# 結果:
# - shell syntax check は成功
# - wrapper 関連テストは 4 passed
# - make doctor は runtime import health を含めて All checks passed.
# - wrapper E2E 3 件はこの環境で skip（tmux usable 判定により未実行）
```

### 変更したファイル
- `tmux-dashboard`
- `Makefile`
- `README.md`
- `tests/test_wrapper_runtime.py`
- `spec-lite/current/report.md`

### コミット
- 未実施（ユーザーがレビュー / コミットを担当するため）

### 判断
- ベストプラクティスは「setup に `uv`、runtime に `.venv/bin/python`」である。
- runtime で `uv` cache や editable 解決に再依存すると、ローカル固有 cache path / 権限差分を毎回踏むため不安定になる。
- broken `.venv` は attach 後ではなく attach 前に止める方が障害切り分けコストを最小化できる。
