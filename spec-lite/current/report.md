---
種別: 実装報告書
機能ID: "dashboard-input-proxy"
機能名: "dashboard 選択ペイン入力プロキシ分析"
関連Issue: ["N/A"]
状態: "draft"
作成者: "Codex"
最終更新: "2026-04-01"
依存: ["requirement.md", "design.md", "plan.md"]
---

# dashboard-input-proxy dashboard 選択ペイン入力プロキシ分析 — 実装報告（LOG）

## 実装サマリー (任意)
- このセッションではコード変更は行わず、`tmux-dashboard` の現状実装、過去の障害履歴、テスト、wrapper の挙動を調査して、選択 tile に限定した入力プロキシ方式の技術比較と推奨案を spec-lite 文書へ整理した。
- 結論は、attach 主方式へ戻さず、viewer 構造を維持したまま tile-target binding と `send-keys` / `paste-buffer` ベースの control-plane を導入する案を best practice とすることである。

## 実装記録（セッションログ） (必須)

### 2026-04-01 00:00 - 00:45

#### 対象
- Step: 分析タスク（実装前調査）
- AC/EC: AC-001, AC-002, AC-003, EC-001, EC-002

#### 実施内容
- リポジトリ全体と `spec-lite/current` / `spec-lite/completed` を確認し、現状の spec-lite 正本がテンプレートのままであることを確認した。
- `tmux_dashboard/orchestrator.py`, `tmux_dashboard/tmuxio.py`, `tmux_dashboard/tile.py`, `tmux-dashboard`, `README.md`, 関連テストを調査した。
- repo_analyst に影響範囲と責務分離を、consultant に方式比較と best practice 判断を依頼し、結果を統合した。
- `spec-lite/current/requirement.md`, `design.md`, `plan.md`, `report.md` と discussion シートを作成する方針を確定した。

#### 実行コマンド / 結果
```bash
rg --files
sed -n '1,260p' tmux_dashboard/orchestrator.py
sed -n '1,320p' tmux_dashboard/tmuxio.py
sed -n '1,220p' tmux_dashboard/tile.py
sed -n '1,260p' README.md
sed -n '1,260p' tests/test_e2e_tmux.py
sed -n '1,240p' tests/test_wrapper_runtime.py
git status --short

# 結果要約
# - 各 tile は capture-only viewer
# - 入力 API / binding 正本は未実装
# - attach / switch-client は既知の不安定面あり
# - worktree は clean
```

#### 変更したファイル
- `spec-lite/current/requirement.md` - 分析要件を追加
- `spec-lite/current/design.md` - 候補方式比較と推奨設計を追加
- `spec-lite/current/plan.md` - 将来実装の段階導入計画を追加
- `spec-lite/current/report.md` - 本調査ログを追加
- `spec-lite/current/discussions/dashboard-input-proxy-analysis.md` - 比較表と PlantUML を含む提案資料を追加

#### コミット
- なし（分析タスクのみ。ユーザーから commit 指示なし）

#### メモ
- 現状の dashboard は「参照専用であること」が実装構造そのものになっている。
- そのため入力可能化は「ビューアをやめる」より「制御プレーンを足す」方向が自然。

---

## 遭遇した問題と解決 (任意)
- 問題: `spec-lite/current` がテンプレートのままで、今回の分析正本が存在しなかった
  - 解決: 本タスク向けに要件・設計・計画・報告・discussion を新規に作成した

## 学んだこと (任意)
- `tmux-dashboard` は tile を元ペインへ attach しているのではなく、`respawn-pane` された viewer process である
- attach / switch-client の障害履歴を踏まえると、control-plane の追加が最も自然な進化経路である

## 今後の推奨事項 (任意)
- 実装に入るなら、まず S01 / S02 の binding 正本化と単発送信 CLI から始める
- `--selected` 自動解決は複数 client 問題があるため、初期は `--tile-pane` 明示指定を正本にする

## 省略/例外メモ (必須)
- 今回は分析と提案のみで、テスト実行やコード変更は行っていない
