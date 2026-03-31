---
種別: 要件定義書
機能ID: "fix-tmux-headless-layout"
機能名: "headless tmux でのレイアウト復旧"
関連Issue: ["tmux split-window headless failure analysis", "wrapper create window root cause analysis", "wrapper create-window acceptance review 20260331", "window-size manual resize follow-up analysis 20260331"]
状態: "draft"
作成者: "codex"
最終更新: "2026-03-31"
---

# fix-tmux-headless-layout headless tmux でのレイアウト復旧 — 要件定義（WHAT / WHY）

## 目的（ユーザーに見える成果 / To-Be） (必須)
- `tmux-dashboard` を detached / headless な tmux 環境でも安定して起動できるようにし、複数セッションを期待どおりタイル表示できる状態へ戻す。
- `./tmux-dashboard` wrapper 経由でも direct runner と同じ復旧品質で動作し、runner window を含む運用でも破綻しない状態にする。
- レイアウト再構成に失敗した場合でも dashboard を壊したまま放置せず、原因を観測できる形で縮退または回復できるようにする。
- 外側 Terminal の resize に対して `dashboard` window 自体が追随し、内側 pane レイアウトも自然に再計算される状態へ戻す。

## 背景・現状（As-Is / 調査メモ） (必須)
- 現状の挙動（事実）:
  - 現行実装は `split-window -p <percent>` を使ってレイアウトを構成している。
  - `tmux 3.4` の detached / headless 条件では `split-window -p 50` が `size missing` で失敗する。
  - `split-window -l 40` と `split-window -l 50%` は同条件で成功した。
  - `split-window -p` 問題の修正後も、`./tmux-dashboard` wrapper 経由では `dashboard:0` が 1 pane のまま残る再現がある。
  - wrapper は session 名 `dashboard` と visible window 名 `dashboard` を同時に作成し、さらに `__tmux_dashboard_runner__` window で内部 runner を起動する。
  - `CliDriver.create_window()` / `LibtmuxDriver.create_window()` は `tmux new-window ... -t session_name` を使っており、wrapper の命名条件では `create window failed: index 0 in use` で失敗する。
  - `LibtmuxDriver.create_window()` は `returncode` / `stderr` を見ず、window が存在しないのに requested target を返せてしまう。
  - `apply_layout()` は最初に `kill-pane -a` を実行するため、途中失敗時に dashboard が 1 pane に退行する。
  - `run_once()` は pane 数不足でも `zip()` で黙って一部セッションだけ描画できてしまう。
  - `check_pane_integrity()` はタイトル設定前に走るため、初回に誤警告を出しやすい。
  - direct runner の既存 E2E は `tmux new-session -d -s dashboard` を使っており、初期 window 名が `zsh` のため wrapper 固有の同名条件を再現していなかった。
  - ユーザー実機では `dashboard` target の tmux window option が `window-size manual` になっており、外側 Terminal を広げても `dashboard:0` の `window_width` が追随しない。
  - ユーザー実機では `dashboard` session に複数 client が attached しており、`window-size manual` の固定が右側 unused space の視覚症状として顕在化している。
- 現状の課題（困っていること）:
  - headless 実行時に dashboard が期待どおり複数 pane を作れず、ツールの主要価値を失っている。
  - レイアウト失敗が可視化されにくく、障害調査が難しい。
  - テストが `xfail` に依存しており、実環境での正常性保証が弱い。
  - wrapper 経路だけ direct runner と異なる壊れ方をし、利用者にとって最も自然な入口が信用できない。
  - `dashboard` target が `window-size manual` のまま残ると、pane 数や列数は正しくても「外側 Terminal を広げても dashboard が追随しない」状態が再発する。
- 再現手順（最小で）:
  1) `TERM=screen-256color tmux new-session -d -x 120 -y 40 -s dashboard 'sh -lc "sleep 300"'`
  2) `tmux split-window -h -p 50 -t dashboard:0`
  3) `size missing` が返ることを確認する
