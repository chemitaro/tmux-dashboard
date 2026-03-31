# wrapper create-window 修正 受け入れ再判定レポート（S05）

- 実施日: 2026-03-31 (UTC)
- 対象実装: S05 follow-up after `acceptance-review-wrapper-fix-20260331.md`
- 参照元: `spec-lite/current/discussions/acceptance-review-wrapper-fix-20260331.md`
- 判定: `pass`
- 位置づけ: 上記受け入れ検査レポートを supersede する再判定記録

## 1. 結論

`acceptance-review-wrapper-fix-20260331.md` で open とされていた 3 findings は、S05 実装と follow-up 回帰追加によりすべて closed と判断する。

本再判定は、元レポートの監査証跡を残したまま、「S05 完了後の authoritative acceptance verdict」を与えるための superseding record である。

## 2. 再判定対象と結果

### 2.1 Finding A: libtmux `swap_window()` / `kill_window()` の fail-closed 不足

- 以前の状態:
  - tmux command failure が default driver で silent success になり得た
- S05 対応:
  - `tmux_dashboard/tmuxio.py` の `LibtmuxDriver.swap_window()` / `kill_window()` に `_raise_if_cmd_failed()` を適用
  - `tests/test_tmuxio.py` に libtmux lifecycle failure regression を追加
- 判定:
  - `closed`

### 2.2 Finding B: create failure 後の ghost residual target 汚染

- 以前の状態:
  - 実在しない predicted staging target が cleanup queue に積まれ得た
- S05 対応:
  - `tmux_dashboard/orchestrator.py` に staging target 実在確認を追加
  - missing target は cleanup warning 補足には使えても residual retry queue へは入れないよう補正
  - `tests/test_orchestrator.py` に missing target 非 enqueue regression を追加
- 判定:
  - `closed`

### 2.3 Finding C: 0 セッション収束後の stale pane title

- 以前の状態:
  - `dashboard:0` が 1 pane に戻っても古い session 名 title が残り得た
- S05 対応:
  - `tmux_dashboard/orchestrator.py` で 0 セッション short-circuit 後に単一 pane の title を空文字へ更新
  - `tests/test_orchestrator.py` に unit regression を追加
  - `tests/test_e2e_tmux.py` に direct runner の zero-session regression を追加
  - さらに本 follow-up で wrapper path の zero-session regression を追加
- 判定:
  - `closed`

## 3. follow-up で追加した acceptance 証跡

### 3.1 wrapper path zero-session regression

- 追加テスト:
  - `tests/test_e2e_tmux.py::test_e2e_wrapper_path_zero_sessions_clear_stale_title`
- シナリオ:
  1. `./tmux-dashboard` で wrapper 経路起動
  2. 少なくとも 1 つの対象 session を作成し provisioning 完了を待機
  3. 対象 session をすべて削除
  4. `dashboard:0` が `1 pane + empty title` に収束することを確認
- 解釈:
  - direct runner だけでなく wrapper 経路でも stale title cleanup が閉じたことを自動検証できる

## 4. 実行コマンド / 結果

```bash
uv run pytest tests/test_e2e_tmux.py -q
# 10 passed in 4.51s

uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_e2e_tmux.py tests/test_cli_entry.py -q
# 50 passed in 4.88s

uv run pytest -q
# 104 passed in 4.79s
```

## 5. 総合判定

- 受け入れ判定: `pass`
- superseded artifact:
  - `spec-lite/current/discussions/acceptance-review-wrapper-fix-20260331.md`
- authoritative current artifact:
  - `spec-lite/current/discussions/acceptance-review-wrapper-fix-20260331-s05-rereview.md`

## 6. スコープ外の明記

- wrapper の attach / TTY 挙動変更は実施していない
- wrapper visible window 名の変更も実施していない
- CLI exit code 方針は従来どおり個別サイクル failure でも exit 0 を維持する
