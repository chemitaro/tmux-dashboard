# 実装報告書

## 実装サマリー

2026-03-14 時点で `tmux-dashboard` の現状実装を調査し、主要モジュール、CLI、設定優先順位、tmux 連携方式、テスト状況、既知の未完了領域を確認した。
今後の質問対応の前提として、仕様書だけでなく実コードと `uv run pytest -q` の実行結果に基づく理解を repo 内に記録する。

## 実装記録

### 2026-03-14 13:20 - 13:35

#### 実施内容
- `README.md`、`@planning/current/requirement.md`、`@planning/current/design.md`、`@planning/current/task.md`、`pyproject.toml` を確認し、ツールの目的と仕様の基準文書を整理した。
- `tmux_dashboard/orchestrator.py`、`tmux_dashboard/tmuxio.py`、`tmux_dashboard/renderer.py`、`tmux_dashboard/tile.py`、`tmux_dashboard/config.py`、`tmux_dashboard/session_manager.py`、`tmux_dashboard/__main__.py` を調査し、実装フローを確認した。
- `tests/` を確認し、単体テスト・回復系テスト・実 tmux E2E の存在と対象範囲を把握した。
- `uv run pytest -q` を実行し、現時点の回帰状態を確認した。
- 実装と設計との差分として、VS Code 対応の `resolve_best_pane()`、`configs/dashboard.yaml` の優先読込、`tile.py` によるタイルごとの描画プロセス、`3 xfailed` の headless tmux 制約付き E2E を確認した。

#### テスト結果
```bash
uv run pytest -q

# 結果サマリー
67 passed, 3 xfailed
```

#### 作成/修正したファイル
1. `planning/current/report.md` - 調査結果と検証結果を追記

#### 遭遇した問題と解決
- **問題**: `tests/test_e2e_tmux.py` の一部ケースは headless tmux 環境で `split-window` の挙動差により厳密検証できない。
- **解決**: 該当ケースは `xfail` として明示されており、現状のテストスイートでは期待された扱いになっていることを確認した。

---

### YYYY-MM-DD HH:MM - HH:MM

#### 実施内容
[次の作業セッションの記録]

---

### 2026-03-30 18:15 - 18:25

#### 実施内容
- `uv run python -m tmux_dashboard --once --iterations 1` を実行し、起動時ログと tmux 状態を観測した。
- `alpha` / `beta` セッションを作成した状態で dashboard を 1 サイクル実行し、期待レイアウトと実際の pane 数・タイトルを比較した。
- `tmux split-window` を detached / headless な `dashboard` セッションに対して直接実行し、エラー条件を再現した。
- `tmux_dashboard/tmuxio.py` と `tmux_dashboard/orchestrator.py` を参照し、pane 分割・整合性チェックの実装順序を確認した。
- `tests/test_e2e_tmux.py` を参照し、headless tmux での `split-window` 失敗が既知制約として `xfail` で吸収されていることを確認した。

#### 判明したこと
- 主因候補は、headless tmux 環境で `split-window` が `size missing` で失敗し、多ペイン構成を作れないこと。
- その結果、`columns` / `rows` の計画は正しくても dashboard 側の実 pane 数が増えず、1 pane のまま止まる。
- `check_pane_integrity()` は `apply_titles()` より前に走るため、初回は未設定の `pane_title` を期待セッション名と比較して警告を出しやすい。
- 現行テストは単体では通るが、E2E の一部は headless 環境では成立しない前提で `xfail` とされているため、「実環境で機能する」ことまでは担保していない。

#### 再現ログ要約
```bash
tmux split-window -h -p 50 -t dashboard:0.0
# => size missing
```

```bash
uv run python -m tmux_dashboard --once --iterations 1
# detected: sessions=['alpha', 'beta'], window=80x24
# plan: columns=1 rows=2
# Pane integrity check failed. Expected: ['alpha', 'beta'], Actual: ['1f4a0dd3b78d']
```

#### 参照箇所
- `tmux_dashboard/tmuxio.py`
  - `CliDriver.split_window()`
  - `LibtmuxDriver.split_window()`
