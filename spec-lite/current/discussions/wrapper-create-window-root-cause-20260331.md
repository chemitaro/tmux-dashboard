---
title: wrapper path create_window root cause analysis
date: 2026-03-31
status: draft
kind: investigation
---

# wrapper path create_window root cause analysis

## 結論

`./tmux-dashboard` 経由で復旧しない本質原因は、`tmux_dashboard/tmuxio.py` の `create_window()` 実装が `tmux new-window -t` の意味を取り違えていることだった。

- `CliDriver.create_window()` と `LibtmuxDriver.create_window()` はどちらも `new-window ... -t session_name` を使っている。
- しかし staging window を特定 index で作りたいなら、tmux には `-t session_name:window_index` を渡す必要がある。
- wrapper は visible window を `dashboard` という名前で作るため、session 名 `dashboard` と window 名 `dashboard` が衝突する。
- この状態で `tmux new-window -t dashboard` を実行すると、tmux 3.4 では `create window failed: index 0 in use` で失敗する。
- `LibtmuxDriver.create_window()` はこの失敗を検知せず、requested target をそのまま返してしまうため、後段では「存在しない staging window」に対して pane 列挙を行い、`pane shortage: tiles=0 sessions=3` になる。

要するに、wrapper 経由の不具合は `split-window` 修正の取りこぼしではなく、`create_window()` の target 解決ミスと、wrapper が作る `session/window` 同名条件が組み合わさって顕在化していた。

## 観測した症状

wrapper 経由では、監視対象 session があるにもかかわらず `dashboard:0` が 1 pane のまま残る。

runner log には以下が出る。

```text
detected: sessions=['alpha', 'beta', 'gamma'], window=80x24
plan: columns=2 rows=2
non-destructive apply failed: pane shortage: tiles=0 sessions=3
```

tmux 状態を見ると runner window は存在するが、staging window は存在せず、active dashboard window も単一 pane のまま。

## 再現実験

### 1. wrapper と同じ命名条件では raw tmux コマンド自体が失敗する

session 名と最初の window 名をどちらも `dashboard` にすると失敗した。

```bash
tmux -L "$sock" new-session -d -s dashboard -n dashboard
tmux -L "$sock" new-window -d -P -F '#{session_name}:#{window_index}' -t dashboard
```

結果:

```text
status=1
out=create window failed: index 0 in use
```

同じ session 名でも、最初の window 名が既定の `zsh` のままなら成功した。

```bash
tmux -L "$sock" new-session -d -s dashboard
tmux -L "$sock" new-window -d -P -F '#{session_name}:#{window_index}' -t dashboard
```

結果:

```text
status=0
out=dashboard:1
```

この差により、wrapper 特有の「visible window を `dashboard` と命名する」条件が不具合の引き金になっていることを確認した。

### 2. 正しい target を渡すと staging window は作成できる

次のコマンドは成功した。

```bash
tmux -L "$sock" new-window -d -P -F '#{session_name}:#{window_index}' -t dashboard:99
```

結果:

```text
status=0
out=dashboard:99
```

`list-windows` にも `99|zsh|0` が追加された。

つまり、tmux が壊れているのではなく、`create_window()` の target 指定が誤っている。

### 3. libtmux driver は失敗を見逃して phantom target を返す

`LibtmuxDriver.create_window()` を独立ソケットで直接呼んで観測したところ、

- 返り値: `dashboard:99`
- 直後の `list-windows`: `0|dashboard|1`, `1|__tmux_dashboard_runner__|0` のまま
- `list_panes_detailed("dashboard:99")`: `[]`

だった。

同時に `libtmux.Server.cmd(...)` の生レスポンスを確認すると、

```text
stdout []
stderr ['create window failed: index 0 in use']
returncode 1
```

となっていた。

つまり `LibtmuxDriver.create_window()` は `returncode` / `stderr` を見ずに進み、window が作られていないのに `requested_target` を返している。

## 既存テストが見逃した理由

`tests/test_e2e_tmux.py` は direct runner 経路を検証しており、wrapper 経路を検証していない。

加えて、E2E テストの dashboard session は次のように作られている。

```bash
tmux new-session -d -s dashboard
```

このため最初の window 名は `dashboard` ではなく既定の `zsh` になり、`new-window -t dashboard` の曖昧条件が発生しない。

一方 wrapper は次を実行する。

```bash
tmux new-session -d -s dashboard -n dashboard -c "$REPO_DIR"
```

そのため wrapper だけが `session name == visible window name == dashboard` の条件を作り、問題を再現させていた。

## 影響範囲

影響は少なくとも次の 3 箇所にまたがる。

- `tmux_dashboard/tmuxio.py`
  - `CliDriver.create_window()`
  - `LibtmuxDriver.create_window()`
- `tmux-dashboard`
  - visible dashboard window を `dashboard` と命名している
- `tmux_dashboard/orchestrator.py`
  - 後段では `pane shortage: tiles=0 sessions=3` として現れるが、ここは症状の顕在化箇所であり一次原因ではない

## 排除できた仮説

- `split-window -l` の回帰が主因ではない
  - wrapper failure は split に到達する前の staging window 作成で壊れている
- libtmux の pane 列挙キャッシュ不整合が主因ではない
  - raw tmux の `new-window -t dashboard` 自体が失敗しているため、cache より前段で問題が起きている
- help 文言の不足が主因ではない
  - help 修正は必要だったが、今回の復旧不全とは独立

## 修正方針の示唆

本件を直すなら、最低でも以下が必要になる。

1. `create_window()` で `new-window -t session_name:window_index` を使う。
2. libtmux / cli の両 driver で `returncode` または created window 実在確認を行い、失敗時は例外にする。
3. wrapper 経路を再現する E2E か integration test を追加する。

## 主要エビデンス

- wrapper 再現ログ
  - `non-destructive apply failed: pane shortage: tiles=0 sessions=3`
- raw tmux 比較
  - `same_name`: `create window failed: index 0 in use`
  - `default_name`: `dashboard:1`
- libtmux 生レスポンス
  - `stdout []`
  - `stderr ['create window failed: index 0 in use']`
  - `returncode 1`
