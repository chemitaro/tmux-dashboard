# 設計書（tmux ダッシュボード / v1）

参照: @planning/current/requirement.md（正式版 v1.1 反映済み）

## 概要
- 同一マシン上の全 tmux セッションを、`dashboard` セッション内にタイル表示し俯瞰する。
- 左下起点・カラー保持・非侵襲（set -g 禁止、`dashboard:0` 限定設定）。
- MVP は `capture-only` で実装。`pipe_stream` は後続機能フラグ。
- tmux 3.2+、Python 3.10+ 前提。

## アーキテクチャ

### 全体構成
```
┌────────────────────────────────────────┐
│ tmux session: dashboard                │
│  window: 0                             │
│  ┌────────────┬────────────┬──────────┐│
│  │ tile pane  │ tile pane  │ tile ... ││  ← 各 pane 内で Renderer(ANSI) が動作
│  │ Renderer   │ Renderer   │          ││     （対象セッションの pane を capture）
│  └────────────┴────────────┴──────────┘│
│            ▲ Orchestrator (Python) ▲    │
│            │  - セッション列挙            │
│            │  - レイアウト計算            │
│            │  - pane作成/破棄             │
│            │  - paneタイトル設定           │
│            │  - Renderer起動/停止         │
└──────────────┴─────────────────────────┘

外部: 対象セッション群（本体のコーディング等が動作）
```

### 技術スタック
- **言語/ランタイム**: Python 3.10+（標準ライブラリ中心）。
- **端末制御**: ANSI 直描画（既定）。curses は Optional Driver。
- **tmux I/O**: サブプロセスで `tmux` コマンド実行（`subprocess.run`）。
- **ログ**: RotatingFileHandler（10MB×5）。
- **設定**: YAML（`--config` > `~/.config/tmux-dashboard/config.yaml` > 組込既定）。

## コンポーネントとインターフェース

### 主要コンポーネント

#### 1. Orchestrator
- 役割: セッション検出、ウィンドウ寸法取得、レイアウト計算、pane 構成、Renderer のライフサイクル管理、dashboardセッション管理。
- 主機能:
  - `scan_sessions()`：`tmux list-sessions` → 除外 → ASCII 昇順。
  - `resolve_target_pane(session)`：ウィンドウ/ペイン選定ルールで対象 pane_id を取得。
  - `get_dashboard_wh()`：`tmux display-message -p -t dashboard:0 "#{window_width} #{window_height}"`。
  - `compute_grid()`：`columns=floor(W/min_tile_width)`, `rows=ceil(n/columns)`。
  - `reconcile_layout()`：構成差分があれば pane 再構成（初版は全面再構成）。
  - `apply_pane_titles()`：`set-option -w` と `select-pane -T`。
  - `spawn_renderers()`：各タイルで Renderer 起動（対象 pane を引数）。
  - `handle_dashboard_recovery()`：dashboardセッション消失時の検出と自動再作成。
  - ポーリングループ：`poll_interval_sec` 間隔で再評価（≤3秒反映）。

#### 2. Renderer（TerminalDriver=ansi 既定）
- 役割: 対象 pane（別セッション）の出力を周期 `capture-pane` し、タイル pane 内に差分描画。
- 主機能:
  - `query_tile_wh()`：`tmux display-message -p -t <tile_pane_id> "#{pane_width} #{pane_height}"` → H の決定。
  - `capture(H)`：`tmux capture-pane -p -e (-J) -S -<H> -E -1 -t <target_pane_id>`。
  - 整形: ANSI を保持しつつ `wcwidth` で見かけ幅を計算、W 列×H 行にクリップ（右端切り捨て）。
  - 差分: 行ハッシュで差分検出、`max_fps` で描画上限、古いフレームは破棄。
  - `SIGWINCH`（tmux 経由の再描画トリガ）に相当するサイズ変化をポーリングで検知し即時再描画。

