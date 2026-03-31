---
種別: 調査メモ
機能ID: "fix-tmux-headless-layout"
機能名: "live wrapper misdisplay analysis"
関連Issue: ["wrapper 実行時に正しく表示されない"]
作成者: "codex"
作成日: "2026-03-31"
---

# live wrapper misdisplay analysis

## 結論

`./tmux-dashboard` を実行しても正しく表示されない現象は、実機では次の 2 層が重なっていた。

1. 新しく起動する runner が依存欠落で即死していた  
2. 以前に起動した別系統の古い runner が生き残っており、`dashboard:0` を継続的に別 session 集合へ再適用していた

このため、wrapper を実行しても:

- 新しい runner は起動に失敗する
- もしくは 1 回だけ反映しても、古い常駐 runner が直後に上書きする

という状態になっていた。

## 調査の事実

### 1. 現物の `dashboard` は plain shell のままだった

```bash
tmux list-windows -t dashboard -F '#{window_index}|#{window_name}|#{window_active}|#{window_width}x#{window_height}'
# 0|dashboard|1|89x48

tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_width}x#{pane_height}|#{pane_current_command}'
# 0|node@1f4a0dd3b78d:/srv/mount/tmux-dashboard|89x48|zsh
```

この時点では pane title は session 名ではなく、単なる shell pane だった。

### 2. wrapper は最後の attach で失敗するが、その前に runner 起動までは進んでいた

```bash
cd /srv/mount/tmux-dashboard && ./tmux-dashboard
# open terminal failed: not a terminal
```

`bash -x ./tmux-dashboard` では runner window 作成と `uv run --no-sync python -m tmux_dashboard --window-target dashboard:0` の起動までは確認できた。

### 3. 新しい runner は `yaml` 欠落で即死した

```bash
cd /srv/mount/tmux-dashboard
uv run --no-sync python -m tmux_dashboard --window-target dashboard:0 --once --iterations 1
```

結果:

```text
ModuleNotFoundError: No module named 'yaml'
```

`pyproject.toml` と `uv.lock` には `PyYAML` が入っている一方、実環境の依存同期が崩れていた。

### 4. `uv sync --locked` だけでは回復しないケースがあり、`.venv` 実体が壊れていた

```bash
cd /srv/mount/tmux-dashboard && uv sync --locked
cd /srv/mount/tmux-dashboard && uv run --no-sync python -c 'import sys; print(sys.executable); import yaml; print(yaml.__file__)'
```

実機では `uv sync --locked` が:

```text
Resolved 14 packages in 2ms
Checked 10 packages in 2ms
```

で終わっていたが、その後も:

```text
ModuleNotFoundError: No module named 'yaml'
```

となり、`.venv` 実体には `PyYAML` が入っていなかった。  
つまり、このケースでは `uv sync --locked` 単体では broken `.venv` を直せていない。

一方で調査環境では一時的に direct runner が起動した時刻もあり、`.venv` の状態が不整合なまま揺れていた可能性が高い。

### 5. `.venv` が壊れたままだと runner は即死し、wrapper 実行後にも process が残らない

```bash
cd /srv/mount/tmux-dashboard
uv run --no-sync python -m tmux_dashboard --window-target dashboard:0 --once --iterations 1
```

結果:

```text
ModuleNotFoundError: No module named 'yaml'
```

この状態では `./tmux-dashboard` を実行しても内部 runner が即死するため、最終的に:

```bash
ps -ef | grep 'tmux_dashboard --window-target dashboard:0' | grep -v grep
```

が空になり、`dashboard:0` は plain shell のまま残る。

### 6. それでも見え方が不安定だったのは、古い runner が別に残っていたため

過去の調査時点では古い runner が残っていた時刻帯があり、log 上は次のように観測された。

runner log の例:

```text
18:07:06 detected: sessions=['hoge', 'kkk']
18:07:08 detected: sessions=['alpha', 'beta', 'gamma']
18:07:10 detected: sessions=['alpha', 'beta', 'gamma']
...
```

