# `window-size manual` 解消策の比較とベストプラクティス

- 実施日: 2026-03-31 (UTC)
- 対象: `tmux-dashboard` の「外側 Terminal を広げても内側 dashboard window が追随しない」問題
- 前提: 原因は `dashboard` session/window が `window-size manual` で固定され、tmux 自体が client サイズへ自動追随していないこと

## 1. 結論

推奨案は次の組み合わせである。

1. wrapper / runner 起動時に `dashboard` target の `window-size` を `latest` へ明示設定する
2. 起動時だけでなく、各 loop の preflight でも `latest` を保証する
3. 既存の `manual` session に対しては、起動時に自動で `latest` へ移行する
4. `resize-window` を主解決策にはしない

この方針が最も小さい責務追加で、今回の不具合に直接効き、既存の `manual` 汚染も自動回復できる。

## 2. 比較対象

比較した案は次の 6 つである。

1. wrapper / runner で `window-size latest` を明示設定
2. wrapper / runner で `window-size smallest` を明示設定
3. wrapper / runner で `window-size largest` を明示設定
4. `manual` のまま `resize-window` を明示実行
5. 起動時のみ設定変更
6. 毎ループ保証

## 3. 各案の評価

### 3.1 `window-size latest`

#### 何をするか

`dashboard` target に対して `set-window-option -w window-size latest` を明示する。

#### 利点

- 「今見ている client のサイズに追随する」という期待に最も近い
- 外側 Terminal の resize に対して自然に追随しやすい
- tmux 標準の window-size policy を使うため、実装責務が小さい
- Python 側のレイアウト計算を変更せずに済む

#### 欠点

- 同一 session を複数 client で同時に見ている場合、最後に active になった client に window size が寄る
- 2 client を同時に監視用途で開く運用では、どちらを基準にするかが利用者体験に依存する

#### 評価

最有力。  
今回の症状は「いま開いている Terminal のサイズへ追随しない」ことなので、`latest` が最も要件に合う。

### 3.2 `window-size smallest`

#### 何をするか

`dashboard` target に対して `window-size smallest` を明示する。

#### 利点

- 小さい client でも常に全体が収まる
- multi-client 運用で「見切れ」を避けやすい

#### 欠点

- 大きい Terminal を使っても dashboard は広がらない
- 今回の症状と見え方がかなり近く、利用者には「追随しない」と見えやすい
- unused space が出やすい

#### 評価

非推奨。  
今回の不具合の再発形に近く、UX 的に逆方向。

### 3.3 `window-size largest`

#### 何をするか

`dashboard` target に対して `window-size largest` を明示する。

#### 利点

- 大きい client を最大限活かせる
- dashboard を広く見せたい用途には向く

#### 欠点

- 小さい client では見切れやスクロールが増える
- multi-client で「どの client でも見やすい」を保証しにくい

#### 評価

限定用途ではありだが、一般既定値には向かない。  
dashboard は観測面が強く、複数端末で開かれる可能性があるため、`largest` は攻めすぎる。

### 3.4 `manual` のまま `resize-window` を明示実行

#### 何をするか

`window-size manual` は維持しつつ、wrapper / runner が `resize-window -x ... -y ...` を打って dashboard window の大きさを都度更新する。

#### 利点

- tmux option を触らずに挙動制御できる
- 「この window だけ特別にサイズを固定しつつ更新する」という実装は可能

#### 欠点

- 誰の client サイズを基準に `resize-window` するかをアプリ側で決める必要がある
- multi-client 時に責務が一気に複雑になる
- tmux の標準 policy を再実装する方向に寄る
- resize race や target 解決失敗時の例外設計が増える

#### 評価

主解決策としては非推奨。  
`window-size` policy で解ける問題を Python 側で再実装するのはコストに対して得るものが少ない。

## 4. 起動時のみ設定変更 vs 毎ループ保証

### 4.1 起動時のみ

#### 利点

- 実装が単純
- tmux option を一度直すだけなので副作用が少ない

#### 欠点

- 実行中に利用者や別 client が `window-size manual` に戻した場合に再発する
- 既存 runner の温存や stale session の影響を受けやすい

#### 評価

単独では弱い。  
初回移行には必要だが、再発防止としては不足。

### 4.2 毎ループ保証

#### 利点

- drift に強い
- 既存 manual 汚染が残っていても自然回復する
- runner の責務として「dashboard window の可変性を維持する」を明確にできる

#### 欠点

- 毎ループで option を触る設計になる
- 明示的に manual を望む利用者がいた場合は上書きしてしまう

#### 評価

推奨。  
ただし「dashboard target は本ツール管理下なので window-size はツールが責任を持って `latest` に保つ」という要件を明文化する前提。

## 5. 既存 `manual` session の移行戦略

### 5.1 自動移行

#### 何をするか

起動時または preflight で、対象 `dashboard` window が `manual` なら `latest` に変更する。

#### 利点

- 既存利用者が `kill-session` しなくても回復する
- サポートコストが低い

#### 欠点

- 既存環境に対する挙動変更になる

#### 評価

推奨。  
今回の不具合は既存状態の汚染を含むので、自己回復を入れるべき。

### 5.2 手動移行だけに任せる

#### 何をするか

README や案内で `tmux setw -t dashboard:0 window-size latest` を手動実行してもらう。

#### 利点

- 実装変更が最小

#### 欠点

- 再発しやすい
- サポート依存になる
- 利用者体験が悪い

#### 評価

非推奨。  
回復策としては使えるが、製品側の解決にはならない。

## 6. 推奨案

### 6.1 採用案

次を採用するのが最も妥当である。

1. wrapper / runner が対象 `dashboard` window の `window-size` を `latest` に明示設定する
2. この保証は起動時だけでなく、loop の preflight でも行う
3. 既存 `manual` は自動移行する

### 6.2 この案を推す理由

- 今回の根本原因に直接効く
- tmux 標準機能を使うため、アプリ側の独自制御が最小
- 既存の `manual` 汚染を自動回復できる
- 画面リサイズ追随という利用者期待に最も近い

## 7. 非推奨案

### 7.1 `smallest`

- 大きい Terminal を使っても広がらず、今回の不満を再生産しやすい

### 7.2 `manual + resize-window`

- 責務が重く、tmux policy の再実装になる

### 7.3 手動移行のみ

- 製品修正ではなく運用回避に留まる

## 8. 採用判断基準

次の基準で判断するのがよい。

1. いま見ている Terminal のサイズに自然追随するか
2. multi-client 環境で再発しにくいか
3. 既存の `manual` 汚染を自動回復できるか
4. tmux 標準機能を優先し、アプリ固有ロジックを増やしすぎないか
5. 既存の wrapper / runner 構造へ小さく安全に組み込めるか

この基準では、`latest` を wrapper / runner が保証する案が最もバランスがよい。

## 9. ベストプラクティス

1. dashboard の window-size policy はアプリが明示管理する
2. 管理値は `latest` を既定とする
3. layout 計算前の preflight で policy drift を是正する
4. 既存 `manual` session は自動移行して回復可能にする
5. multi-client での期待挙動を requirement / design に明記する
6. 手動回避コマンドは補助策として文書化するが、主解決策にはしない

## 10. 参考資料

- tmux wiki, Advanced Use / Window sizes: <https://github.com/tmux/tmux/wiki/Advanced-Use>
- tmux(1) man page, `window-size` option: <https://www.man7.org/linux/man-pages/man1/tmux.1.html>
