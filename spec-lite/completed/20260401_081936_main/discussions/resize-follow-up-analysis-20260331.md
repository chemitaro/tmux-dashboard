# ウィンドウリサイズ追随不良の分析レポート

- 実施日: 2026-03-31 (UTC)
- 対象: ローカル実行時に「ウィンドウサイズを変更してもペインレイアウトが追随しない」症状
- 判定: repo 現行コードでは単純な resize 不良は再現せず。ユーザー実機では `dashboard` session の multi-client window-size 決定が本命

## 1. 結論

現行の `main` ブランチにある repo コードでは、ウィンドウサイズ変更に対してレイアウト再計算は動作した。  
そのため、少なくとも「今の repo の resize 追随ロジックが全面的に壊れている」とは判断しない。

追加でユーザー実機の tmux 状態と repo の設定ファイルを確認した結果、今回の主要因はさらに絞れた。

```text
dashboard|2|2
spec-dock-3f57db443e05-copilot-sandbox|2|1
spec-dock-codex-sandbox|1|1
tmux-dashboard-codex-sandbox|1|1
```

```text
0|spec-dock-3f57db443e05-copilot-sandbox|95|47
1|spec-dock-codex-sandbox|95|49
2|tmux-dashboard-codex-sandbox|95|97
```

この出力は、`dashboard:0` が `dashboard` 以外の tmux session 全体を pane 化していることを直接示している。  
ユーザーからは「dashboard 以外の全 session を表示する」が仕様だと明示されたため、これは不具合ではなく期待どおりの挙動である。

さらに repo 内の実際の設定ファイルを確認すると、プロジェクト設定 `configs/dashboard.yaml` には次が入っている。

```yaml
min_tile_width: 65
```

これは `configs/dashboard.example.yaml` の `40` とは異なる。

設定の優先順位は

1. `--config`
2. `configs/dashboard.yaml`
3. `~/.config/tmux-dashboard/config.yaml`
4. 組み込みデフォルト

なので、明示指定がなければ現行 repo は `min_tile_width: 65` を使う。

実際、列数計算は `floor(window_width / min_tile_width)` なので、

- 幅 `191`
- `min_tile_width = 65`
- session 数 `3`

なら

```text
floor(191 / 65) = 2
columns = min(3, 2) = 2
rows = ceil(3 / 2) = 2
```

となり、あなたの実機で見えている

- 左列 2 pane
- 右列 1 pane
- 各 pane 幅がおおむね `95`

という観測と完全に一致する。

さらにユーザー実機から、次の追加証跡が得られた。

```text
tmux display-message -p -t dashboard:0 '#{window_width} #{window_height} #{window_name}'
191 98 python3.12

tmux list-windows -t dashboard -F '#{window_index}|#{window_name}|#{window_active}'
0|python3.12|1
1|__tmux_dashboard_runner__|0
```

加えて、ユーザー提供のスクリーンショット `spec-lite/current/discussions/スクリーンショット 2026-03-31 16.39.34.png` では、

- 外側の Terminal window は広くなっている
- しかし内側の `dashboard:0` はそれより狭い幅のまま残っている
- 右側の余剰領域が `·` に相当するドット状背景で埋まっている

という見え方になっている。

この「外側 client は広いのに、tmux window 自体は狭いままで、余白がドットで埋まる」という症状は、tmux の multi-client window-size policy と一致する。  
さらにユーザー実機で次が確認できた。

```text
tmux show-options -t dashboard -w | rg 'window-size|aggressive-resize'
window-size manual

tmux list-clients -t dashboard -F '#{client_tty}|#{client_width}x#{client_height}|#{session_name}'
/dev/ttys019|266x99|dashboard
/dev/ttys026|278x99|dashboard
```

つまり `dashboard` session には十分大きい 2 client が attached しているにもかかわらず、window option が `manual` のため、`dashboard:0` の size は client 幅へ自動追随しない。  
この時点で、今回のクリティカルな本質原因は「tmux の `window-size manual` により dashboard window のサイズが固定化されていること」と判断できる。

現時点で最も有力な本質原因候補は次の順序である。