- 観測点（どこを見て確認するか）:
  - UI: `tmux list-panes -t dashboard:0 -F '#{pane_id}|#{pane_index}|#{pane_width}x#{pane_height}|#{pane_title}'`
  - Log: `uv run python -m tmux_dashboard --once --iterations 1` の標準出力 / ログ
  - Log: wrapper runner の `non-destructive apply failed: pane shortage: tiles=0 sessions=3`
  - Code: `tmux_dashboard/tmuxio.py`, `tmux_dashboard/orchestrator.py`, `tmux-dashboard`, `tests/test_e2e_tmux.py`
- 実際の観測結果（貼れる範囲で）:
  - Input/Operation: `tmux split-window -h -p 50 -t dashboard:0`
  - Output/State: `size missing`
  - Input/Operation: `tmux split-window -h -l 50% -t dashboard:0`
  - Output/State: 成功し、pane が 2 つに増える
  - Input/Operation: `tmux new-window -d -P -F '#{session_name}:#{window_index}' -t dashboard` under wrapper-equivalent naming
  - Output/State: `create window failed: index 0 in use`
  - Input/Operation: `tmux new-window -d -P -F '#{session_name}:#{window_index}' -t dashboard:99`
  - Output/State: 成功し、window `dashboard:99` が作成される
- 情報源（ヒアリング/調査の根拠）:
  - ドキュメント: `@spec-lite/current/discussions/tmux-split-window-headless-analysis.md`
  - ドキュメント: `@spec-lite/current/discussions/wrapper-create-window-root-cause-20260331.md`
  - ドキュメント: `@spec-lite/current/discussions/resize-follow-up-analysis-20260331.md`
  - ドキュメント: `@spec-lite/current/discussions/window-size-manual-remediation-options-20260331.md`
  - ドキュメント: `@spec-lite/current/discussions/window-size-latest-switch-guide-20260331.md`
  - コード: `tmux_dashboard/tmuxio.py`（`CliDriver.split_window`, `CliDriver.split_pane`, `LibtmuxDriver.split_window`, `LibtmuxDriver.split_pane`）
  - コード: `tmux_dashboard/tmuxio.py`（`CliDriver.create_window`, `LibtmuxDriver.create_window`）
  - コード: `tmux_dashboard/orchestrator.py`（`apply_layout`, `check_pane_integrity`, `run_once`）
  - コード: `tmux-dashboard`（wrapper の session/window 構成）
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
  - `./tmux-dashboard` wrapper 経由でも複数 pane レイアウトを構成できるようにする
  - レイアウト失敗時に dashboard を単一 pane に壊したままにしない
  - pane 数不足や分割失敗を観測可能にする
  - 初回の pane integrity 判定ノイズを抑える
  - 再現した失敗モードをテストで担保する
  - `create_window()` が phantom target を返さず、window 作成失敗を fail-closed で扱う
  - `swap-window` / `kill-window` failure も driver 層で fail-closed に扱う
  - 0 セッション収束後に stale pane title を残さない
  - create failure 後に ghost residual target を retry queue に残さない
  - `dashboard` target の `window-size` を `latest` として管理し、outer Terminal resize に追随できる状態を維持する
  - 既存 `manual` 汚染が残る session でも、起動時または runner preflight で自動回復できるようにする
- MUST NOT（絶対にやらない／追加しない）:
  - 利用者に tmux attach 必須の運用を強制しない
  - dashboard 以外のセッション設定やグローバル tmux 設定を変更しない
  - 調査対象外のレンダラー描画仕様や UI デザインを変更しない
  - wrapper の visible window 名を変更するだけで問題を回避し、根本原因を放置しない
- OUT OF SCOPE（今回やらない）:
  - `pipe_stream` モードの本格実装
  - 新しい表示機能やセッション選択ロジックの全面刷新
  - README 全面改稿や新規 CLI オプション追加

