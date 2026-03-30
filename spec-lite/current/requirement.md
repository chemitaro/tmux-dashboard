---
種別: 要件定義書
機能ID: "fix-tmux-headless-layout"
機能名: "headless tmux でのレイアウト復旧"
関連Issue: ["tmux split-window headless failure analysis"]
状態: "draft"
作成者: "codex"
最終更新: "2026-03-30"
---

# fix-tmux-headless-layout headless tmux でのレイアウト復旧 — 要件定義（WHAT / WHY）

## 目的（ユーザーに見える成果 / To-Be） (必須)
- `tmux-dashboard` を detached / headless な tmux 環境でも安定して起動できるようにし、複数セッションを期待どおりタイル表示できる状態へ戻す。
- レイアウト再構成に失敗した場合でも dashboard を壊したまま放置せず、原因を観測できる形で縮退または回復できるようにする。

## 背景・現状（As-Is / 調査メモ） (必須)
- 現状の挙動（事実）:
  - 現行実装は `split-window -p <percent>` を使ってレイアウトを構成している。
  - `tmux 3.4` の detached / headless 条件では `split-window -p 50` が `size missing` で失敗する。
  - `split-window -l 40` と `split-window -l 50%` は同条件で成功した。
  - `apply_layout()` は最初に `kill-pane -a` を実行するため、途中失敗時に dashboard が 1 pane に退行する。
  - `run_once()` は pane 数不足でも `zip()` で黙って一部セッションだけ描画できてしまう。
  - `check_pane_integrity()` はタイトル設定前に走るため、初回に誤警告を出しやすい。
- 現状の課題（困っていること）:
  - headless 実行時に dashboard が期待どおり複数 pane を作れず、ツールの主要価値を失っている。
  - レイアウト失敗が可視化されにくく、障害調査が難しい。
  - テストが `xfail` に依存しており、実環境での正常性保証が弱い。
- 再現手順（最小で）:
  1) `TERM=screen-256color tmux new-session -d -x 120 -y 40 -s dashboard 'sh -lc "sleep 300"'`
  2) `tmux split-window -h -p 50 -t dashboard:0`
  3) `size missing` が返ることを確認する
- 観測点（どこを見て確認するか）:
  - UI: `tmux list-panes -t dashboard:0 -F '#{pane_id}|#{pane_index}|#{pane_width}x#{pane_height}|#{pane_title}'`
  - Log: `uv run python -m tmux_dashboard --once --iterations 1` の標準出力 / ログ
  - Code: `tmux_dashboard/tmuxio.py`, `tmux_dashboard/orchestrator.py`, `tests/test_e2e_tmux.py`
- 実際の観測結果（貼れる範囲で）:
  - Input/Operation: `tmux split-window -h -p 50 -t dashboard:0`
  - Output/State: `size missing`
  - Input/Operation: `tmux split-window -h -l 50% -t dashboard:0`
  - Output/State: 成功し、pane が 2 つに増える
- 情報源（ヒアリング/調査の根拠）:
  - ドキュメント: `@spec-lite/current/discussions/tmux-split-window-headless-analysis.md`
  - コード: `tmux_dashboard/tmuxio.py`（`CliDriver.split_window`, `CliDriver.split_pane`, `LibtmuxDriver.split_window`, `LibtmuxDriver.split_pane`）
  - コード: `tmux_dashboard/orchestrator.py`（`apply_layout`, `check_pane_integrity`, `run_once`）
  - コード: `tests/test_e2e_tmux.py`（headless 前提の `xfail`）

## 対象ユーザー / 利用シナリオ (任意)
- 主な利用者（ロール）:
  - 複数 tmux セッションを並行監視したい開発者
  - attach せずに dashboard を常駐起動したい利用者
- 代表的なシナリオ:
  - detached で dashboard を起動し、あとから `tmux attach -t dashboard` して全セッションを俯瞰する
  - VS Code integrated terminal や headless サーバ上で常時 dashboard を動かす

## スコープ（暴走防止のガードレール） (必須)
- MUST（必ずやる）:
  - headless / detached 条件で複数 pane レイアウトを構成できるようにする
  - レイアウト失敗時に dashboard を単一 pane に壊したままにしない
  - pane 数不足や分割失敗を観測可能にする
  - 初回の pane integrity 判定ノイズを抑える
  - 再現した失敗モードをテストで担保する
- MUST NOT（絶対にやらない／追加しない）:
  - 利用者に tmux attach 必須の運用を強制しない
  - dashboard 以外のセッション設定やグローバル tmux 設定を変更しない
  - 調査対象外のレンダラー描画仕様や UI デザインを変更しない
- OUT OF SCOPE（今回やらない）:
  - `pipe_stream` モードの本格実装
  - 新しい表示機能やセッション選択ロジックの全面刷新
  - README 全面改稿や新規 CLI オプション追加

## 非交渉制約（守るべき制約） (必須)
- Python 3.10+ / tmux 3.2+ 前提を維持する
- 依存ライブラリは原則追加しない
- dashboard 以外のセッションへ侵襲的変更を加えない
- 既存 CLI (`python -m tmux_dashboard`, `--once`, `--iterations`, `--window-target`) の互換を壊さない
- TDD で進め、最終的に `uv run pytest -q` をグリーンにする

## 前提（Assumptions） (必須)
- headless 再現はこの開発環境の `tmux 3.4` で確認済みであり、少なくとも同系統の環境では現実的な障害である
- `split-window -l` 系は current target / pane target の両方で使える
- 調査レポートに記録した実測結果を本件の As-Is として扱う
- `-l` の既定は absolute-cell 指定とし、算出長が 0 以下になる場合のみ `%` 指定へ fallback する