- `tmux_dashboard/orchestrator.py`
  - `apply_layout()`
  - `check_pane_integrity()`
- `tests/test_e2e_tmux.py`
  - headless tmux 制約に関する `xfail`

#### 次の調査方針
- detached / headless tmux で `split-window` が成立する条件の洗い出し。
- `dashboard` セッション生成方法の差分（初期コマンド、TERM、サイズ指定、client 有無）の影響確認。
- 実装修正候補として、pane 分割戦略の見直しと整合性チェック順序の妥当性を検討。

#### サブエージェント分析の統合メモ
- `repo_analyst` 観点:
  - 多ペイン化は `apply_layout()` → `split_window()` / `split_pane()` に強く依存しており、ここが失敗すると機能全体が停止する。
  - `apply_layout()` が先に `kill-pane -a` を実行するため、分割失敗時に dashboard を単一 pane に退行させる。
  - E2E は headless 制約を `xfail` で吸収しており、実運用上の失敗モードが見えにくい。
- `code_reviewer` 観点:
  - `run_once()` の `zip(tiles_sorted, sessions)` により、pane 数不足がサイレントに切り捨てられ、一部セッションだけ描画して進行してしまう。
  - `check_pane_integrity()` の評価順序により、初回ノイズが再レイアウト誘発要因になっている。
  - `window_size()` 周りの包括例外捕捉が、真因を「dashboard 消失」に見せかけやすい。

#### 追加再現結果
```bash
TERM=screen-256color tmux new-session -d -s dashboard 'sleep 300'
tmux resize-window -t dashboard:0 -x 120 -y 40
tmux split-window -h -p 50 -t dashboard:0
# => size missing
```

```bash
uv run python - <<'PY'
from tmux_dashboard import config, tmuxio
cfg = config.load_config(None)
cfg.tmux.driver = 'cli'
io = tmuxio.create_from_config(cfg)
io.split_window('dashboard:0', 'h', 50)
PY
# => CalledProcessError: tmux split-window ... -t dashboard:0.0
```

#### 現時点の暫定結論
- 一次原因は headless / detached tmux で pane 分割前提が崩れていること。
- 二次原因として、現在の実装はその失敗を検知・隔離・縮退表示できず、むしろ dashboard 状態を悪化させる。
- 単体テストは通るが、実 tmux での操作前提を十分に保証していない。

---

### 2026-03-30 18:25 - 18:40

#### 追加事実
- ユーザー追加検証:
  - 環境: `tmux 3.4` / detached session / `TERM=screen-256color` / `new-session -d -x 120 -y 40`
  - `split-window -p 50` は `size missing`
  - `split-window -l 40` と `split-window -l 50%` は成功
  - pane id target でも `-l 50%` の水平・垂直分割が成功

#### 解釈
- 問題は「headless では split-window が全面的に使えない」ではなく、「`-p` ベースの分割指定が headless 条件で壊れやすい」可能性が高い。
- 現行実装は `layout.progressive_percent_splits()` を使って `-p` 指定の分割を前提にしているため、実装の中心仮定が tmux 3.4 detached 条件と噛み合っていない。
- したがって、修正戦略の本命は headless 回避ではなく、`-p` 依存を下げて `-l` ベースの分割アルゴリズムへ寄せること。

#### 設計への影響
- `tmux_dashboard/layout.py`:
  - `progressive_percent_splits()` 中心の設計は見直し候補
- `tmux_dashboard/orchestrator.py`:
  - `apply_layout()` の `split_window(... percent=...)` / `split_pane(... percent=...)` 呼び出し方式を変更候補
- `tmux_dashboard/tmuxio.py`:
  - `split_window()` / `split_pane()` のインターフェースを percent ではなく length 指定対応に拡張する案が有力

#### 更新後の仮説順位
1. 主因: `split-window -p` 依存
2. 増幅要因: `kill-pane -a` を先に実行する非トランザクション構成
3. 観測ノイズ: `check_pane_integrity()` の初回誤警告と pane不足の黙殺

