# headless tmux 復旧 手動検証レポート

- 実施日時: 2026-03-30 14:52 UTC - 14:55 UTC
- 実施者: Codex
- 対象機能: `fix-tmux-headless-layout`
- 目的: 元の潜在バグである「headless / detached tmux 環境で dashboard が分割されず 1 pane のままになる」状態が解消されたかを、実際の tmux セッションで手動確認する

## 結論

今回の手動検証で確認した範囲では、元の潜在バグは解消されています。

- detached/headless 条件で `dashboard:0` が複数 pane に分割されることを確認
- pane title が対象セッション名になることを確認
- ウィンドウ幅を `79` に縮小した後も、単一列レイアウトへ再計算されることを確認
- セッション削除後の再実行で、削除したセッション名が pane title から消えることを確認
- 8 セッション / 幅 `160` の exact grid で 8 pane が構成されることを確認

## 実施環境

- リポジトリ: `/srv/mount/tmux-dashboard`
- 実行コマンド: `uv run python -m tmux_dashboard ...`
- tmux 実行時環境:
  - `SHELL=/bin/bash`
  - `TERM=screen-256color`

補足:
- `.venv/bin/python` はローカル環境由来の壊れたシンボリックリンクを含んでいたため、手動検証では `uv run` を使用した
- これはアプリ修正対象の不具合ではなく、検証用 Python 実行経路の都合

## シナリオ 1: headless multi-session split

### 手順

1. `dashboard`, `alpha`, `beta`, `gamma` の 4 セッションを detached で作成
2. `uv run python -m tmux_dashboard --config <tmp cfg> --window-target dashboard:0 --once --iterations 1` を実行
3. `tmux list-panes -t dashboard:0 -F '#{pane_id}|#{pane_width}|#{pane_height}|#{pane_left}|#{pane_top}|#{pane_title}'` で結果を確認

### 観測結果

- window size: `80 24`
- pane count: `3`
- titles: `alpha`, `beta`, `gamma`

```text
%4|39|10|0|1|alpha
%6|39|12|0|12|beta
%5|40|23|40|1|gamma
```

### 判定

- 期待どおり
- 元の不具合である「1 pane のまま」は再現しなかった

## シナリオ 2: resize down to single column

### 手順

1. シナリオ 1 の状態から `tmux resize-window -t dashboard:0 -x 79 -y 40` を実行
2. 同じ `--once` 実行を再度実行
3. pane geometry と title を確認

### 観測結果

- window size: `79 40`
- pane count: `3`
- すべての pane width が `79`
- titles: `alpha`, `beta`, `gamma`

```text
%7|79|11|0|1|alpha
%9|79|13|0|13|beta
%8|79|13|0|27|gamma
```

### 判定

- 期待どおり
- 単一列レイアウトへ再計算され、S02 で修正したサイズ巻き戻りも再現しなかった

## シナリオ 3: remove one session and re-run

### 手順

1. シナリオ 2 の状態から `tmux kill-session -t beta` を実行
2. `--once` 実行を再度実行
3. pane title と pane 数を確認

### 観測結果

- window size: `79 40`
- pane count: `2`
- titles: `alpha`, `gamma`

```text
%10|79|18|0|1|alpha
%11|79|20|0|20|gamma
```

### 判定

- 期待どおり
- 削除済み `beta` は title から消えた

## シナリオ 4: exact grid with 8 sessions

### 手順

1. `dashboard` と `s1` から `s8` までの 9 セッションを detached で作成
2. `tmux resize-window -t dashboard:0 -x 160 -y 40` を実行
3. `--once` 実行を実行
4. pane 数と title 一覧を確認

### 観測結果

- pane count: `8`
- titles: `s1` から `s8`

```text
%9|39|18|0|1|s1
%13|39|20|0|20|s2
%12|39|18|40|1|s3
%14|39|20|40|20|s4
%11|39|18|80|1|s5
%15|39|20|80|20|s6
%10|40|18|120|1|s7
%16|40|20|120|20|s8
```

### 判定

- 期待どおり
- S03 で通常検証へ戻した exact grid ケースは、手動でも成立した

## 総合評価

- 元の潜在バグ: 解消を確認
- S02 の非破壊 apply: 手動観測上、dashboard が壊れたまま残る挙動は確認されなかった
- S03 の headless E2E 通常検証化: 手動でも整合

## 残メモ

- `tests/test_e2e_tmux.py` で残っている `dynamic_add_then_remove` の headless 条件分岐までは今回の手動検証対象に含めていない
- ただし、元の障害に対する復旧確認としては十分な結果が得られた
