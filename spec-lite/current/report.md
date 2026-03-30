---
種別: 実装報告書
機能ID: "migration-spec-lite"
機能名: "planning から spec-lite への移行"
関連Issue: ["調査レポート起点の運用移行"]
状態: "draft"
作成者: "codex"
最終更新: "2026-03-30"
依存: ["requirement.md", "design.md", "plan.md"]
---

# migration-spec-lite planning から spec-lite への移行 — 実装報告（LOG）

## 実装サマリー (任意)
- 旧 `planning/` ベースの運用から `spec-lite/` ベース運用へ移行するため、今回の調査レポートを `spec-lite/current/discussions/` に作成した。
- 以後の作業記録は `spec-lite/current/report.md` を正本とし、旧 `planning/` の成果物は `spec-lite/completed/` へアーカイブして退役させる。

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

## 遭遇した問題と解決 (任意)
- 問題: ...
  - 解決: ...

## 学んだこと (任意)
- ...
- ...

## 今後の推奨事項 (任意)
- ...
- ...

## 省略/例外メモ (必須)
- 該当なし