#### 追加深掘り（2026-03-30 18:25 - 18:40）
- `tmux 3.4` / `TERM=screen-256color` / detached session / `-x 120 -y 40` の条件で、`split-window` のオプション差を比較した。
- 結果:
  - `split-window -h -p 50 -t dashboard:0` → `size missing`
  - `split-window -h -l 40 -t dashboard:0` → 成功
  - `split-window -h -l 50% -t dashboard:0` → 成功
  - `split-window -h -l 50% -t <pane_id>` → 成功
  - `split-window -v -l 50% -t <pane_id>` → 成功
- 以上より、headless で全面的に分割不能なのではなく、**現行実装の `-p` ベース分割戦略がこの環境の tmux 3.4 と相性が悪い**可能性が高い。

#### 実験ログ要約
```bash
tmux new-session -d -x 120 -y 40 -s dashboard 'sh -lc "sleep 300"'
tmux split-window -h -p 50 -t dashboard:0
# => size missing
```

```bash
tmux new-session -d -x 120 -y 40 -s dashboard 'sh -lc "sleep 300"'
tmux split-window -h -l 50% -t %0
tmux split-window -v -l 50% -t %0
# => いずれも成功
```

#### 更新した仮説
- 根本原因は「headless tmux そのもの」よりも、「`split-window -p <percent>` を前提にした実装」。
- その上で、`apply_layout()` の先行破壊 (`kill-pane -a`) や、pane 数不足の黙殺、整合性チェック順序が障害を拡大している。

---

### 2026-03-30 18:30 - 18:45

#### 実施内容（一次情報調査）
- tmux の公式 man page（man7 / OpenBSD）を参照し、`new-session` と `split-window` の仕様を確認。
- tmux upstream ソース（`cmd-new-session.c` / `cmd-split-window.c`）を参照し、`detached` 時のサイズ決定ロジックと `size missing` メッセージ発生条件を確認。
- CHANGES（tmux 3.5a 系）を参照し、`window-size` / `default-size` / `resize-window` の関係と `split-window -p` の履歴的扱いを確認。

#### 事実（一次情報から確定）
1. `new-session -d` ではクライアントサイズではなく `default-size`（既定 80x24）を基準にセッションサイズが決まる。`-x/-y` 指定時はその値が反映される。
2. `split-window` で `size missing` が出るのは、サイズ解釈フェーズで `cause` が立つ時であり、tmux 内部で `cmdq_error("size %s", cause)` が実行される経路。
3. `resize-window` は `window-size` を `manual` に寄せる仕様で、`default-size`/`new-session -x/-y` と組み合わせると headless セッションの分割可能性に直接影響する。

#### 本件への含意（repo向け）
- `tmux_dashboard/tmuxio.py` は `split-window ... -p <percent>` 固定で実行しており、サイズ決定の失敗が起きると即レイアウト不能になる。
- `session_manager.ensure_dashboard_session()` は `new-session -d -s dashboard` のみで、`-x/-y` を使わないため、headless 条件では分割余地が環境依存になる。
- `tests/test_e2e_tmux.py` の `xfail` はこの制約を反映しており、現在の E2E は「headless でも多ペインが作れる」ことを保証しない。

#### 参照（一次情報）
- man7 tmux: https://man7.org/linux/man-pages/man1/tmux.1.html
- OpenBSD tmux man: https://man.openbsd.org/tmux
- tmux source (`cmd-split-window.c`): https://github.com/tmux/tmux/blob/master/cmd-split-window.c
- tmux source (`cmd-new-session.c`): https://github.com/tmux/tmux/blob/master/cmd-new-session.c
- CHANGES (Debian source mirror): https://sources.debian.org/src/tmux/3.5a-3/CHANGES

---

## 最終テスト結果

### テストカバレッジ
```
[カバレッジレポートのサマリー]
```

### 品質チェック
```bash
# リンター実行結果
[結果]

# フォーマッター実行結果
[結果]
```

## 学んだこと

1. [技術的な学び]
2. [プロセスの改善点]

## 今後の推奨事項

1. [改善提案や技術的負債]
2. [次のステップの推奨]

## 完了確認

- [ ] すべての要件が実装された
- [ ] すべてのテストが通っている
- [ ] コードレビューが完了した
- [ ] ドキュメントが更新された
- [ ] アーカイブの準備ができた
