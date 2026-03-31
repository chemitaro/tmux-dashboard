# `window-size latest` への切り替え方法ガイド

- 作成日: 2026-03-31 (UTC)
- 対象: `tmux-dashboard` の `dashboard` window が `window-size manual` で固定され、外側 Terminal の resize に追随しない問題
- 前提: 推奨方針は `dashboard` target の `window-size` を `latest` に切り替えること

## 1. 結論

切り替えそのものは tmux の window option を `manual` から `latest` に変えるだけでよい。

最小の手動コマンドはこれである。

```bash
tmux set-window-option -t dashboard:0 window-size latest
```

短縮形ならこれでも同じである。

```bash
tmux setw -t dashboard:0 window-size latest
```

これにより、`dashboard:0` は「最後に active になった client のサイズ」を採用するようになる。  
その結果、いま見ている Terminal を広げたり狭めたりしたときに、内側の tmux window も追随しやすくなる。

## 2. なぜこれで直るのか

現在の問題は、`dashboard` window が `window-size manual` のため、tmux 自体が client のサイズ変化を window size へ反映していないことにある。

`latest` へ切り替えると、tmux は

- 最後に active になった client
- その client の現在サイズ

を基準に window size を決める。

このツールは `window_width` / `window_height` を見て layout を再計算するので、tmux 側の window size が更新されれば、アプリ側の再レイアウトも自然に追随する。

## 3. 今すぐ手動で切り替える方法

### 3.1 現在値の確認

```bash
tmux show-options -t dashboard:0 -w | rg '^window-size'
```

期待される現在値:

```text
window-size manual
```

### 3.2 `latest` へ変更

```bash
tmux set-window-option -t dashboard:0 window-size latest
```

### 3.3 変更確認

```bash
tmux show-options -t dashboard:0 -w | rg '^window-size'
```

期待結果:

```text
window-size latest
```

### 3.4 動作確認

1. `tmux-dashboard` を表示した Terminal window を広げる
2. 次を確認する

```bash
tmux display-message -p -t dashboard:0 '#{window_width} #{window_height} #{window_name}'
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_width}|#{pane_height}|#{pane_title}'
```

期待結果:

- `window_width` が外側 Terminal の resize に応じて変わる
- pane 幅 / 高さも追随して変わる

## 4. プロダクト側ではどう切り替えるべきか

手動コマンドだけでも応急処置にはなるが、製品修正としては自動化すべきである。

推奨は次の 2 段階である。

### 4.1 wrapper 起動時に保証する

`./tmux-dashboard` が visible dashboard window を確定した直後に、対象 window へ次を打つ。

```bash
tmux set-window-option -t "$dashboard_window_target" window-size latest
```

これで既存の `manual` 汚染が残っていても、起動時点で回復できる。

### 4.2 runner の preflight でも保証する

`run_once()` の前、または各 loop の preflight で対象 window の `window-size` を再確認し、`latest` でなければ戻す。

これにより、

- 利用者が途中で `manual` に戻した
- 別クライアントや別スクリプトが option を変更した
- 既存 session が古い状態のまま残っていた

といった drift から自己回復できる。

## 5. 既存 session の扱い

今回のように `dashboard` session がすでに存在していて、その window option が `manual` になっている場合でも、起動時に `latest` へ上書きすればよい。  
`kill-session` を強制する必要はない。

つまり移行方針はこうなる。

1. 新規 session: 作成直後に `latest` を設定
2. 既存 session: 起動時に `latest` を再設定
3. 実行中 drift: preflight で `latest` に戻す

## 6. 注意点

### 6.1 `latest` の意味

`latest` は「最後に active になった client のサイズを使う」という意味である。  
そのため、同じ `dashboard` session を複数 Terminal で同時に見ている場合、どの client を最後に触ったかで window size が変わる。

ただし今回の要件は「いま使っている Terminal の resize に追随してほしい」なので、`manual` や `smallest` より `latest` のほうが適している。

### 6.2 rollback

もし手元で元に戻したい場合は、次で `manual` に戻せる。

```bash
tmux set-window-option -t dashboard:0 window-size manual
```

ただし今回の問題は再発するため、通常は非推奨である。

## 7. ベストプラクティス

1. `dashboard` target の `window-size` はアプリが責任を持って管理する
2. 既定値は `latest` にする
3. 起動時だけでなく preflight でも保証する
4. 既存 `manual` 状態は自動回復する
5. 手動コマンドは補助策として残すが、主解決策は自動化する

## 8. 参考資料

- 比較資料: [window-size-manual-remediation-options-20260331.md](/srv/mount/tmux-dashboard/spec-lite/current/discussions/window-size-manual-remediation-options-20260331.md)
- 原因分析: [resize-follow-up-analysis-20260331.md](/srv/mount/tmux-dashboard/spec-lite/current/discussions/resize-follow-up-analysis-20260331.md)
- tmux wiki, Advanced Use / Window sizes: <https://github.com/tmux/tmux/wiki/Advanced-Use>
- tmux(1) man page, `window-size` option: <https://www.man7.org/linux/man-pages/man1/tmux.1.html>