1. `dashboard` session の window option が `window-size manual` になっており、tmux 自体が client サイズに追随しない
2. `dashboard` session に複数 client が attached しており、manual 設定の固定サイズ問題が視覚的に顕在化している
3. `LibtmuxDriver.window_size()` が fail-open で、target 解決失敗時に `(0, 0)` を返しうる
4. wrapper が既存 runner を温存しすぎており、古い runner が残っている
5. 実行している `tmux-dashboard` コマンドが別 install / 別 symlink を向いている

`min_tile_width: 65` は 2 列レイアウト自体の説明には有効だが、「外側 Terminal を広げても内側 tmux window 幅が変わらない」ことの主因ではない。  
主因は、tmux がそもそも `dashboard:0` の window size を現在の visible client に追随させていない可能性が高い。

## 2. コード上の resize 追随経路

### 2.1 main loop は毎回 `run_once()` を呼ぶ

`tmux_dashboard.__main__.py` の通常ループは、毎サイクル `orch.run_once(window_target=...)` を実行し、その後 `poll_interval_sec` だけ sleep する。

- 参照: [__main__.py](/srv/mount/tmux-dashboard/tmux_dashboard/__main__.py#L72)

つまり、常駐 runner が生きている限り、ウィンドウサイズ変化は次のサイクルで再評価される設計である。

### 2.2 `run_once()` は window size から plan を再計算する

`tmux_dashboard.orchestrator.Orchestrator.run_once()` は毎サイクル `window_size()` を取得し、その値から `compute_plan()` を通して `columns`, `rows` を再計算する。  
レイアウト差分判定に使う signature も `(columns, rows, sessions)` なので、幅変更で列数や行数が変われば再レイアウト条件になる。

- 参照: [orchestrator.py](/srv/mount/tmux-dashboard/tmux_dashboard/orchestrator.py#L303)
- 参照: [orchestrator.py](/srv/mount/tmux-dashboard/tmux_dashboard/orchestrator.py#L344)

### 2.3 resize 回帰テストも存在し、通過している

E2E には resize 用の回帰テストがあり、今回の実行でも全体テストは green だった。

- 参照: [test_e2e_tmux.py](/srv/mount/tmux-dashboard/tests/test_e2e_tmux.py#L213)
- 参照: [test_e2e_tmux.py](/srv/mount/tmux-dashboard/tests/test_e2e_tmux.py#L297)

## 3. こちらでの再現検証

### 3.1 direct runner ループ

以下の条件で direct runner を常駐させた。

- `dashboard` session / `dashboard` window を作成
- `alpha`, `beta`, `gamma` session を作成
- `uv run python -m tmux_dashboard --config <cfg> --window-target dashboard:0` をループ実行
- 実行中に `tmux resize-window` で幅を変更

観測結果:

- 初期: `39 | 39 | 40`
- 幅 `79` 後: `79 | 79 | 79`
- 幅 `160` 後: `53 | 53 | 52`

この結果から、少なくともこちらの環境では resize 後に plan 再計算とレイアウト再適用が起きている。

### 3.2 wrapper 経路

`./tmux-dashboard` 経路でも同様に確認した。

観測結果:

- 初期: `39 | 39 | 40`
- 幅 `79` 後: `79 | 79 | 79`
- 幅 `160` 後: `53 | 53 | 52`

つまり wrapper 経路でも、repo 現行コードでは resize 追随は再現した。

## 4. 本命原因候補

### 4.1 stale runner が最有力

wrapper スクリプトは、既存 runner pane のプロセス引数に `tmux_dashboard` が含まれていれば respawn しない。

- 参照: [tmux-dashboard](/srv/mount/tmux-dashboard/tmux-dashboard#L174)

このため、以前から動き続けている古い runner がいる場合、

- repo のコードを更新しても
- `make install` や `uv sync --locked` をやっても

既存 runner 自体はそのまま生き続ける。  
その結果、「手元では古いコードが動き続けていて、新しい resize 挙動になっていない」ことが起こりうる。

### 4.2 別 install / 別 symlink

`make install` は `/usr/local/bin/tmux-dashboard` を repo の `./tmux-dashboard` へ symlink するだけである。  
したがって、ローカルで実行している `tmux-dashboard` が別の repo や古い場所を向いていると、こちらで見ているコードとは別物が動く。

### 4.3 `--once` 実行

`--once` は単発実行なので、resize 後の追随は自動では起きない。  
resize 追随を確認するには、wrapper 常駐か direct runner の通常ループが必要である。

### 4.4 「全 session を数える」は仕様どおりで、今回の主因ではない

ユーザーは「dashboard 以外の全 session を表示する」が仕様であると明言した。  
そのため、`Orchestrator.scan_sessions()` が `dashboard` 以外の全 session を対象にしていること自体は設計どおりであり、今回の不具合の主因から外す。

- 参照: [orchestrator.py](/srv/mount/tmux-dashboard/tmux_dashboard/orchestrator.py#L49)

今回の `list-panes` 出力で sandbox 系 session 名が pane title として並んでいるのは、むしろ「session 選定は仕様どおりに動いている」証拠である。

### 4.5 `min_tile_width` の期待値と実値がズレている

今回の調査で見つかった最も説明力の高い事実は、repo の現行プロジェクト設定 `configs/dashboard.yaml` が `min_tile_width: 65` であることだ。

- 参照: `configs/dashboard.yaml`
- 対照: `configs/dashboard.example.yaml` は `40`

この差により、ユーザーやテストで想定していた「幅 191 なら 3 列に近いはず」という直感は成立しない。  
実際には `191 // 65 = 2` なので、2 列レイアウトになる。

つまり少なくとも今回の観測の一部は、

- 幅追随不良

ではなく

- 現行設定に対して正しいレイアウト結果

である可能性が高い。

### 4.6 `dashboard` session に複数 client が attached しており、しかも `window-size manual` で固定されている

ユーザー実機では `tmux list-sessions` が次を返している。

```text
dashboard|2|2
```

つまり `dashboard` session には 2 つの attached client がいる。

tmux の window size は attached client 群から決まり、`window-size` オプションにより

- `largest`
- `smallest`
- `latest`
- `manual`

のどれを使うかが変わる。tmux wiki の説明では、

- `smallest`: 大きい client 側では unused space が `·` で埋まる
- `latest`: 最も最近使われた client のサイズを使う

となる。

今回のスクリーンショットで「外側 Terminal を広げても、内側 dashboard の実サイズは固定のままで、余った領域が `·` で埋まる」なら、tmux が

- 他の attached client のサイズ
- または `smallest` / `latest` の policy

に従って `dashboard:0` の window size を決めている可能性が非常に高い。

しかし今回は policy 候補のさらに上位で、実機が `window-size manual` を返している。  
`manual` では tmux は client attach や outer terminal resize に合わせて window size を更新しないため、プロダクトの Python 側は `window_width` を見て正しく計算していても、その `window_width` 自体が古い固定値のままになりうる。

今回のスクリーンショットはまさにこのパターンと一致する。  
外側 Terminal の余白は tmux pane ではなく、tmux が「この client は大きいが、window 自体は別サイズで描画する」と決めたときの unused space とみるのが自然である。

## 6. 現時点での本質原因の整理

ここまでの調査から、今回のクリティカルな本質原因候補は次のように整理できる。

1. ダッシュボード側のレイアウト計算は動いている
2. 2 列 1+2 構成は `min_tile_width: 65` に照らして正しい
3. それでも「外側を広げても内側が広がらない」症状が残る
4. その症状は `dashboard` session に 2 client が attached している事実、`window-size manual`、そしてスクリーンショットの unused space の見え方で強く説明できる

したがって、今回まず疑うべきは Python 側の列数計算ではなく、tmux session/window 側の固定サイズ設定である。

## 7. 追加で確定させるべき確認項目

本質原因の確定に必要だった確認は完了した。  
実機では `window-size manual` が確認され、attached client も十分大きいことが確認できたため、「client が小さいからではなく、manual だから固定化している」という説明が成立した。

今後の修正検討では、少なくとも次の論点を設計対象に含める必要がある。

1. wrapper / runner が `dashboard` window を自動追随させたいなら `window-size` を `latest` か `smallest` に明示するか
2. あるいは `resize-window` を明示的に打って manual state を更新するか
3. 既存の `dashboard` session が manual のまま残っている場合の移行・回復手順をどうするか

## 8. 参考資料

- tmux wiki, Advanced Use / Window sizes: <https://github.com/tmux/tmux/wiki/Advanced-Use>
- tmux(1) man page, `window-size` option: <https://www.man7.org/linux/man-pages/man1/tmux.1.html>

## 5. 補助的に見つかった事項

`Config.poll_interval_sec` は dataclass でも `_from_dict()` でも `int` 扱いなので、`0.5` のような値は `0` に丸められる。

- 参照: [config.py](/srv/mount/tmux-dashboard/tmux_dashboard/config.py#L58)
- 参照: [config.py](/srv/mount/tmux-dashboard/tmux_dashboard/config.py#L97)

これは今回の「追随しない」症状の主因ではなく、むしろ逆に busy loop を起こしやすい方向の挙動である。  
ただし設定解釈としては注意点なので、将来的な改善候補ではある。

## 6. 現時点の分析判断

### 6.1 いま言えること

- repo 現行コードの resize 追随ロジック自体は動作している
- こちらの環境では direct runner / wrapper の両方で追随を確認した
- したがって、問題はローカル実行経路差である可能性が高い

### 6.2 優先度順の原因候補

1. `dashboard` session に複数 client が attached しており、tmux の `window-size` policy が現在の client 幅を採用していない
2. 実装が `dashboard` 以外の全 session を対象にしており、sandbox 系 session まで pane 対象にしている
3. `configs/dashboard.yaml` の `min_tile_width: 65` により、期待列数より少ない列数が正しく計算されている
4. stale runner が古いコードのまま動いている
5. 実行中の `tmux-dashboard` が別 install / 別 symlink を向いている
6. `--once` など常駐しない起動方法で確認している
7. tmux クライアント / サーバ側のローカル環境依存差

## 7. 次に確認すべきポイント

ローカル側で次を確認すると、原因の切り分けが進む。

```bash
which tmux-dashboard
ls -l "$(which tmux-dashboard)"
tmux list-sessions -F '#{session_name}|#{session_attached}|#{session_windows}'
tmux list-windows -t dashboard -F '#{window_index}|#{window_name}|#{window_active}'
tmux display-message -p -t dashboard:1.0 '#{pane_pid}'
ps -p "$(tmux display-message -p -t dashboard:1.0 '#{pane_pid}')" -o args=
```

特に最後の `ps` で、runner pane が今の repo の Python / uv 実行かどうかを見るのが重要である。
また、`list-sessions` で detached session が多く残っていれば、「幅追随していない」のではなく「対象数が多すぎて見え方が悪い」可能性が高い。

今回のユーザー実機出力では、すでに pane title と session 名が一致しているため、「対象数が多すぎる」仮説はかなり強く支持されている。

## 8. 推奨アクション

1. 仕様として「全 session を出す」が正しいのか、「attached / active な session だけを出したい」のかを決める
2. `dashboard` session の `window-size` / `aggressive-resize` を実機で確認する
3. `tmux list-clients -t dashboard -F '#{client_tty}|#{client_width}x#{client_height}|#{session_name}'` で、どの client が attached しているかを確認する
4. 現行設定 `configs/dashboard.yaml` の `min_tile_width: 65` を採用し続けるのか、`40` などへ戻すのかを決める
5. 必要なら sandbox 系 session を `exclude_patterns` で除外して意図どおりの pane 数になるか確認する
6. 既存 `dashboard` session を完全停止してから起動し直す
7. `which tmux-dashboard` と symlink 先を確認する
さらにユーザーのスクリーンショットでは、右側の未使用領域が `·` で埋まっていた。  
これは tmux の複数 client / window-size 方針における典型的な見え方と一致する。tmux wiki では、window size は attached client 群から決まり、`window-size=smallest` の場合は「大きい client 側では unused space が `·` で埋まる」と説明されている。

- 参照: tmux wiki “Window sizes” <https://github.com/tmux/tmux/wiki/Advanced-Use>
- 参照: tmux man page `window-size largest | smallest | manual | latest` <https://www.man7.org/linux/man-pages/man1/tmux.1.html>
