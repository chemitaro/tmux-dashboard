---
種別: 要件定義書
機能ID: "dashboard-input-proxy"
機能名: "dashboard 選択ペイン入力プロキシ分析"
関連Issue: ["N/A"]
状態: "draft"
作成者: "Codex"
最終更新: "2026-04-01"
---

# dashboard-input-proxy dashboard 選択ペイン入力プロキシ分析 — 要件定義（WHAT / WHY）

## 目的（ユーザーに見える成果 / To-Be） (必須)
- `tmux-dashboard` の現状を完全に把握したうえで、「参照専用ダッシュボード」を維持しつつ、選択したタイルに対応する元ペインへだけ安全に入力できる実現方式を比較し、最も実施可能で優れた方式を提案できるようにする。
- 提案内容を Markdown の分析シートとして構造化し、今後の実装判断の正本にする。

## 背景・現状（As-Is / 調査メモ） (必須)
- 現状の挙動（事実）:
  - ダッシュボード各タイルは元ペインの live attach ではなく、`capture-pane` を周期取得して再描画する viewer である。
  - `Orchestrator.run_once()` は各 tile pane を `respawn-pane` で `python -m tmux_dashboard.tile` に置き換える。
  - `tile.py` は read-only renderer であり、標準入力を読まず、画面クリアと再描画のみを繰り返す。
  - `tmuxio` には `send-keys` や pane user option 管理の公開契約がなく、入力ルーティングの仕組みは存在しない。
  - wrapper は dashboard window と runner window を維持し、過去に attach / switch-client / multi-client window-size 問題が観測されている。
- 現状の課題（困っていること）:
  - タイルはきれいに整列して監視できるが、そのままでは操作できない。
  - 以前 attach を主経路にしようとした際に正しく動作せず、参照専用に寄せた経緯がある。
  - しかし利用上は「全タイル操作」ではなく「選択中タイルに対応する元ペインだけを操作したい」要求がある。
- 再現手順（最小で）:
  1) `tmux-dashboard` を起動して `dashboard` session を作成する。
  2) `dashboard:0` を開くと複数 tile に各 session の内容が表示される。
  3) 任意 tile を見ても、その場で元ペインへ入力する経路がない。
- 観測点（どこを見て確認するか）:
  - UI: `dashboard:0` の各 tile が viewer であること、pane title とタイル内容の対応
  - Log: orchestrator の renderer spawn ログ、wrapper の bootstrap / attach 系ログ
  - tmux state: `respawn-pane`, `list-panes`, `pane_title`, `window-size`
- 実際の観測結果（貼れる範囲で）:
  - Input/Operation: `tmux-dashboard` 起動後、各 tile pane は `tmux_dashboard.tile` を実行する
  - Output/State: tile 側で shell は動かず、`capture-pane` ベースの再描画のみ
- 情報源（ヒアリング/調査の根拠）:
  - ドキュメント: `README.md`（live view / capture-pane 前提）
  - コード: `tmux_dashboard/orchestrator.py`（`run_once` / mapping / `respawn-pane`）、`tmux_dashboard/tile.py`（capture-only loop）、`tmux_dashboard/tmuxio.py`（driver API）
  - テスト: `tests/test_orchestrator.py`, `tests/test_tmuxio.py`, `tests/test_wrapper_runtime.py`, `tests/test_vscode_terminal_support.py`
  - 過去ログ: `spec-lite/completed/20260401_081936_main/report.md`

## 対象ユーザー / 利用シナリオ (任意)
- 主な利用者（ロール）:
  - 複数 tmux session を並列運用し、dashboard から状況把握したい開発者
- 代表的なシナリオ:
  - dashboard で session 全体を俯瞰しながら、必要な時だけ選択した tile の元ペインへコマンドやキー入力を送りたい
  - attach の不安定さを回避しつつ、軽い操作と復帰を安全に行いたい

## スコープ（暴走防止のガードレール） (必須)
- MUST（必ずやる）:
  - 現状実装の表示アーキテクチャと attach 失敗履歴を踏まえて、実現方式を複数案で比較する
  - 技術的に実施可能な best practice を 1 つ推奨する
  - 提案内容を `spec-lite/current/*.md` と discussion シートに整理する
- MUST NOT（絶対にやらない／追加しない）:
  - このタスクでソースコード実装や挙動変更を行わない
  - attach/switch-client を前提とした unsafe な結論を、既知リスクを無視して推奨しない
- OUT OF SCOPE（今回やらない）:
  - 実際の入力プロキシ機能の実装
  - TUI 全互換（vim/fzf/less など）の保証
  - tmux 以外の multiplexer や UI フロントエンド対応

## 非交渉制約（守るべき制約） (必須)
- dashboard の既定挙動は read-only / viewer を維持する
- 入力可能化する場合も「選択中タイルのみ」に限定し、broadcast 操作はしない
- 既知の attach 不安定系を主経路へ戻さない
- 既存の非侵襲方針（global tmux config を汚さない）を維持する
- 提案は現行 repo の責務分離に沿わせる

