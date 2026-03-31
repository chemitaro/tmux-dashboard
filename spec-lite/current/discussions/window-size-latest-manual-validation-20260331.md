# S06 手動検証レポート（window-size latest 自動回復）

- 実施日: 2026-03-31 (UTC)
- 対象: `window-size manual` 汚染の自動回復と resize 追随
- 対象実装:
  - `tmux_dashboard/tmuxio.py`
  - `tmux_dashboard/orchestrator.py`
  - `tmux-dashboard`

## シナリオ 1: direct runner が manual を latest へ回復する

### 手順

```bash
tmux kill-server >/dev/null 2>&1 || true
tmux new-session -d -s dashboard
tmux new-session -d -s alpha
tmux new-session -d -s beta
tmux set-window-option -t dashboard:0 window-size manual

uv run python -m tmux_dashboard --config <libtmux設定> --window-target dashboard:0 --once --iterations 1

tmux show-options -w -t dashboard:0 window-size
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_width}x#{pane_height}'
```

### 結果

- `window-size latest` へ自動回復した
- pane title は `alpha`, `beta` へ更新された

実測:

```text
window-size latest
0|alpha|39x23
1|beta|40x23
```

## シナリオ 2: wrapper が manual を latest へ回復し、resize に追随する

### 手順

```bash
tmux kill-server >/dev/null 2>&1 || true
tmux new-session -d -s dashboard -n dashboard
tmux new-session -d -s alpha
tmux new-session -d -s beta
tmux new-session -d -s gamma
tmux set-window-option -t dashboard:0 window-size manual

tmux new-session -d -s control "cd /srv/mount/tmux-dashboard && ./tmux-dashboard"

tmux show-options -w -t dashboard:0 window-size
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_width}x#{pane_height}'

tmux resize-window -t dashboard:0 -x 79 -y 40
tmux display-message -p -t dashboard:0 '#{window_width}x#{window_height}'
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_width}x#{pane_height}'

tmux resize-window -t dashboard:0 -x 191 -y 98
tmux display-message -p -t dashboard:0 '#{window_width}x#{window_height}'
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_width}x#{pane_height}'
```

### 結果

- 起動後に `window-size latest` へ回復した
- 幅 `79` へ縮小すると全 pane 幅が `79` に追随した
- 幅 `191` へ拡大すると pane 幅が `95` へ再計算された

実測:

```text
window-size latest
0|alpha|80x6
1|beta|80x8
2|gamma|80x7

79x40
0|alpha|79x12
1|beta|79x13
2|gamma|79x12

191x98
0|alpha|95x47
1|beta|95x49
2|gamma|95x97
```

## 判定

- 判定: `pass`
- 根拠:
  - `window-size manual` 汚染の自動回復が direct runner / wrapper の両経路で確認できた
  - resize 時の `window_width` と pane 幅追随が確認できた

## シナリオ 3: multi-client 条件の観測（EC-010 補強）

### 観測コマンド

```bash
tmux show-options -t dashboard -w | rg 'window-size|aggressive-resize'
tmux list-clients -t dashboard -F '#{client_tty}|#{client_width}x#{client_height}|#{session_name}'
```

### 実機観測（ユーザー環境）

```text
window-size manual

/dev/ttys019|266x99|dashboard
/dev/ttys026|278x99|dashboard
```

### 解釈

- `dashboard` session に複数 client が attached している状態を確認できる。
- この条件で `window-size manual` だと、外側 Terminal のサイズ変化に window 自体が追随せず、unused space が残る症状と整合する。
- 本修正で `window-size latest` を保証することで、EC-010 の「multi-client 条件で manual 固定による追随停止を起こさない」要件に対する説明力を確保できる。

## シナリオ 4: 修正後の multi-client 条件で `latest` が active client 幅へ追随する

### 手順

```bash
tmux kill-server >/dev/null 2>&1 || true
tmux new-session -d -s dashboard -n dashboard
tmux new-session -d -s alpha
tmux new-session -d -s beta
tmux new-session -d -s gamma
tmux set-window-option -t dashboard:0 window-size manual

# direct runner を常駐起動して policy 自動回復を有効にする
uv run python -m tmux_dashboard --window-target dashboard:0 &

# control-mode client を 2 つ attach する
tmux -C attach-session -t dashboard
tmux -C attach-session -t dashboard

tmux list-clients -F '#{client_tty}|#{client_width}x#{client_height}|#{client_session}|#{client_control_mode}'
tmux show-options -w -t dashboard:0 window-size

# 1つ目の client を 79x40、2つ目の client を 191x98 相当に更新
tmux refresh-client -t <client1> -C 79x40
tmux display-message -p -t dashboard:0 '#{window_width}x#{window_height}'

tmux refresh-client -t <client2> -C 191x98
tmux display-message -p -t dashboard:0 '#{window_width}x#{window_height}'
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_width}x#{pane_height}|#{pane_title}'
```

### 結果

- `window-size latest` が維持された
- multi-client 条件でも、active client 側のサイズ更新に合わせて `dashboard:0` の `window_width` が `79x40` → `191x98` に追随した
- pane 幅も `191` に合わせて再計算された

実測:

```text
/dev/pts/16|80x|dashboard|1
/dev/pts/18|80x|dashboard|1
window-size latest

after client1 resize:
79x40

after client2 resize:
191x98
0|191x32|alpha
1|191x32|beta
2|191x31|gamma
```

### 解釈

- これは `tmux resize-window` を直接打って window を強制変更したのではなく、attached client 側のサイズ変更を `refresh-client -C` で与え、その結果として `dashboard:0` の `window_width` が追随した証跡である。
- したがって、AC-008 の「外側 Terminal resize に対する追随」と EC-010 の「multi-client 条件で latest が active client へ追随する」を、修正後状態で補強できる。