## 非交渉制約（守るべき制約） (必須)
- Python 3.10+ / tmux 3.2+ 前提を維持する
- 依存ライブラリは原則追加しない
- dashboard 以外のセッションへ侵襲的変更を加えない
- `dashboard` 管理 window に対する window-local option 変更に限定し、global tmux option は変更しない
- 既存 CLI (`python -m tmux_dashboard`, `--once`, `--iterations`, `--window-target`) の互換を壊さない
- TDD で進め、最終的に `uv run pytest -q` をグリーンにする

## 前提（Assumptions） (必須)
- headless 再現はこの開発環境の `tmux 3.4` で確認済みであり、少なくとも同系統の環境では現実的な障害である
- `split-window -l` 系は current target / pane target の両方で使える
- 調査レポートに記録した実測結果を本件の As-Is として扱う
- `-l` の既定は absolute-cell 指定とし、算出長が 0 以下になる場合のみ `%` 指定へ fallback する
- tmux の `new-window` で target index を指定したい場合は `session:window_index` を渡す必要がある
- 今回の要件では「いま使っている Terminal の resize に追随する」挙動が優先であり、multi-client 時の既定 policy は `latest` が最も要件に近い

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
- R-004: `window-size latest` は最後に active になった client に寄るため、同じ `dashboard` session を複数 client で同時監視する運用では見え方が変わりうる

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
  - Then: staging 用の一時 window または同等の内部退避機構で分割成功を確認した場合にのみ `dashboard:0` へ切り替わる。`swap-window` failure は driver 例外と orchestrator error log により観測され、既存 `dashboard:0` 状態を保持する。swap 後の旧 window `kill-window` cleanup 失敗は新 `dashboard:0` を成功扱いのまま残しつつ警告と residual cleanup retry 対象として観測できる
  - 観測点（UI/HTTP/DB/Log など）: pane 数, pane title, `dashboard:0` の中身, swap/cleanup の warning/error ログ, driver 例外
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
  - Then: 一部セッションだけを黙って表示せず、`run_once()` は dashboard を変更せずに明示ログを残し、CLI entrypoint は `--once` / 通常ループともに exit 0 のまま観測可能にする
  - 観測点（UI/HTTP/DB/Log など）: `dashboard:0` の pane 状態不変、`run_once()` / CLI ログ、テスト結果
  - 権限/認可条件（ある場合）: 該当なし
- AC-005:
  - Actor/Role: 開発者
  - Given: wrapper が `dashboard` session と visible window `dashboard`、runner window `__tmux_dashboard_runner__` を持つ通常運用状態
  - When: `./tmux-dashboard` を実行する
  - Then: `dashboard:0` が対象セッション数に応じて再構成され、wrapper 経由でも direct runner と同等に複数 pane と pane title が得られる
  - 観測点（UI/HTTP/DB/Log など）: `tmux list-panes -t dashboard:0 ...`, wrapper runner ログ
  - 権限/認可条件（ある場合）: 該当なし
- AC-006:
  - Actor/Role: 開発者
  - Given: staging window 作成コマンドが失敗する条件がある
  - When: `create_window()` を通じて staging window を作成する
  - Then: 実在しない target を返さず、driver 層では例外、orchestrator / CLI 層では dashboard 不変と明示ログとして扱われる
  - 観測点（UI/HTTP/DB/Log など）: driver 例外, orchestrator / CLI ログ, driver 単体テスト
  - 権限/認可条件（ある場合）: 該当なし
- AC-007:
  - Actor/Role: 開発者
  - Given: 直前サイクルで複数セッションの pane title が設定され、その後表示対象セッションが 0 件になった
  - When: `run_once()` が 0 セッション short-circuit を実行する
  - Then: `dashboard:0` は単一 pane を維持しつつ、pane title は空または 0 セッション用の中立値に更新され、削除済みセッション名を表示しない
  - 観測点（UI/HTTP/DB/Log など）: `tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}'`, orchestrator テスト
  - 権限/認可条件（ある場合）: 該当なし