#### 3. TmuxIO
- 役割: tmux コマンドの実行ラッパ、出力パース、安全なエラー処理（バックオフ）。
- ドライバ設計: `TmuxDriver` 抽象を定義し、実装を差し替え可能にする。
  - `LibtmuxDriver`（既定）: `libtmux.Server/Session/Window/Pane` を用いて操作。未サポートは `obj.cmd(...)` で生コマンド実行。
  - `CliDriver`: `subprocess.run(["tmux", ...])` による直接実行。
  - 設定: `config.tmux.driver in {"libtmux","cli"}`。
- 主機能: `list_sessions()`, `list_windows(session)`, `list_panes(session, win)`, `display(target, fmt)`, `capture(target, opts)`, `set_window_option`, `select_pane_title` など。

##### 3.1 LibtmuxDriver 詳細（Phase 8 事前整理）
- Server 初期化: `socket_name` / `socket_path` を `libtmux.Server(**kwargs)` に反映（cfg 由来）。
- Window 解決: `window_target='session:window_index'` から `server.sessions` → `session.windows` を走査し Window を取得。見つからない場合はフォールバック（安全策）。
- 取得系:
  - `window_size(target)`: Window の `window_width/window_height` 属性を参照（将来: `display-message` 併用を検討）。
  - `list_panes(target)`: Window の `panes` から `pane_id` を抽出。
- 実行系:
  - `capture_pane(pane_id, H, join_wrapped)`: `pane.cmd("capture-pane", -p, -e, [-J], -S -H, -E -1, -t pane_id)`。
  - `set_window_option(target, key, value)`: `window.cmd("set-option", -w, -t target, key, value)`（非侵襲）。
  - `set_pane_title(pane_id, title)`: `window.cmd("select-pane", -t pane_id, -T title)`。
  - `kill_other_panes(target)`: `window.cmd("kill-pane", -a, -t target)`。
  - `split_window(target, dir, percent)`: `window.cmd("split-window", -h/-v, -p percent, -t target)`。

##### 3.2 統合テスト方針（Phase 8）
- 段階的統合:
  1) FakeIO 駆動で Orchestrator のセッション増減・リサイズ再計算・タイトル設定を確認（既存+拡充）。
  2) `libtmux` の TestServer を利用した軽量E2E（tmux の有無で skip）。
- Skip 条件: 実行環境に tmux / libtmux が無い場合は pytest のマーカーで skip。
- 非侵襲検証: `set-option -w` の使用、`set -g` 不使用をログ/コマンド監視で確認。

#### 4. Layout
- 役割: 列/行数の計算、分割手順の生成、差分判定。
- 主機能: `calc_columns(W, min_tile_width)`, `calc_rows(n, columns)`, `plan_splits(columns, rows)`。

#### 5. Config
- 役割: YAML ロード、既定値適用、バリデーション。
- 主フィールド: `min_tile_width`, `poll_interval_sec`, `exclude_patterns`, `viewer.{mode,pipe_stream,join_wrapped_lines,max_fps,drop_stale_frames,wrap_mode,truecolor}`, `logging.{level,dir,rotate_max_bytes,rotate_backup_count}`。

#### 6. logging_setup
- 役割: ロガー初期化（RotatingFileHandler）。

#### 7. utils_wcwidth
- 役割: `wcwidth` ベースの幅計算、ANSI 除去/保持ヘルパ、行末 `\x1b[0m` 付与。

#### 8. SessionManager
- 役割: dashboardセッションの存在確認と自動作成。
- 主機能:
  - `ensure_dashboard_session(io)`：セッション一覧を確認、不在時は `tmux new-session -d -s dashboard` で作成。
  - 新規作成時は True、既存時は False を返却。

