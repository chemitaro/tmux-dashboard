# tmux-dashboard

tmux-dashboard は、同一マシン上の tmux セッションをダッシュボード形式で一覧表示する CLI ツールです。セッション名（ASCII昇順）で並べ、各タイル（pane）に対象セッションの出力をカラーを保ったまま流し込みます。左下起点（左端 W 列 × 下端 H 行）で読みやすく俯瞰できます。

## 特徴
- dashboard セッションを除く全 tmux セッションを自動検出（ASCII 昇順）
- カラー保持（ANSI/TrueColor 推奨）、左下起点でクリップ表示
- リサイズ・セッション増減を検知してレイアウト再計算
- 非侵襲（`set-option -w` のみ使用。`set -g` は使用しません）
- VS Code 内蔵ターミナル対応（インテリジェント pane スキャン機能）

## 動作要件
- OS: Linux / macOS
- tmux: 3.2 以上を推奨
- Python: 3.10 以上
- パッケージ管理: [uv](https://github.com/astral-sh/uv)

## インストール（uv）
1) uv をインストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2) 依存を同期（初回）

```bash
uv sync --all-extras --dev
```

3) テスト（任意）

```bash
uv run pytest -q
```

## 使い方（クイックスタート）
1) dashboard セッションを作成

```bash
tmux new-session -d -s dashboard
```

2) ダッシュボードを起動（既定設定のまま）

```bash
uv run python -m tmux_dashboard
```

3) 設定ファイルを使う（推奨）

```bash
cat > ~/tmux-dashboard.yaml << 'YAML'
min_tile_width: 40
tmux:
  driver: libtmux   # libtmux推奨（CLIでも可）
viewer:
  max_fps: 30
  wrap_mode: clip-right
logging:
  level: INFO
YAML

uv run python -m tmux_dashboard --config ~/tmux-dashboard.yaml
```

4) 一度だけ実行して動作を試す（デバッグ用途）

```bash
uv run python -m tmux_dashboard --once --iterations 1
```

## CLI オプション
- `--config <path>`: 設定ファイル（YAML）。未指定時は `~/.config/tmux-dashboard/config.yaml` を探索。
- `--window-target <session:window>`: ダッシュボード対象（既定: `dashboard:0`）。
- `--once` `--iterations N`: N 回だけ更新して終了（デバッグ用途）。

## 設定（YAML）例
```yaml
min_tile_width: 40
poll_interval_sec: 2
exclude_patterns:
  - "^dashboard$"   # dashboard セッションは除外

pane_border_enabled: true
pane_border_format: "#{pane_title}"

tmux:
  driver: libtmux     # 推奨: libtmux / 代替: cli
  socket_name: null
  socket_path: null

viewer:
  mode: capture-only
  join_wrapped_lines: true
  max_fps: 30
  drop_stale_frames: true
  wrap_mode: clip-right
  truecolor: true

logging:
  level: INFO
  dir: ~/.local/state/tmux-dashboard
  rotate_max_bytes: 10485760
  rotate_backup_count: 5
```

## よく使う tmux 操作（参考）
- dashboard 作成: `tmux new-session -d -s dashboard`
- セッション作成: `tmux new-session -d -s alpha`
- セッション削除: `tmux kill-session -t alpha`
- ウィンドウリサイズ: `tmux resize-window -t dashboard:0 -x 120 -y 40`
- サーバ全停止（リセット）: `tmux kill-server`

## ドライバ（tmux 接続方式）
- `libtmux`（推奨）: 安定した API で操作。server/window/pane の `cmd(...)` を併用可。
- `cli`: `tmux` コマンド直叩き。headless 環境では client 未接続時の `split-window` が失敗する場合があります。

## トラブルシューティング
- pane が増えない / 分割されない:
  - headless 環境では `split-window` が失敗する場合があります。`libtmux` ドライバを使用してください。
  - `dashboard` 以外のセッションが存在するか確認してください。
- 表示が崩れる / 色が残る:
  - 端末の TrueColor 設定をご確認ください（必要に応じて 256色にフォールバック）。

## テスト
- 全体: `uv run pytest -q`
- E2E（実 tmux 使用）: `tests/test_e2e_tmux.py`
  - 本テストは `tmux kill-server` を行います（他の tmux セッションがある場合はご注意ください）。
  - 環境によっては headless で `split-window` が不可なため、いくつかのケースは `xfail` となります。

## ライセンス
本リポジトリ内のコードはプロジェクト目的のために提供されています。個別ファイルのライセンス表記がある場合はそちらを優先します。
