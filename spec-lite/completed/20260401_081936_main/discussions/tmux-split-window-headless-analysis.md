# tmux split-window headless analysis

## 目的
- `tmux-dashboard` が機能しない原因を、実測・コード調査・外部調査を統合して記録する。
- 旧 `planning/` ベースの調査成果を、`spec-lite` 運用へ移行する際の参照正本として残す。

## 結論サマリー
- 主因は、現行実装が `tmux split-window -p <percent>` に依存していること。
- `tmux 3.4` の detached / headless 条件では、この `-p` 分割が `size missing` で失敗する。
- 一方で `split-window -l 40` や `split-window -l 50%` は同条件でも成功した。
- したがって「headless tmux 全体が非対応」ではなく、「`-p` ベース分割戦略が現在の tmux 挙動と噛み合っていない」がより正確な診断である。

## 調査対象
- 対象コマンド:
  - `tmux new-session`
  - `tmux split-window`
  - `tmux resize-window`
- 対象コード:
  - `tmux_dashboard/tmuxio.py`
  - `tmux_dashboard/orchestrator.py`
  - `tmux_dashboard/session_manager.py`
  - `tests/test_e2e_tmux.py`
  - `tests/test_tmuxio.py`

## 実測結果

### 1. 現行ツール実行時の観測
```bash
uv run python -m tmux_dashboard --once --iterations 1
```

観測要点:
- `sessions=['alpha', 'beta']` を検出しても、dashboard 側は 1 pane のまま止まるケースがある
- 初回は `Pane integrity check failed` の警告が出やすい

### 2. `-p` と `-l` の比較
実験条件:
- `tmux 3.4`
- `TERM=screen-256color`
- detached session
- `new-session -d -x 120 -y 40 -s dashboard 'sh -lc "sleep 300"'`

#### `-p` は失敗
```bash
tmux split-window -h -p 50 -t dashboard:0
# => size missing
```

#### `-l` は成功
```bash
tmux split-window -h -l 40 -t dashboard:0
tmux split-window -h -l 50% -t dashboard:0
# => success
```

#### pane id target + `-l` も成功
```bash
tmux split-window -h -l 50% -t %0
tmux split-window -v -l 50% -t %0
# => success
```

## コード上の原因

### 1. 分割I/O が `-p` 固定
- `CliDriver.split_window()` は `split-window ... -p ...` を使う
- `CliDriver.split_pane()` も `split-window ... -p ...` を使う
- `LibtmuxDriver.split_window()` / `split_pane()` も同様

影響:
- headless 条件で多ペイン化が成立しない

### 2. レイアウト処理が失敗を増幅
- `apply_layout()` は最初に `kill-pane -a` を実行する
- その後の `split-window` / `split-pane` が失敗すると、dashboard は単一 pane に退行する

### 3. 障害が見えにくい
- `run_once()` の `zip(tiles_sorted, sessions)` により、pane 数が不足しても一部セッションだけ描いて進行する
- 結果として「全部壊れた」ではなく「一部だけ表示される」ため、失敗が気づきにくい

### 4. 初回の整合性チェックがノイズ化
- `check_pane_integrity()` が `apply_titles()` より前に走る
- 初回は既定 `pane_title` と期待セッション名を比較して不一致になりやすい

## テスト上のギャップ
- `tests/test_tmuxio.py` は主に「どのコマンド文字列を発行したか」を見ている
- `tests/test_e2e_tmux.py` は headless での `split-window` 問題を `xfail` で吸収している
- そのため、テストグリーンでも「実 tmux で正常に多ペイン化できる」保証にはなっていない

## 外部調査の要点
- tmux 側の `size missing` は split サイズ解釈エラー経路に対応する
- `new-session -d` のサイズは client tty ではなく `default-size` / `-x/-y` 系に依存する
- ただし今回の repo に対しては、サイズ指定そのものより `-p` 使用がより直接的な要因として効いている

参照:
- tmux source:
  - `cmd-split-window.c`
  - `cmd-new-session.c`
- tmux man page:
  - man7 / OpenBSD man page

## 推奨方針
1. `split-window -p` / `split-pane -p` をやめ、`-l` ベースへ置き換える
2. `apply_layout()` をトランザクション化し、分割成功を確認するまで既存 pane を壊さない
3. pane 数不足をエラーとして可視化する
4. `check_pane_integrity()` の順序を見直す
5. `-l` 経路専用の E2E を追加し、`xfail` 依存を縮小する

## 補足
- この資料は調査レポートであり、正式な要件・設計・実装計画は `@spec-lite/current/*.md` に切り出して管理する。