### インターフェース定義（擬似）
```python
class TmuxIO:
    def list_sessions(self) -> list[str]: ...
    def list_windows(self, session: str) -> list[dict]: ...  # {index:int, active:bool}
    def list_panes(self, session: str, win_idx: int) -> list[dict]: ...  # {index:int, active:bool, id:str}
    def display(self, target: str, fmt: str) -> str: ...
    def capture(self, target: str, *, H: int, join_wrapped: bool) -> str: ...
    def set_window_option(self, target: str, key: str, value: str): ...  # -w 限定
    def select_pane_title(self, pane_id: str, title: str): ...
    def split(self, how: str, percent: int): ...  # -h/-v
    def kill_other_panes(self): ...

class TmuxDriver(Protocol):
    def list_sessions(self) -> list[str]: ...
    def window_size(self, window_target: str) -> tuple[int, int]: ...
    def capture_pane(self, pane_target: str, H: int, join_wrapped: bool) -> str: ...
    def set_window_option(self, window_target: str, key: str, value: str): ...
    def set_pane_title(self, pane_target: str, title: str): ...

class Orchestrator:
    def run(self): ...

class Renderer:
    def loop(self): ...
```

## データモデル

### セッション→対象pane マッピング
```python
SessionView = TypedDict('SessionView', {
  'session': str,
  'target_pane_id': str,   # 対象セッション側の pane_id
  'tile_pane_id': str,     # dashboard 側の pane_id
})
```

### レイアウトプラン
```python
LayoutPlan = TypedDict('LayoutPlan', {
  'columns': int,
  'rows': int,
  'splits': list[dict],  # 例: [{'dir': 'h', 'percent': 33}, ...]
})
```

## コア機能の設計

### 対象 pane 選定（要件 5.6）
1. `list_windows(session)` から `active==True` を優先。無ければ `index` 最小。
2. 該当 window の `list_panes(session, win_idx)` から `active==True` を優先。無ければ `index` 最小。
3. 得た `pane_id` を対象として Renderer が `capture-pane -t <pane_id>` を行う。

### レイアウト計算（要件 5.3, 6）
- `columns = max(1, min(N, floor(W / min_tile_width)))`  # N は対象セッション数（dashboard除外後）
- `rows = ceil(N / columns)`
- tmux の分割は % 丸めのため端数は末尾で吸収。`min_tile_width` を厳守。
- 初版は全面再構成（`kill-pane -a` → 水平分割で列を作成 → 各列で垂直分割）。

手順（例）:
1. 既存 pane を残しつつ `kill-pane -a -t dashboard:0` で単一 pane に。
2. 列数 `C` を `split-window -h -p percent` で作成（均等割 or 端数調整）。
3. 各列 pane を選択し、行数 `R` に合わせて `split-window -v -p percent` を実行。
4. 生成順に、左→右、上→下（行優先）の順でタイル pane をセッション順（ASCII昇順）にマッピングし、不要な空セルは生成しない（N 個のみ生成）。

### タイトル設定（要件 5.4）
- `tmux set-option -w -t dashboard:0 pane-border-status top`
- `tmux set-option -w -t dashboard:0 'pane-border-format' '#{pane_title}'`
- 各タイル: `tmux select-pane -t <tile_pane_id> -T '<session_name>'`

### レンダリング（要件 5.5, 7.4）
- H の決定: `<tile_pane_id>` の `pane_height` を用いる。tmuxの`pane_height`はコンテンツ領域の行数であり、`pane-border-status top`のボーダー行は含まれないため、原則として減算不要。環境差異に備え、`capture-pane -S -H -E -1`で取得される行数と突合し、オフバイワンを検知した場合にのみ1行調整（フェイルセーフ）。
- `capture-pane` 引数: `-p -e (-J) -S -<H> -E -1 -t <target_pane_id>`。
- 整形: `wcwidth` による見かけ幅。`wrap_mode='clip-right'` で右端クリップ。
- 差分: 行ごとにハッシュ比較。更新がある行のみ再描画。
- フレーム制御: `max_fps=30`、キュー輻輳時は古いフレームをドロップ（最新優先）。
- 行末リセット: 各行末に `\x1b[0m` を付与。

### ポーリングと再配置（要件 4, 6, 9）
- 周期: `poll_interval_sec`（既定 2s）。
- 監視対象: セッション一覧、`dashboard:0` の `window_width/height`。
- 差分検知: セッション増減 or W/H 変化 or `min_tile_width` 影響 → レイアウト再計算。
- レンダラーは W/H 変化を検知し即時再描画。