- AC-008:
  - Actor/Role: 開発者
  - Given: `dashboard` target が既存 session として残っており、tmux window option が `window-size manual` または `latest` 以外になっている
  - When: wrapper 起動または runner の通常サイクルが `dashboard` target を扱う
  - Then: `dashboard` target の window-local option は `window-size latest` に収束し、外側 Terminal の resize 後に `dashboard:0` の `window_width` と pane 幅/高さが追随して変化する
  - 観測点（UI/HTTP/DB/Log など）: `tmux show-options -t dashboard:0 -w`, `tmux display-message -p -t dashboard:0 '#{window_width} #{window_height}'`, `tmux list-panes -t dashboard:0 ...`, E2E / 手動テスト
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
  - 期待: 既存どおり単一 pane の dashboard を維持し、エラー扱いしない。pane title は空または中立値へ収束する
  - 観測点（UI/HTTP/DB/Log など）: pane 数 1、pane title、ログ
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
- EC-005:
  - 条件: session 名と visible window 名がどちらも `dashboard`
  - 期待: `create_window()` は適切な `session:window_index` target を使って staging window を作成できる
  - 観測点: `tmux list-windows`, wrapper 経路 E2E, driver 単体テスト
- EC-006:
  - 条件: tmux / libtmux から `new-window` の失敗が返る
  - 期待: phantom target を返さず fail-closed で停止し、原因がログまたは例外で観測できる
  - 観測点: driver 単体テスト、orchestrator ログ
- EC-007:
  - 条件: swap 後 cleanup 失敗で旧 window が残置し、次サイクルが来る
  - 期待: orchestrator は残置 window の best-effort cleanup を再試行し、成功でも失敗でも新規レイアウト進行を不必要に妨げない
  - 観測点: warning / info ログ、残置 window の有無、orchestrator テスト
- EC-008:
  - 条件: `create_window()` が window 未作成のまま失敗し、その予測 staging target が tmux 上に存在しない
  - 期待: orchestrator はその missing target を residual cleanup queue に積まず、後続サイクルの retry を ghost target で塞がない
  - 観測点: orchestrator テスト、warning ログ、residual queue 状態
- EC-009:
  - 条件: 既存の `dashboard` target が `window-size manual` のまま残っている
  - 期待: wrapper 起動時または runner preflight で `window-size latest` へ自動回復し、利用者に `kill-session` を要求しない
  - 観測点: `tmux show-options -t dashboard:0 -w`, wrapper / runner テスト
- EC-010:
  - 条件: `dashboard` session に複数 client が attached している
  - 期待: 既定 policy は `latest` とし、最後に active になった client 基準で resize 追随する。少なくとも `manual` 固定による追随停止は起きない
  - 観測点: `tmux list-clients -t dashboard`, `tmux show-options -t dashboard:0 -w`, 手動テスト

## 用語（ドメイン語彙） (必須)
- TERM-001: headless = tmux client が付いていない detached 実行状態
- TERM-002: pane 数不足 = 表示対象セッション数より `dashboard:0` の pane 数が少ない状態
- TERM-003: 分割戦略 = `split-window` / `split-pane` に渡すサイズ指定方式とその配分ロジック
- TERM-004: phantom target = tmux に実在しないのに driver が返してしまう window target
- TERM-005: ghost residual target = create failure 後に retry queue へ誤記録された、tmux 上に実在しない cleanup target
- TERM-006: window-size policy = tmux が window の有効サイズを決める window-local option。今回の既定は `latest` を採用する

## 未確定事項（TBD / 要確認） (必須)
- 該当なし

## 完了条件（Definition of Done） (必須)
- すべてのAC/ECが満たされる
- 未確定事項が解消される、または暫定合意が `design.md` / `plan.md` に反映される
- MUST NOT / OUT OF SCOPE を破っていない
- `uv run pytest -q` がグリーンで、headless 分割、wrapper 経路、`window-size latest` 収束と resize 追随の回帰を再現するテストが追加されている

## 省略/例外メモ (必須)
- 該当なし
