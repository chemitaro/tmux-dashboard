# wrapper create-window 修正 受け入れ検査レポート

- 実施日: 2026-03-31 (UTC)
- 対象コミット: `69dec89 fix(tmux): wrapper経路のcreate-window失敗をfail-closedにする`
- 比較基点: `322f277 docs(spec-lite): wrapper 根本原因の仕様を更新`
- 判定: `fail`

## 1. 結論

今回の実装は、元の wrapper create-window 問題に対して大きく前進しており、`./tmux-dashboard` 経路でも `dashboard` session / `dashboard` window 同名条件で multi-pane layout を構成できることは確認できた。

ただし、受け入れ判定としてはまだ `pass` にできない。理由は次の 2 点である。

1. `libtmux` driver の `swap_window()` / `kill_window()` が tmux command failure を例外化しておらず、fail-closed 契約が崩れる
2. `create_window()` が「何も作らずに失敗した」ケースでも、存在しない staging target を residual cleanup queue に積みうる

加えて、手動テストでは 0 セッション収束後に pane title が古い session 名のまま残る観測があり、ユーザー視点では未解消感が残る。

## 2. 実施内容

### 2.1 Git 確認

- `git log --oneline --decorate -n 12`
- `git show --stat HEAD`
- 差分確認対象:
  - `tmux_dashboard/tmuxio.py`
  - `tmux_dashboard/orchestrator.py`
  - `tests/test_tmuxio.py`
  - `tests/test_orchestrator.py`
  - `tests/test_e2e_tmux.py`
  - `tests/test_cli_entry.py`

### 2.2 自動テスト

- 実行コマンド: `uv run pytest -q`
- 結果: `100 passed in 1.98s`

### 2.3 コードレビュー

- reviewer: `code_reviewer`
- review status: `fail`

## 3. レビュー指摘

### 3.1 P1: libtmux swap/cleanup failure が例外化されていない

- 重要度: `P1`
- 該当箇所: `tmux_dashboard/tmuxio.py:784-792`

`create_window()` では `_raise_if_cmd_failed()` を通して tmux command failure を検知している一方、`swap_window()` と `kill_window()` は `server.cmd(...)` の戻り値を検査していない。

そのため、tmux が `swap-window` / `kill-window` に対して failure を返しても Python 側で例外にならず、`orchestrator.run_once()` の failure handling が起動しない可能性がある。今回の実装は「swap failure は error log を出して active window を壊さない」「cleanup failure は residual retry に回す」という契約で組まれているため、ここが silent success になると仕様の本質部分が崩れる。

### 3.2 P2: create fail 後に存在しない residual target を記録しうる

- 重要度: `P2`
- 該当箇所: `tmux_dashboard/orchestrator.py:355-370`

`create_window()` が「window を 1 枚も作らずに失敗した」場合でも、現在の実装は予測した `staging_target` に対して cleanup を試み、その cleanup が失敗すると `_residual_window_targets` に記録する。

このとき実体のない target が queue に残ると、以後の `_retry_residual_cleanup()` が毎サイクルその ghost target を先頭で再試行し、後続の本物の residual cleanup を遅延させる。

## 4. 手動テスト

### 4.1 ケース A: direct runner で same-name session/window 条件を再現

#### 手順

```bash
tmux kill-server || true
tmux new-session -d -s dashboard -n dashboard
tmux new-session -d -s alpha
tmux new-session -d -s beta
tmux new-session -d -s gamma
uv run python -m tmux_dashboard --config <libtmux config> --window-target dashboard:0 --once --iterations 1
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_left}|#{pane_top}|#{pane_width}|#{pane_height}'
```

#### 結果

- `dashboard:0` は 3 pane に分割された
- pane title は `alpha`, `beta`, `gamma` に一致した
- 以前の root cause である「same-name 条件で create-window が失敗して 1 pane のまま止まる」症状は再現しなかった

#### 判定

- `pass`

### 4.2 ケース B: wrapper (`./tmux-dashboard`) を非対話シェルから実行

#### 手順

```bash
tmux kill-server || true
tmux new-session -d -s alpha
tmux new-session -d -s beta
tmux new-session -d -s gamma
./tmux-dashboard --config <libtmux config>
```

#### 結果

- `dashboard:0` には 3 pane が構成された
- runner window `__tmux_dashboard_runner__` も作成された
- ただし wrapper 自体は `open terminal failed: not a terminal` で exit `1`

#### 解釈

これは create-window 修正とは別で、wrapper の最後の `attach` / `switch-client` が TTY を前提としているために発生する。非対話シェルでは wrapper の exit code は失敗になるが、dashboard provisioning 自体は成功していた。

#### 判定

- 機能復旧の観点では `pass`
- ただし「非 TTY で wrapper を叩くと終了コードだけは失敗になる」という注意点は残る

### 4.3 ケース C: wrapper 起動後に対象セッションを順次削除

#### 手順

```bash
tmux kill-server || true
tmux new-session -d -s alpha
tmux new-session -d -s beta
./tmux-dashboard --config <libtmux config>
tmux kill-session -t alpha
tmux kill-session -t beta
tmux list-sessions -F '#{session_name}' | sort
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}'
```

#### 結果

- 残存 session は `dashboard` のみ
- `dashboard:0` は 1 pane に収束した
- しかし pane title は `alpha` のまま残った

#### 判定

- pane 数の収束だけを見ると `pass`
- UI 一貫性の観点では `fail`

#### 補足

現行 spec は 0 セッション時に「単一 pane を維持して正常終了する」ことは明示しているが、pane title のクリアまでは acceptance criteria に書き切れていない。それでも利用者が見る情報として stale title が残るため、実運用上は未解消問題として扱うのが妥当である。

## 5. 受け入れ判定

### 5.1 総合判定

- `fail`

### 5.2 理由

1. `libtmux` driver の `swap_window()` / `kill_window()` が fail-closed になっていない
2. create failure 後の residual cleanup queue に ghost target が残りうる
3. 0 セッション収束後に stale pane title が残る観測がある

## 6. 推奨アクション

1. `tmux_dashboard/tmuxio.py`
   - `swap_window()` と `kill_window()` でも `_raise_if_cmd_failed()` を適用する
2. `tmux_dashboard/orchestrator.py`
   - create failure 後は「その target が実在する場合のみ cleanup / residual 登録する」か、「missing target は residual に積まない」分岐を追加する
3. 0 セッション path
   - `kill_other_panes(window_target)` 後に pane title を明示クリアするか、0 セッション時専用の title policy を定義する
4. 追加テスト
   - libtmux swap failure / kill failure の unit test
   - create failure で ghost residual を残さない test
   - 0 セッション時の stale title regression test

## 7. 参考ログ

- `git log --oneline --decorate -n 12`
- `git show --stat HEAD`
- `uv run pytest -q`
- 手動テスト stderr:

```text
open terminal failed: not a terminal
```