## エラーハンドリング / リトライ
- tmux コマンド失敗時は指数バックオフ（例: 0.5s, 1s, 2s, 最大3s）。
- 例外はログにスタックトレースを書き、影響最小化（個別 Renderer 異常でも他タイル継続）。
- `pipe_stream` 利用時は終了時に必ず解除（ON は後続機能）。
- tmux 未インストール/未起動の検出: 起動時に`tmux -V`/libtmux接続を試行し、分かりやすい診断を出力（復旧案内）。
- **dashboardセッション消失時**：
  - `window_size()` 等で `subprocess.CalledProcessError` をキャッチ。
  - SessionManager でセッション再作成。
  - ターミナルに `[tmux-dashboard] Recreated dashboard session` を表示。
  - 同一サイクル内でレイアウトを再構築（レンダラーも自動再起動）。

## ログ / 可観測性
- 出力先: `~/.local/state/tmux-dashboard`。
- ローテーション: 10MB×5。
- 指標: 再レイアウト回数、平均 fps、ドロップ率、エラー件数、対象セッション数。

## セキュリティ / 非侵襲方針
- `set -g` 禁止。`set-option -w -t dashboard:0` のみ。
- 対象セッションの設定・レイアウトは変更しない（`capture-only`）。

## ディレクトリ/ファイル構成

要件 12.2 の推奨構成を具現化したレイアウトを前提とする。

```
repo-root/
├─ tmux_dashboard/
│  ├─ __init__.py
│  ├─ __main__.py            # CLIエントリ: 引数パース、Orchestrator起動/終了処理
│  ├─ orchestrator.py        # セッション検出・レイアウト・pane管理・自動復旧
│  ├─ renderer.py            # タイル描画（ANSI差分描画・fps制御）
│  ├─ tmuxio.py              # TmuxDriver抽象 + LibtmuxDriver/CliDriver
│  ├─ layout.py              # 列/行計算・分割計画
│  ├─ config.py              # 設定ロード/バリデーション
│  ├─ logging_setup.py       # RotatingFileHandler 初期化
│  ├─ utils_wcwidth.py       # 幅計算/ANSIユーティリティ
│  └─ session_manager.py     # dashboardセッション管理
├─ tests/
│  ├─ conftest.py            # 共通fixture（libtmux TestServer, 時刻モック 等）
│  ├─ test_config.py
│  ├─ test_layout.py
│  ├─ test_ansi_width.py
│  ├─ test_renderer.py
│  ├─ test_tmuxio.py
│  └─ test_orchestrator.py
├─ configs/
│  └─ dashboard.example.yaml  # 設定テンプレート
├─ docs/
│  └─ requirements.md         # 要件定義（本件では @planning を正とし同期）
├─ planning/
│  └─ current/                # 要件/設計/タスク/レポート
├─ README.md
├─ pyproject.toml
└─ uv.lock
```

各ファイルの責務（概要）
- `tmux_dashboard/__main__.py`: `argparse` で `--config` 等を受け取り、`Orchestrator` を生成・起動。SIGINT/SIGTERMで安全停止。
- `tmux_dashboard/orchestrator.py`: セッション列挙、ウィンドウ寸法取得、レイアウト計算、pane生成/破棄、タイトル設定、Rendererのライフサイクル管理。
- `tmux_dashboard/renderer.py`: `capture-pane` 出力の成形（W×H, 左基準/下端H行）、差分描画、`max_fps`、行末SGRリセット、オフバイワン検知時のH安全調整。
- `tmux_dashboard/tmuxio.py`: `TmuxDriver`抽象＋`LibtmuxDriver`（既定）/`CliDriver`（代替）。`list_sessions`/`window_size`/`capture_pane`/`set_window_option`/`set_pane_title` 等を提供。
- `tmux_dashboard/layout.py`: `calc_columns`/`calc_rows`/`plan_splits` などの純粋関数群。
- `tmux_dashboard/config.py`: YAML/既定値/優先順位（--config > XDG > 組込）/バリデーション。
- `tmux_dashboard/logging_setup.py`: ローテーション（10MB×5）、ログディレクトリ既定（`~/.local/state/tmux-dashboard`）。
- `tmux_dashboard/utils_wcwidth.py`: `wcwidth` 準拠の幅計算、ANSI保持/リセットユーティリティ。
- `tests/conftest.py`: libtmuxの`TestServer`で独立tmuxを用意、環境変数/XDG/時刻モックなど共通fixtureを提供。