となっており、別の常駐 runner が直後に再適用していたことが確認できた。

### 7. ユーザー実機では stale runner が 1 本残存した時刻帯もあったが、最新時点では runner は消えており shell のみ残っている

ユーザーからの追加観測:

```bash
ps -ef | grep 'tmux_dashboard --window-target dashboard:0' | grep -v grep
```

```text
node       83176   83099  0 17:29 pts/8    00:00:00 /home/node/.local/bin/uv run --no-sync python -m tmux_dashboard --window-target dashboard:0
node       83231   83176  0 17:29 pts/8    00:00:17 /srv/mount/tmux-dashboard/.venv/bin/python3 -m tmux_dashboard --window-target dashboard:0
```

同時に:

```bash
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_width}x#{pane_height}|#{pane_current_command}'
```

```text
0|node@1f4a0dd3b78d:/srv/mount/tmux-dashboard|89x48|zsh
```

その後の最新観測では:

```bash
ps -ef | grep 'tmux_dashboard --window-target dashboard:0' | grep -v grep
```

は空であり、`dashboard:0` は:

```text
0|node@1f4a0dd3b78d:/srv/mount/tmux-dashboard|122x5|zsh
```

だった。

このことから、少なくともユーザー実機では時刻によって次の両方が起きていた:

- `dashboard:0` を管理しているつもりの runner は 17:29 開始の古い 1 系統のみ
- しかし現物の `dashboard:0` は pane title が shell のままで、dashboard として構成されていない
- 最新時点では stale runner も消えており、broken `.venv` により新しい runner も立ち上がらない

という状態が確認できた。

## 現在の観測結果

最終観測時点では `dashboard:0` は次の状態になっていた。

```bash
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_width}x#{pane_height}|#{pane_current_command}'
```

```text
0|hoge|89x22|python3
1|kkk|89x24|python3
```

つまり、表示ロジック自体は `hoge` / `kkk` を描けている。

## 本質原因

### 一次原因

- wrapper は `uv run --no-sync` 前提で動く
- しかし実機の `.venv` は broken state で、`PyYAML` が実体として入っていなかった
- `uv sync --locked` が `Checked` だけで終了しても、この broken state が回復しないケースがあった
- そのため新しい runner が起動できなかった

### 二次原因

- `dashboard:0` を管理する古い `tmux_dashboard` プロセスが別経路で生き残っていた
- wrapper は「既存の別プロセスが同じ target を管理中か」を検知しない
- そのため、新しい実行と古い常駐実行が競合しうる
- さらに、残留 runner が「生きているように見えても実際には dashboard を構成できていない」状態を検知できていない可能性が高い

## 影響

- `./tmux-dashboard` 実行後も dashboard が plain shell のままに見える
- 一時的に正しい pane が出ても、古い runner が書き戻して再び崩れる
- 利用者には「表示が正しくない」「レイアウトが追随しない」ように見える

## 回復手順

### 環境修復

```bash
cd /srv/mount/tmux-dashboard
rm -rf .venv
uv sync --locked
```

### 既存干渉 runner の停止確認

```bash
ps -ef | rg 'python -m tmux_dashboard --window-target dashboard:0'
```

複数出ている場合は、意図した 1 つだけを残す必要がある。

### 表示確認

```bash
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_width}x#{pane_height}|#{pane_current_command}'
```

期待:

```text
0|hoge|...|python3
1|kkk|...|python3
```

## 推奨される恒久対策

1. wrapper 起動前に `yaml` などの critical import preflight を行い、失敗時は runner を起動せず明示エラーで止める  
2. `dashboard:0` を管理している既存 runner PID / command line を検知し、重複管理を拒否または置換する  
3. runner window の有無だけでなく、「同じ `window-target` を管理している既存プロセスの存在」を契約に含める  