## 判断材料/トレードオフ（Decision / Trade-offs） (任意)
- 論点: `-p` 維持か `-l` への変更か
  - 選択肢A: `-p` を維持し、tmux 起動条件だけで回避する
  - 選択肢B: 分割戦略を `-l` ベースへ切り替える
  - 決定: 選択肢Bを採用する
  - 理由: 実測で `-l` が成功し、attach 必須運用を避けられるため

## リスク/懸念（Risks） (任意)
- R-001: `-l` への変更で端数配分ロジックが既存期待とずれる
- R-002: tmux バージョン差で `-l 50%` の解釈差がある可能性
- R-003: 既存 E2E の `xfail` を縮小する際、環境依存でテストが不安定になる可能性

## 受け入れ条件（観測可能な振る舞い） (必須)
- AC-001:
  - Actor/Role: 開発者
  - Given: detached / headless な tmux 環境で `dashboard` を新規作成できる
  - When: 対象セッションが 2 件以上ある状態で `uv run python -m tmux_dashboard --once --iterations 1` を実行する
  - Then: `dashboard:0` に対象セッション数に応じた pane が作成され、各 pane title に対象セッション名が設定される
  - 観測点（UI/HTTP/DB/Log など）: `tmux list-panes -t dashboard:0 ...`, CLI ログ
  - 権限/認可条件（ある場合）: 該当なし
- AC-002:
  - Actor/Role: 開発者
  - Given: 既存の dashboard に対して再レイアウトが必要な状態（セッション増減または window size 変更）がある
  - When: orchestrator が再レイアウトを実行する
  - Then: staging 用の一時 window または同等の内部退避機構で分割成功を確認した場合にのみ `dashboard:0` へ切り替わり、失敗時は既存 `dashboard:0` 状態を保持しつつ失敗をログで観測できる
  - 観測点（UI/HTTP/DB/Log など）: pane 数, pane title, ログ出力
  - 権限/認可条件（ある場合）: 該当なし
- AC-003:
  - Actor/Role: 開発者
  - Given: 初回起動直後または復旧直後で pane title がまだ期待セッション名と一致していない
  - When: 1 サイクルの `run_once()` を実行する
  - Then: タイトル未設定だけを理由に不要な警告や再レイアウトループを起こさない
  - 観測点（UI/HTTP/DB/Log など）: orchestrator ログ、pane title 一覧
  - 権限/認可条件（ある場合）: 該当なし
- AC-004:
  - Actor/Role: 開発者
  - Given: pane 数がセッション数より少ない、または分割が失敗した
  - When: dashboard の描画マッピングを作成する
  - Then: 一部セッションだけを黙って表示せず、失敗を明示的に観測できる
  - 観測点（UI/HTTP/DB/Log など）: 例外 / ログ / テスト結果
  - 権限/認可条件（ある場合）: 該当なし

### 入力→出力例 (任意)
- EX-001:
  - Input: 2 セッション `alpha`, `beta` と `window_width=120`, `min_tile_width=40`
  - Output: `dashboard:0` に 2 pane が存在し、pane title に `alpha`, `beta` が含まれる
- EX-002:
  - Input: headless 条件での再レイアウト失敗
  - Output: dashboard が単一 pane に破壊されず、失敗理由がログまたはテストで観測できる

## 例外・エッジケース（仕様として固定） (必須)
- EC-001:
  - 条件: 表示対象セッションが 0 件
  - 期待: 既存どおり単一 pane の dashboard を維持し、エラー扱いしない
  - 観測点（UI/HTTP/DB/Log など）: pane 数 1、ログ
- EC-002:
  - 条件: `split-window` または `split-pane` が失敗する
  - 期待: 既存 pane を破壊しきらずに失敗を観測可能にし、サイレント劣化しない
  - 観測点: pane 数、ログ、テスト
- EC-003:
  - 条件: pane title が未設定または一時的に既定値
  - 期待: 初回サイクルでただちに異常扱いしない。必要ならタイトル適用後の整合性で判定する
  - 観測点: ログ、pane title
- EC-004:
  - 条件: headless だが `-l` ベースの分割は利用可能
  - 期待: その経路で正常レイアウトを構築できる
  - 観測点: pane 数、pane 幅/高さ、E2E テスト

## 用語（ドメイン語彙） (必須)
- TERM-001: headless = tmux client が付いていない detached 実行状態
- TERM-002: pane 数不足 = 表示対象セッション数より `dashboard:0` の pane 数が少ない状態
- TERM-003: 分割戦略 = `split-window` / `split-pane` に渡すサイズ指定方式とその配分ロジック

## 未確定事項（TBD / 要確認） (必須)
- Q-001:
  - 質問: pane 数不足時の挙動は例外送出か、明示ログ + 縮退継続か
  - 選択肢:
    - A: 例外として fail-fast
    - B: ログを出して縮退継続
  - 推奨案（暫定）: A をテスト・内部処理、B を CLI ループ層
  - 影響範囲: AC-004 / EC-002 / run_once の責務設計

## 完了条件（Definition of Done） (必須)
- すべてのAC/ECが満たされる
- 未確定事項が解消される、または暫定合意が `design.md` / `plan.md` に反映される
- MUST NOT / OUT OF SCOPE を破っていない
- `uv run pytest -q` がグリーンで、headless 分割の回帰を再現するテストが追加されている

## 省略/例外メモ (必須)
- 該当なし