## 前提（Assumptions） (必須)
- 利用者は tmux 上で dashboard を閲覧できる
- dashboard session には複数 client が attach しうる
- 入力ニーズの中心は「一部コマンドやキーを送ること」であり、当面は完全な terminal fidelity を最優先しない

## 判断材料/トレードオフ（Decision / Trade-offs） (任意)
- 論点: viewer アーキテクチャを維持したまま入力を足すべきか
  - 選択肢A: attach / switch-client に戻して実ペインを操作する
  - 選択肢B: viewer のまま control-plane で入力を転送する
  - 決定: B を推奨
  - 理由: 現状構造との整合が高く、既知の attach リスクを主経路に持ち込まないため

## リスク/懸念（Risks） (任意)
- R-001: 選択中 tile の定義が複数 client 環境で曖昧になりうる
- R-002: `send-keys` ベースでは高速 TUI 操作の体験が劣化する
- R-003: tile と target pane の対応情報が stale になると誤送信につながる

## 受け入れ条件（観測可能な振る舞い） (必須)
- AC-001:
  - Actor/Role: 設計者 / 保守者
  - Given: 現状の tmux-dashboard 実装と過去の report / discussion を調査した
  - When: 本タスクの要件定義と分析シートを読む
  - Then: なぜ dashboard が表示専用なのか、attach を避けるべき理由が根拠付きで理解できる
  - 観測点（UI/HTTP/DB/Log など）: `requirement.md`, discussion シート
  - 権限/認可条件（ある場合）: なし
- AC-002:
  - Actor/Role: 設計者 / 実装者
  - Given: 複数の実現案がある
  - When: 比較表と推奨結論を読む
  - Then: 少なくとも 3 案以上の方式比較と、採用 / 不採用理由、段階導入案、best practice が確認できる
  - 観測点（UI/HTTP/DB/Log など）: discussion シート、`design.md`
  - 権限/認可条件（ある場合）: なし
- AC-003:
  - Actor/Role: 実装者
  - Given: 将来この機能を実装する
  - When: `plan.md` を確認する
  - Then: どの責務に何を追加すべきか、テスト順序と導入フェーズが把握できる
  - 観測点（UI/HTTP/DB/Log など）: `plan.md`
  - 権限/認可条件（ある場合）: なし

### 入力→出力例 (任意)
- EX-001:
  - Input: 「選択中 tile だけに `npm test` を送る方法を設計したい」
  - Output: pane mapping 永続化 + `send-keys` / `paste-buffer` を用いる control-plane 方式を推奨
- EX-002:
  - Input: 「attach で直接操作する方式を再検討したい」
  - Output: 既知の attach / switch-client リスクを列挙した上で、主方式としては不採用と判断

## 例外・エッジケース（仕様として固定） (必須)
- EC-001:
  - 条件: dashboard が複数 client attach 状態で「selected pane」の意味が曖昧
  - 期待: 推奨方式では `--tile-pane` 明示指定を正本とし、selected 解決は補助導線として扱う
  - 観測点（UI/HTTP/DB/Log など）: `design.md`, discussion シート
- EC-002:
  - 条件: 元ペインへの入力が `send-keys` で完全再現できない TUI 操作を含む
  - 期待: MVP は shell / command / basic keys に限定し、完全 TUI は out of scope と明記する
  - 観測点: `requirement.md`, `design.md`

## 用語（ドメイン語彙） (必須)
- TERM-001: tile = `dashboard:0` 内で 1 セッションを映す viewer pane
- TERM-002: target pane = tile が mirror している元の tmux pane
- TERM-003: input proxy = 選択中 tile から target pane へ入力だけを転送する制御経路
- TERM-004: armed mode = 選択中 tile に対して明示的に入力転送を許可した状態

## 未確定事項（TBD / 要確認） (必須)
- Q-001:
  - 質問: MVP で扱う入力範囲をどこまでにするか
  - 選択肢:
    - A: printable text + Enter のみ
    - B: 上記に加えて矢印、Backspace、Ctrl 系、paste を含める
  - 推奨案（暫定）: B。ただし実装は段階導入し、Phase 1 は A 寄りに絞る
  - 影響範囲: AC-003 / 制約 / `plan.md`
- Q-002:
  - 質問: 「selected tile」の正本を何で定義するか
  - 選択肢:
    - A: active dashboard pane を自動解決
    - B: `tile_pane_id` を明示指定し、自動解決は補助にする
  - 推奨案（暫定）: B
  - 影響範囲: EC-001 / 実装インターフェース / テスト

## 完了条件（Definition of Done） (必須)
- すべてのAC/ECが文書で満たされる
- 未確定事項が整理され、推奨案が明記される
- MUST NOT / OUT OF SCOPE を破っていない（コード実装に踏み込んでいない）

## 省略/例外メモ (必須)
- 該当なし