## テスト戦略（pytest）
- 単体:
  - `utils_wcwidth`: 日本語/絵文字/合成文字の幅計算、ANSI リセットの健全性。
  - `layout`: 列/行計算、`min_tile_width` 厳守、分割比率計画。
  - `renderer`: `-J` 有無の行整形、差分描画、fps・ドロップ制御。
  - `config`: 既定値・`--config` 優先・exclude の `re.fullmatch` 挙動。
  - `tmuxio`: ドライバ選択（`libtmux`/`cli`）の切替、非侵襲コマンド（`set-option -w`）の検証。
- 統合（軽量）:
  - `libtmux` の pytest プラグイン（`TestServer`）で独立 tmux を起動し、セッション増減・W/H 変化で再レイアウトされることを検証（実行環境の既存 tmux を汚染しない）。

## CLI / 起動・停止
- エントリ: `python -m tmux_dashboard --config <path>`。
- 未指定時: `~/.config/tmux-dashboard/config.yaml` → 無ければ既定値。
- 起動例: 要件 9 に準拠。

## 今後の拡張
- `TerminalDriver` に `curses` 実装を追加。
- `pipe_stream`（FIFO）による低レイテンシ化。
- 差分レイアウト適用（全面再構成の最小化）。
```

---

## 開発環境設計（uv）

本プロジェクトの Python ツールチェーンは Astral の「uv」を標準採用する。

### 目的
- 依存解決と環境同期の高速化（pip/poetry/pip-tools 代替）。
- `uv.lock` による完全再現性と CI の安定化。
- `.venv` に閉じる非侵襲な環境構築と `uv run` による一貫した実行。

### 構成
- `pyproject.toml`：プロジェクトメタデータ・依存定義（PEP 準拠）
- `uv.lock`：ロックファイル（要コミット）
- `.venv/`：プロジェクト専用仮想環境（非コミット）
- 既定 Python：要件は 3.10+。必要に応じ `uv python install 3.12` 等で取得。

### 基本フロー
1. uv インストール
   - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - 代替: `brew install uv` / `winget install --id=astral-sh.uv -e` / `scoop install main/uv` / `pipx install uv`
2. 依存同期
   - `uv sync`（初回は `.venv` 作成、プロジェクトを editable インストール）
   - 厳密再現時は `uv sync --locked`
3. 実行・テスト
   - 実行: `uv run python -m tmux_dashboard --config <path>`
   - テスト: `uv run pytest`
4. 依存の変更
   - 追加/削除: `uv add <pkg>` / `uv remove <pkg>`
   - ロック更新: `uv lock`（全体）／`uv lock --upgrade-package <pkg>`（個別）

### 設定
- venv ディレクトリ: 既定 `.venv`（必要に応じ `UV_PROJECT_ENVIRONMENT` で変更可）
- 開発用依存: PEP 735 の dev グループを利用する場合は `uv sync` で既定導入、除外時は `--no-dev`
- オプション依存（extras）: `uv sync --extra <name>`／`--all-extras`

### CI（GitHub Actions 例）
```yaml
name: CI
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v6
      - name: Sync deps
        run: uv sync --locked --all-extras --dev
      - name: Run tests
        run: uv run pytest -q
```

### 運用ルール
- `uv.lock` は常にコミット。`.venv/` はコミットしない。
- すべてのスクリプト・Make ターゲットは `uv run <cmd>` でラップする（エディタ/CI の整合）。
- uv の仕様変更は上流ドキュメントの更新に追従し、本節を適宜メンテナンスする。
