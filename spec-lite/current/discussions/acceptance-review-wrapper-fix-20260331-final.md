# wrapper create-window 修正 最終受け入れ検査レポート

- 実施日: 2026-03-31 (UTC)
- 対象コミット: `99d978b7b1bd8b817773bf8936db1ddc0f3d3bad`
- 比較基点: `954fa48 docs(spec-lite): 受け入れ改善の仕様を追補`
- 判定: `pass`

## 1. 対象と目的

本レポートは、S05 実装完了後の最終受け入れ検査結果である。  
前回の受け入れで `fail` となった 3 点を本当に閉じられたかを、Git 差分確認、コードレビュー、テスト実行、手動テストで再確認した。

前回 open だった 3 findings:

1. libtmux `swap_window()` / `kill_window()` の fail-closed 不足
2. create failure 後に ghost residual target が cleanup retry queue を汚染しうる
3. 0 セッション収束後に stale pane title が残る

## 2. Git 確認

### 2.1 実装コミット

- `99d978b fix(tmux): S05の失敗収束と受け入れ再判定を完了`

### 2.2 主な変更ファイル

- `tmux_dashboard/tmuxio.py`
- `tmux_dashboard/orchestrator.py`
- `tests/test_tmuxio.py`
- `tests/test_orchestrator.py`
- `tests/test_e2e_tmux.py`
- `spec-lite/current/discussions/acceptance-review-wrapper-fix-20260331-s05-rereview.md`

## 3. 差分レビュー結果

### 3.1 main-agent コードレビュー

差分の核心部を確認した結果、前回の fail 3 点に対して次の修正が入っていることを確認した。

- `tmux_dashboard/tmuxio.py`
  - `LibtmuxDriver.swap_window()` が `_raise_if_cmd_failed()` を通る
  - `LibtmuxDriver.kill_window()` が `_raise_if_cmd_failed()` を通る
- `tmux_dashboard/orchestrator.py`
  - `_window_exists()` を追加し、create failure 時は staging target 実在確認後にだけ cleanup / residual 登録を行う
  - `_clear_single_pane_title()` を追加し、0 セッション short-circuit 後に空 title へ戻す
- `tests/test_tmuxio.py`
  - libtmux `swap_window()` / `kill_window()` failure の回帰テストを追加
- `tests/test_orchestrator.py`
  - missing staging target 非 enqueue
  - 0 セッション stale title 解消
- `tests/test_e2e_tmux.py`
  - direct runner の zero-session title cleanup
  - wrapper path の zero-session title cleanup

### 3.2 QA review

- reviewer: `qa_reviewer`
- 結果: `pass`
- 要旨:
  - 前回 fail だった 3 点は、追加された unit/E2E で直接検証されている
  - CLI entrypoint 回帰も既存防御線と wrapper zero-session E2E でカバーされている
  - 残存リスクは tmux 実行環境依存のスモーク領域に限定される

## 4. 自動テスト結果

### 4.1 実行コマンド

```bash
uv run pytest -q
```

### 4.2 結果

```text
104 passed in 4.95s
```

## 5. 手動テスト結果

### 5.1 ケース A: direct runner / same-name session-window

#### 手順

```bash
tmux kill-server || true
tmux new-session -d -s dashboard -n dashboard 'sleep 300'
tmux new-session -d -s alpha 'sleep 300'
tmux new-session -d -s beta 'sleep 300'
tmux new-session -d -s gamma 'sleep 300'
uv run python -m tmux_dashboard --config <libtmux config> --window-target dashboard:0 --once --iterations 1
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}|#{pane_left}|#{pane_top}|#{pane_width}|#{pane_height}'
```

#### 観測結果

- `dashboard:0` は 3 pane に分割された
- pane title は `alpha`, `beta`, `gamma`
- same-name 条件でも root cause は再現しなかった

#### 判定

- `pass`

### 5.2 ケース B: wrapper 経路で 0 セッション収束

#### 手順

```bash
tmux kill-server || true
tmux new-session -d -s alpha
tmux new-session -d -s beta
./tmux-dashboard --config <libtmux config>
tmux kill-session -t alpha
tmux kill-session -t beta
tmux list-panes -t dashboard:0 -F '#{pane_index}|#{pane_title}'
```

#### 観測結果

- wrapper 起動直後は `0|alpha`, `1|beta`
- 全対象セッション削除後は `0|`
- つまり `dashboard:0` は 1 pane かつ空 title に収束した

#### 判定

- `pass`

### 5.3 補足観測

- 非 TTY で wrapper を直接叩くと、最終 attach の都合で `open terminal failed: not a terminal` により wrapper 自体は exit `1` になる
- ただし provisioning と dashboard 再構成は成功していた
- これは前回同様、今回の修正対象外であり、受け入れ結果には影響させていない

## 6. 前回 fail 3 点の再判定

### 6.1 libtmux `swap_window()` / `kill_window()` fail-closed

- 結果: `closed`
- 根拠:
  - `tmux_dashboard/tmuxio.py` で `_raise_if_cmd_failed()` を適用
  - `tests/test_tmuxio.py` に回帰追加

### 6.2 ghost residual target

- 結果: `closed`
- 根拠:
  - `tmux_dashboard/orchestrator.py` で `_window_exists()` による存在確認を追加
  - missing target 非 enqueue の unit test 追加

### 6.3 0 セッション stale pane title

- 結果: `closed`
- 根拠:
  - `_clear_single_pane_title()` の追加
  - unit test / direct E2E / wrapper path 手動検証で確認

## 7. 総合判定

- 受け入れ判定: `pass`

## 8. 残存リスク

- tmux 実行環境依存の一時的不安定さ
- wrapper の非 TTY attach 挙動

いずれも今回の S05 スコープ外、または今回の fail 3 点とは独立のため、受け入れを止める理由にはしない。
