# wrapper create-window 問題の解決ベストプラクティス

- 作成日: 2026-03-31 (UTC)
- 対象: `./tmux-dashboard` 経路の create-window / swap-window / cleanup / 0 セッション収束の安定化
- 根拠:
  - `spec-lite/current/discussions/wrapper-create-window-root-cause-20260331.md`
  - `spec-lite/current/discussions/acceptance-review-wrapper-fix-20260331.md`

## 1. 結論

今回の問題は、単一の create-window バグではなく、次の 3 層の契約不足が重なって起きている。

1. driver 層が tmux command failure を fail-closed に扱えていない
2. orchestrator 層が「実在しない target」と「cleanup が必要な target」を区別しきれていない
3. 0 セッション short-circuit が UI の後始末まで責任を持っていない

したがって、ベストプラクティスは「局所修正を足す」のではなく、「driver / orchestrator / UI 収束の責務境界を明確にして契約で閉じる」ことである。

## 2. 推奨アプローチ

### 2.1 driver は tmux failure を必ず例外化する

- `create_window()` だけでなく `swap_window()` と `kill_window()` も同じ失敗検知 helper を通す
- CLI / libtmux の両 driver で同じ契約に揃える
- 「tmux が失敗を返したが Python 側は成功として進む」経路を残さない

### 2.2 cleanup 対象は「実在確認済み target」に限定する

- create failure 直後は、予測した `staging_target` をそのまま residual queue に積まない
- まず `list-windows` または `list-panes` で target の実在を確認する
- 実在しない target は cleanup warning の補足情報には使えても、retry queue には入れない

### 2.3 residual queue は「再試行価値のある実体」だけを保持する

- queue に積むのは swap 後 cleanup failure のように、実際に window が残っているケースだけにする
- missing target を queue に入れると、次サイクルで ghost retry が先頭を塞ぎ、本当に消したい residual window の cleanup を遅らせる

### 2.4 0 セッション収束は UI の後始末まで含めて完了とみなす

- pane 数を 1 に戻すだけで終わらせない
- pane title も空文字または中立値へ戻す
- 直前の実セッション名が残る状態を「正常収束」とみなさない

### 2.5 wrapper の非 TTY 問題と create-window 問題は分けて扱う

- `open terminal failed: not a terminal` は wrapper の attach/switch-client 特性であり、今回の create-window 問題とは別軸
- まずは provisioning 契約を正しくする
- 非 TTY wrapper の終了コード改善は、必要なら別 issue として切り出す

## 3. 実装上の具体策

### 3.1 driver helper の統一

- `_raise_if_cmd_failed()` を `create/swap/kill` の全 command path に適用する
- libtmux でも `returncode`, `stderr`, `stdout` を共通ルールで評価する
- `create_window()` の「実在確認 helper」を `window_exists(target)` 相当へ抽出し、orchestrator からも再利用できる形にする

### 3.2 orchestrator の cleanup 分岐整理

- create failure path:
  - missing target なら residual queue に積まない
  - existing target なら best-effort cleanup → 失敗時のみ residual queue へ入れる
- swap failure path:
  - staging target は実在する前提なので cleanup failure を residual queue へ入れてよい
- 0 セッション path:
  - `kill_other_panes(window_target)` 後に single pane の title をクリアする

### 3.3 テスト戦略

- unit:
  - libtmux `swap_window()` failure が例外になる
  - libtmux `kill_window()` failure が例外になる
  - create failure で missing target が residual queue に積まれない
  - 0 セッション short-circuit 後に pane title が空になる
- e2e:
  - wrapper 起動後に全対象セッションを削除すると、`dashboard:0` が 1 pane かつ空 title になる

## 4. 実施順の推奨

1. driver の fail-closed 補完
2. orchestrator の ghost residual queue 防止
3. 0 セッション stale title 解消
4. unit / e2e 回帰追加
5. 手動受け入れ再実施

## 5. 避けるべき対処

- wrapper の visible window 名だけを変えて症状を隠す
- cleanup failure を warning のみで飲み込み、default driver の silent success を放置する
- 0 セッション時の stale title を「表示だけの問題」として後回しにする
- 非 TTY wrapper の終了コード問題を今回の create-window 契約修正と混ぜる

## 6. 完了判定の目安

以下が満たされたら、今回の追加修正は妥当と判断できる。

- `swap_window()` / `kill_window()` failure が unit test で例外として観測できる
- create failure 後の missing target が residual queue を汚染しない
- 0 セッション時に `dashboard:0` が 1 pane かつ空 title へ収束する
- `uv run pytest -q` がグリーン
- 手動テストで wrapper/direct runner の same-name 条件と 0 セッション収束を再確認できる
