---
種別: 調査メモ
機能ID: "fix-tmux-headless-layout"
機能名: "wrapper visible window duplication analysis"
関連Issue: ["wrapper 実行後に dashboard window が増殖する", "visible dashboard window 名が消える"]
作成者: "codex"
作成日: "2026-04-01"
---

# wrapper visible window duplication analysis

## 結論

手動確認で見えた副作用の一次原因は、`swap-window` の後に visible dashboard window の **window 名が `dashboard` のまま維持されていない** ことだった。  
staging window は `new-window` 時に名前を付けていないため、tmux の既定 window 名 `python3.12` を持つ。`swap-window` は pane 構造だけでなく **window 名も丸ごと交換** するため、昇格後の visible window は `dashboard` ではなく `python3.12` になる。

その結果、次回の wrapper 起動時に [tmux-dashboard](/Users/iwasawayuuta/workspace/tools/tmux-dashboard/tmux-dashboard#L160) が `window_name == dashboard` を見つけられず、新しい visible dashboard window を追加作成する。これが `dashboard:0`, `dashboard:1` のような重複 window を生む本質原因である。

## 手動確認で観測した事実

### 1. wrapper 起動直後に dashboard session へ 3 window が存在した

```bash
tmux list-windows -t dashboard -F '#{window_index}|#{window_name}|#{window_active}|#{window_width}x#{window_height}|#{window_panes}'
```

観測結果:

```text
0|python3.12|1|80x24|3
1|python3.12|0|80x24|3
2|__tmux_dashboard_runner__|0|80x24|1
```

本来期待する構成は:

- visible dashboard window: 1 つ
- runner window: 1 つ

なので、`python3.12` が 2 つ残るのは異常。

### 2. runner は `dashboard:1` を管理対象としていた

```bash
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index}|#{window_name}|#{pane_title}|#{pane_current_command}|#{pane_dead}|#{pane_start_command}'
```

観測結果の要点:

```text
dashboard:0.* | window_name=python3.12 | alpha/beta/gamma
dashboard:1.* | window_name=python3.12 | alpha/beta/gamma
dashboard:2.0 | window_name=__tmux_dashboard_runner__ | pane_start_command=... --window-target dashboard:1
```

つまり runner は visible target として `dashboard:1` を見ており、`dashboard:0` は前回の遺物として残っていた。

### 3. session 削除と resize は `dashboard:1` 側に追随した

`gamma` session を kill したあと:

```text
dashboard:0 -> alpha, beta
dashboard:1 -> alpha, beta
```

さらに:

```bash
tmux resize-window -t dashboard:1 -x 120 -y 30
tmux display-message -p -t dashboard:1 '#{window_width}x#{window_height}'
tmux list-panes -t dashboard:1 -F '#{pane_index}|#{pane_title}|#{pane_width}x#{pane_height}'
```

観測結果:

```text
120x30
0|alpha|120x13
1|beta|120x15
```

runner log でも:

```text
updated window-size policy: window_target=dashboard:1 from=manual to=latest
detected: sessions=['alpha', 'beta'], window=120x30
```

となっており、runner の管理対象は `dashboard:1` で固定されていた。

## コード上の因果関係

### A. wrapper は visible window を名前 `dashboard` で探索している

[tmux-dashboard](/Users/iwasawayuuta/workspace/tools/tmux-dashboard/tmux-dashboard#L160) は次で visible dashboard window を探す。

```bash
tmux list-windows -t "$SESSION_NAME" -F "#{window_index}|#{window_name}" \
  | awk -F '|' -v name="$DASHBOARD_WINDOW_NAME" '$2==name{print $1; exit}'
```

ここで `window_name == dashboard` が見つからなければ、[tmux-dashboard](/Users/iwasawayuuta/workspace/tools/tmux-dashboard/tmux-dashboard#L170) が新しい visible window を作る。

### B. staging window には `dashboard` という名前を付けていない

[tmux_dashboard/tmuxio.py](/Users/iwasawayuuta/workspace/tools/tmux-dashboard/tmux_dashboard/tmuxio.py#L366) の `create_window()` は `tmux new-window -P ... -t dashboard:<index>` を呼ぶが、`-n dashboard` を付けていない。

そのため staging window は shell / Python の既定名、今回の観測では `python3.12` になる。

### C. orchestrator は `swap-window` 後に window 名を戻していない

[tmux_dashboard/orchestrator.py](/Users/iwasawayuuta/workspace/tools/tmux-dashboard/tmux_dashboard/orchestrator.py#L439) は staging target を `swap-window` で本番 target と入れ替える。

```python
self.io.swap_window(staging_target, window_target)
```

しかしその後に:

- visible target の window 名を `dashboard` に戻す
- residual old window の window 名を無害化する

のどちらも実施していない。

tmux は `swap-window` で window 名も交換するため、**本番 target が staging 側の `python3.12` を受け取る**。  
次回 wrapper 起動時、visible window 探索は失敗し、新しい `dashboard` window を追加する。

## 本質原因

一次原因:

- non-destructive apply の staging window に visible dashboard と同じ命名契約を持たせていない

二次原因:

- wrapper が visible dashboard window を index ではなく `window_name == dashboard` で識別している
- swap 後に visible target の名前を invariant として再設定していない

## 影響

- wrapper 再起動のたびに `dashboard` session 内へ追加 window が増える
- runner が `dashboard:1` やそれ以降の別 index を管理対象にし始める
- 利用者視点では「dashboard は動くが window 構成が増殖する」「どの window が本物かわからない」状態になる
- `__tmux_dashboard_runner__` の隣に不要な tiled window が残り、将来的に cleanup 失敗や target 誤認の温床になる

## 再現手順

1. `alpha`, `beta`, `gamma` の tmux session を作る
2. `./tmux-dashboard` を tmux 内で起動する
3. `tmux list-windows -t dashboard -F '#{window_index}|#{window_name}|#{window_active}'` を見る
4. `python3.12` named window が 2 つと `__tmux_dashboard_runner__` が見える
5. `tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index}|#{window_name}|#{pane_start_command}'` を見る
6. runner が `--window-target dashboard:1` を持つことを確認する

## ベストプラクティス

### 必須

1. staging window に visible window と同じ命名契約を持たせない
2. `swap-window` 後に visible target の window 名を `dashboard` へ明示的に戻す
3. wrapper は visible dashboard window の識別を「名前だけ」に依存しない

### 実装方針として有力な順

#### 方案A: swap 後に visible target を rename する

- `create_window()` は現状維持
- `swap-window` 成功直後に `rename-window -t window_target dashboard` を実行する
- あわせて cleanup 対象になった old window へは任意の一時名を付けてもよい

利点:

- 変更範囲が最小
- wrapper と orchestrator の契約が揃う

注意:

- `swap-window` 後にどちらの target が old/new になるかを driver 契約として明文化する必要がある

#### 方案B: staging window を最初から一時名で作り、swap 後に visible 名を再付与する

- 例: `__tmux_dashboard_staging__<index>`
- staging であることが `list-windows` 上でも判別しやすい

利点:

- 調査容易性が高い
- `python3.12` のような accidental name を排除できる

注意:

- rename 処理は結局必要

#### 方案C: wrapper が active visible target を別手段で覚える

- 例: session option / window option / dedicated marker

利点:

- 名前依存を弱められる

注意:

- 現状の責務より重い
- まずは rename invariant の方が単純で安全

## 推奨

現時点の最適解は **方案A + B の併用**。

- staging window は明示的な一時名で作る
- `swap-window` 後は visible target を必ず `dashboard` に rename する
- wrapper は `dashboard` 名探索を維持してよいが、その invariant を orchestrator 側で保証する

これにより:

- visible window は常に 1 つ
- runner target は常にその visible window
- wrapper 再起動で window が増殖しない

という運用契約に戻せる。
