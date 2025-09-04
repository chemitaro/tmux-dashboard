# tmux ダッシュボード 要件定義書（Codex CLI 向け / 正式版 v1.1）

> **目的**：この文書は Codex CLI（自律開発エージェント）が、本ツールを実装・テスト・出荷するための**唯一の仕様源**です。  
> **中心思想**：俯瞰性・可読性（左下起点＋カラー）・非侵襲（環境非汚染）・安定実用。

---

## 目次
- [1. 背景と思想](#1-背景と思想)
- [2. スコープと対象](#2-スコープと対象)
- [3. ユースケース](#3-ユースケース)
- [4. 振る舞い仕様（ビヘイビア）](#4-振る舞い仕様ビヘイビア)
- [5. 機能要件](#5-機能要件)
- [6. 非機能要件](#6-非機能要件)
- [7. 技術仕様（方式A：キャプチャ＋レンダラー）](#7-技術仕様方式aキャプチャレンダラー)
- [8. 設定仕様（YAML）](#8-設定仕様yaml)
- [9. 運用（起動・停止・常時最新化）](#9-運用起動停止常時最新化)
- [10. テスト計画（受け入れ基準）](#10-テスト計画受け入れ基準)
- [11. リスクと対策](#11-リスクと対策)
- [12. 実装ガイド（Codex CLI への指示）](#12-実装ガイドcodex-cli-への指示)
- [13. 付録A：tmux コマンド参照](#13-付録atmux-コマンド参照)
- [14. 用語集](#14-用語集)
 - [15. 開発環境・環境構築（uv）](#15-開発環境環境構築uv)

---

## 1. 背景と思想
- **背景**：CLI 型コーディングエージェントを含む複数の tmux セッションが同時進行で出力を生成。全体の“いま”を一望する必要がある。
- **思想（目的）**
  - **俯瞰性**：全セッションの最新状態を 1 画面で一覧。
  - **可読性**：**左下起点**（下端の新着ログ重視）＋**カラー保持**で意味を損なわない。
  - **非侵襲／環境非汚染**：**既存 tmux 設定（~/.tmux.conf 等）を変更しない**。対象セッションの状態・レイアウトを壊さない。
  - **安定実用**：秒オーダの反映で十分。滑らかさと負荷のバランス最適化。

---

## 2. スコープと対象
- **対象**：同一マシン上の全 **tmux セッション**。
- **本ツール**：`dashboard` という **tmux セッション**として起動。**自身（dashboard）は一覧から除外**。
- **OS**：Linux / macOS。
- **tmux**：**3.2+ を前提（最新安定版を推奨）**。
- **実装言語**：**Python 3.10+**。
- **実行形態**：`dashboard` セッション内で Python のオーケストレータが**常駐**し、最新状態を**継続更新**。

---

## 3. ユースケース
### UC-1：新規セッションの自動反映
1. 利用者が新規セッション `alpha` を起動。  
2. `dashboard` のポーリング（既定 2 秒）で検出。  
3. ASCII 昇順で再ソート → レイアウト再計算 → タイル追加。  
4. タイル上部に `alpha`、内容領域に**カラー付き**の**下端 H 行**が即時表示。

### UC-2：セッション削除の自動反映
1. `beta` が終了。  
2. 次回ポーリングで消滅を検知 → タイル削除 → グリッド再計算。  
3. **min_tile_width** を下回らない列数で自動再配置。

### UC-3：ダッシュボードのリサイズ
1. `dashboard` ウィンドウを縦長に変更。  
2. 次回ポーリングで `window_width/height` 変化を検知 → 列数再計算 → 再配置。  
3. 各タイル内レンダラーは `SIGWINCH` で **W/H 再取得**し **即時再描画**。

### UC-4：高スループット出力（コーディングエージェント）
- 高頻度出力でも、各タイルは **差分描画**＋**fps 上限（デフォ 30fps）**で**滑らか**に追従。  
- キュー輻輳時には**古いフレームを破棄**し、**常に最新の下端**を優先表示。

---

## 4. 振る舞い仕様（ビヘイビア）
- **並び順**：セッション名の **ASCII 昇順**で固定。
- **ラベル**：各タイル上部に **セッション名**（pane border）を表示。
- **内容領域**：**左から W 列 × 下端 H 行**＝**左下起点**。
- **カラー**：ANSI カラー（TrueColor 推奨）を保持。
- **入力**：不可（**閲覧専用**）。
- **反映レイテンシ**：追加／削除／リサイズの反映 ≤ **3 秒**（設定で短縮可）。
- **環境非汚染**：グローバル設定変更禁止。**`set -g` は使わず `-w` で `dashboard:0` のウィンドウ限定設定**。対象セッションの設定・レイアウトに副作用なし。

### 4.1 レイアウト挙動シミュレーション（代表ケース）
前提規則（要点抜粋）:
- 列数: `columns = max(1, min(N, floor(window_width / min_tile_width)))`
- 行数: `rows = ceil(N / columns)`
- 分割: 水平（列）→ 垂直（行）の順に分割。百分率は `floor(100/C)`/`floor(100/R)` を基準にし、端数は末尾で吸収（最後の列/行に加算）。
- マッピング: セッション名のASCII昇順で、左→右、上→下に割り当て（行優先）。空セルは生成しない（N個のみ）。

ケースA
- 入力: `window_width=120`, `min_tile_width=40`, `N=3`
- 計算: `columns=floor(120/40)=3` → `min(N,3)=3`、`rows=ceil(3/3)=1`
- 結果: 横3×縦1。水平比率: 33%, 33%, 34%。縦は1段。

ケースB
- 入力: `window_width=120`, `min_tile_width=40`, `N=4`
- 計算: `columns=3`、`rows=ceil(4/3)=2`
- 結果: 横3×縦2（実際の生成は4タイル）。1段目: 3タイル、2段目: 左端1タイルのみ。
  - 水平比率: 33%, 33%, 34%。
  - 垂直比率（各列）: 50%/50%（端数は末尾吸収）。未使用セルは生成しないため、2段目は左列のみ分割される。

ケースC
- 入力: `window_width=79`, `min_tile_width=40`, `N=2`
- 計算: `floor(79/40)=1` → `columns=1`、`rows=ceil(2/1)=2`
- 結果: 横1×縦2（縦に2分割）。水平100%、垂直は50%/50%。

ケースD
- 入力: `window_width=200`, `min_tile_width=60`, `N=5`
- 計算: `floor(200/60)=3` → `columns=3`、`rows=ceil(5/3)=2`
- 結果: 横3×縦2（実生成5タイル）。1段目: 3、2段目: 2（左から）。
  - 水平比率: 33%, 33%, 34%。
  - 垂直比率: 50%/50%（各列で末尾吸収）。

ケースE
- 入力: `window_width=200`, `min_tile_width=100`, `N=3`
- 計算: `floor(200/100)=2` → `columns=2`、`rows=ceil(3/2)=2`
- 結果: 横2×縦2（実生成3タイル）。1段目: 2、2段目: 左1。
  - 水平比率: 50%, 50%。
  - 垂直比率: 50%/50%。

ケースF
- 入力: `window_width=160`, `min_tile_width=45`, `N=7`
- 計算: `floor(160/45)=3` → `columns=3`、`rows=ceil(7/3)=3`
- 結果: 横3×縦3（実生成7タイル）。
  - 1段目: 3（左→右）
  - 2段目: 3（左→右）
  - 3段目: 1（左のみ）
  - 水平比率: 33%, 33%, 34%。垂直比率: 33%, 33%, 34%。

ケースG（列数>セッション数は抑制）
- 入力: `window_width=120`, `min_tile_width=40`, `N=1`
- 計算: `columns=min(3, N)=1`、`rows=1`
- 結果: 横1×縦1（不要な空列は作らない）。

ケースH（`window_width < min_tile_width`）
- 入力: `window_width=30`, `min_tile_width=40`, `N=4`
- 計算: `floor(30/40)=0` → `columns=max(1, min(4, 0))=1`、`rows=4`
- 結果: 横1×縦4（縦に積む）。

備考
- 百分率丸めにより、列・行の末尾に1〜数%の端数が集約される（見た目の総和は100%）。
- マージン・ボーダーはtmuxのpane border設定に依存し、`pane_height`はコンテンツ領域の行数（原則）である。

---

## 5. 機能要件
### 5.1 セッション検出
- `tmux list-sessions -F "#{session_name}"` で列挙。  
- 除外：`^dashboard$` 固定＋ `exclude_patterns`（設定）。  
- ソート：ASCII 昇順。  
- 間隔：`poll_interval_sec`（デフォ **2 秒**）。

### 5.2 ウィンドウサイズ検出
- `tmux display-message -p -t dashboard:0 "#{window_width} #{window_height}"`。  
- 間隔：セッション検出と同一サイクル。

### 5.3 レイアウト
- 入力：`window_width/height`、セッション数、`min_tile_width`。  
- 算出：  
  - `columns = max(1, floor(window_width / min_tile_width))`  
  - `rows = ceil(num_sessions / columns)`  
- 制約：**min_tile_width 未満**のタイル幅を作らない。  
- 差分がある時のみ panes を再構成（初版は一括）。

### 5.4 タイルのタイトル（環境非汚染）
- **`dashboard` のウィンドウ限定設定**：  
  - `tmux set-option -w -t dashboard:0 pane-border-status top`  
  - `tmux set-option -w -t dashboard:0 'pane-border-format' '#{pane_title}'`  
  - 各 pane へ：`tmux select-pane -t <pane_id> -T "<session_name>"`

### 5.5 内容表示（左下起点・カラー保持・閲覧専用）
- **初期フィル**：  
  - `tmux capture-pane -p -e -J -S -<H> -E -1 -t <pane_id>`  
- **継続更新（デフォルト）**：`capture-only`（非侵襲）  
  - レンダラーが一定周期で `capture-pane` を実行しリングバッファ更新。  
- **オプション**：`pipe_stream`（任意）  
  - `tmux pipe-pane -o -t <pane_id> "cat > <fifo>"` でストリーミング受信 → より滑らかに。  
  - 既定は **false**（環境非汚染を最優先）。
  
 追加仕様：
 - **H の定義**：H は「タイル pane の描画可能行数（見出し行を除く）」とし、`tmux display-message -p -t <tile_pane_id> "#{pane_width} #{pane_height}"` の `pane_height` を採用。  
 - **折返し結合の可否**：`-J` は既定で有効。設定 `viewer.join_wrapped_lines: true|false` により切替（既定 true）。

### 5.6 表示対象 pane の選択規則（決定版）
- 原則：「各セッションのアクティブ window のアクティブ pane」を優先。決定不能時も決定的（deterministic）。
- 手順：
  1. そのセッション内で `window_active==1` の window があれば採用。無ければ `window_index` の最小を採用。  
     取得例：`tmux list-windows -t <session> -F "#{window_index} #{window_active}"`
  2. 採用した window 内で `pane_active==1` の pane を採用。無ければ `pane_index` の最小を採用。  
     取得例：`tmux list-panes -t <session>:<win_idx> -F "#{pane_index} #{pane_active} #{pane_id}"`
  3. 採用 pane の `pane_id` を対象としてキャプチャ（レンダラーはこの pane の出力を表示）。
  
理由：複数クライアント接続や detatch 状態でも一貫して決定可能。

### 5.7 dashboardセッション管理（自動復旧）
- **セッション存在確認**：各ポーリングサイクルで `dashboard` セッションの存在を確認。
- **自動再作成**：`dashboard` セッションが存在しない場合、自動的に新規作成。
  - `tmux new-session -d -s dashboard` で detached モードで作成。
  - 作成時はターミナルに `[tmux-dashboard] Recreated dashboard session` を表示。
- **エラーハンドリング**：
  - `window_size()` 等の tmux コマンド実行時にセッション不在エラーをキャッチ。
  - セッション再作成後、同一サイクル内でレイアウト構築を再実行。
  - レンダラーは新規 pane で自動的に再起動される（レイアウト再構築時）。
- **復旧頻度**：ユーザー操作による削除を想定（頻繁ではない）。

---

## 6. 非機能要件
- **レイテンシ**：構成変更の反映 ≤ **3 秒**。
- **滑らかさ**：高出力時も体感カクつきなし（30fps 上限＋差分描画＋最新優先）。
- **安定性**：tmux コマンド失敗は指数バックオフで再試行。
- **可搬性**：Linux / macOS 同等動作。
- **セキュリティ**：ローカル実行のみ。外部通信なし。
- **可観測性**：再レイアウト回数、描画 fps、ドロップ率、エラーをログ出力。
- **環境非汚染**：`~/.tmux.conf` 変更なし、プラグイン不要、**`set -g` 禁止**。設定は `dashboard` 内に限定。
- **ログローテーション**：既定で 10MB × 5 世代（RotatingFileHandler 相当）。保存先は `~/.local/state/tmux-dashboard`。

---

## 7. 技術仕様（方式A：キャプチャ＋レンダラー）
### 7.1 コンポーネント
- **Orchestrator（Python）**：セッション検出、ウィンドウ寸法取得、レイアウト計算、pane 作成／破棄、pane タイトル設定、各タイル用レンダラー起動。
- **Tile Renderer（Python／ANSI直描画を既定、curses は任意）**：初期 `capture-pane`、以降 `capture-only` 周期更新（任意で `pipe_stream`）。差分描画＋fps 上限。端末抽象は `TerminalDriver`（`ansi` 既定、`curses` 代替）。

### 7.2 初期フィル
```
tmux capture-pane -p -e -J -S -<H> -E -1 -t <pane_id>
# -e: ANSI保持, -J: 折返し結合, -E -1: 最下行, -S -<H>: 下からH行
```

### 7.3 継続更新
- `capture-only`：一定周期で `capture-pane` → リングバッファ更新。
- `pipe_stream`（任意）：FIFO へストリーム出力、レンダラーが非同期読取。保持不可環境では自動で `capture-only` へ。
  - 初回出荷（MVP）は `capture-only` を既定。`pipe_stream` は後続機能フラグとして提供。

### 7.4 レンダリング
- ANSI は幅 0、`wcwidth` で見かけ幅計算、**W 列×H 行**に整形（右端切り捨て）。
- **差分描画**（行ハッシュ）、**max_fps=30**、**古いフレーム破棄**（最新優先）。
- 各行末に `\x1b[0m` を付与（SGR リセット）。
- `SIGWINCH` で自 pane の W/H を再取得し即時再描画。

---

## 8. 設定仕様（YAML）
```yaml
min_tile_width: 40
poll_interval_sec: 2
exclude_patterns:
  - "^dashboard$"

pane_border_enabled: true
pane_border_format: "#{pane_title}"   # dashboard:0 のウィンドウにのみ適用

tmux:
  driver: "libtmux"         # "libtmux" または "cli"（サブプロセス直叩き）
  socket_name: null          # 必要時のみ指定（例: "default"）
  socket_path: null          # 例: "/tmp/tmux-1000/default"

viewer:
  mode: "capture-only"      # 既定。環境非汚染を最優先
  pipe_stream: false        # true で pipe-pane を使用（任意）
  join_wrapped_lines: true  # capture-pane の -J を有効（false で無効化）
  max_fps: 30
  drop_stale_frames: true
  wrap_mode: "clip-right"
  truecolor: true

logging:
  level: "INFO"
  dir: "~/.local/state/tmux-dashboard"
  rotate_max_bytes: 10485760   # 10MB
  rotate_backup_count: 5
```

### 8.1 設定ロードの優先順位
1. `--config <path>` 明示指定が最優先。
2. 既定パス `~/.config/tmux-dashboard/config.yaml` が存在すれば読み込み。
3. 上記いずれも無ければ、組み込み既定値を使用。

### 8.2 除外パターンの解釈
- `exclude_patterns` は Python の正規表現で評価し、`re.fullmatch` によりセッション名全体との完全一致で判定。  
- 大文字小文字は区別（既定）。必要に応じてパターン側で `(?i)` を利用（将来の拡張で `ignore_case` を検討）。

### 8.3 tmux ドライバ選択
- `tmux.driver` は `libtmux` を既定とする。利点：
  - オブジェクト指向API（Session/Window/Pane）で安全に操作可能。
  - `capture-pane` や `set-option -w` 等の生コマンドは `obj.cmd()` で明示的に呼び出し可能。
  - libtmux の pytest プラグイン（`TestServer`）により、テスト用の独立サーバを容易に構築可能（既存環境を汚染しない）。
- `cli` を選択すると、サブプロセスで `tmux` コマンドを直接実行する実装に切り替わる。
- いずれのドライバでも**非侵襲**原則（`set -g` 禁止、`dashboard:0` 窓限定の `-w` 設定）を遵守する。

---

## 9. 運用（起動・停止・常時最新化）
### 起動例
```bash
tmux new-session -d -s dashboard    # 無ければ作成
tmux send-keys -t dashboard:0 'python -m tmux_dashboard --config ~/dashboard.yaml' C-m
tmux attach -t dashboard            # 閲覧開始
```
- `dashboard` を表示している限り、Python 常駐プログラムが**最新状態を維持**。
- プログラム起動時に `dashboard` セッションが存在しない場合は自動作成。

### 自動復旧
- **dashboardセッション消失時**：ユーザーが誤って `tmux kill-session -t dashboard` を実行しても、次のポーリングサイクルで自動復旧。
- **復旧動作**：
  1. セッション不在を検出
  2. 新規 `dashboard` セッションを作成（detached）
  3. レイアウト・タイトル・レンダラーを再構築
  4. ターミナルに復旧メッセージを表示
- **継続性**：Python プロセスは停止せず、エラーをハンドリングして継続動作。

### 停止
```bash
# オーケストレータを終了（Ctrl-C）または
tmux kill-session -t dashboard
```

---

## 10. テスト計画（受け入れ基準）
1. **並び順**：常に ASCII 昇順。  
2. **左下起点**：全タイルが常に **下端 H 行 × 左基準 W 列**。  
3. **カラー**：ANSI 色（256色／TrueColor）の整合。  
4. **反映**：追加／削除／リサイズ ≤ 3 秒。  
5. **滑らかさ**：高出力時でも顕著なカクつき無し（ドロップ率・平均 fps をログで確認）。  
6. **min_tile_width**：未満にならない列数で配置。  
7. **非侵襲**：対象セッションの設定・レイアウトが変化しない（pipe_stream=false で検証）。  
8. **ログ**：差分検出・再レイアウト・fps・ドロップ率・例外が記録される。  
9. **自動復旧**：`dashboard` セッション削除後、3秒以内に自動再作成されレイアウトが復元される。

---

## 11. リスクと対策
| リスク | 影響 | 対策 |
|---|---|---|
| 多セッション×高出力で負荷上昇 | CPU/IO増、遅延 | max_fps 上限、差分描画、キュー破棄、`capture-only` 維持。必要なら `pipe_stream=true` は任意で使用。 |
| ANSI/全角の幅計算誤差 | 右端崩れ | `wcwidth` ベース、行末 SGR リセット、ユニットテスト。 |
| TrueColor 非対応端末 | 色再現低下 | 256色へフォールバック。 |
| pipe 使用時の侵襲懸念 | pane 状態変更（**一時的**） | 既定は **false**。ON 時も終了フックで必ず解除。 |
| dashboardセッション消失 | プログラム停止 | 各サイクルで存在確認、自動再作成、エラーハンドリングによる継続動作。 |

---

## 12. 実装ガイド（Codex CLI への指示）
### 12.1 期待する成果物
- Python パッケージ `tmux_dashboard/`（モジュール本体）
- エントリポイント：`python -m tmux_dashboard --config <path>`
- 設定テンプレート：`configs/dashboard.example.yaml`
- ログ出力一式：`~/.local/state/tmux-dashboard`（既定）
- ドキュメント：`README.md`、`docs/`（本ファイルは `docs/requirements.md` として保存）
- ユニットテスト：ANSI 幅計算・差分描画・レイアウト計算

### 12.2 推奨ディレクトリ構成
```
tmux-dashboard/
├─ tmux_dashboard/
│  ├─ __init__.py
│  ├─ orchestrator.py      # セッション検出・レイアウト・pane管理
│  ├─ renderer.py          # タイル内レンダラー（curses/ANSI処理）
│  ├─ tmuxio.py            # tmux コマンド I/O ラッパ
│  ├─ layout.py            # 列数/行数計算・差分判定
│  ├─ config.py            # 設定ロード/バリデーション
│  ├─ logging_setup.py
│  └─ utils_wcwidth.py     # 幅計算ユーティリティ
├─ tests/
│  ├─ test_layout.py
│  ├─ test_ansi_width.py
│  └─ test_diff_render.py
├─ configs/
│  └─ dashboard.example.yaml
├─ docs/
│  └─ requirements.md      # ← 本ファイル
└─ README.md
```

### 12.3 実装のキーポイント
- **グローバル設定変更禁止**：`set -g` は使わない。`set-option -w -t dashboard:0` のみ。
- **ラベル表示**：`pane-border-format` は `#{pane_title}` を使い、各 pane に `select-pane -T` でタイトルを設定。
- **左下起点**：`capture-pane` は常に `-E -1`（最下行）＋ `-S -<H>`（下から H 行）を使う。
- **滑らかさ**：差分描画＋ `max_fps` 上限＋**最新優先**キュー制御。
- **ユニットテスト**：日本語・絵文字・複合文字含む幅計算の正当性、ANSI リセットの健全性。

---

## 13. 付録A：tmux コマンド参照
- セッション列挙：`tmux list-sessions -F "#{session_name}"`
- pane 列挙：`tmux list-panes -a -F "#{session_name} #{pane_id} #{pane_active}"`
- ウィンドウ寸法：`tmux display-message -p -t dashboard:0 "#{window_width} #{window_height}"`
- 初期フィル：`tmux capture-pane -p -e -J -S -<H> -E -1 -t <pane_id>`
- タイトル：
  - `tmux set-option -w -t dashboard:0 pane-border-status top`
  - `tmux set-option -w -t dashboard:0 'pane-border-format' '#{pane_title}'`
  - `tmux select-pane -t <pane_id> -T "<session_name>"`
- レイアウト（例）：`tmux split-window -h/-v -p <percent>`、`tmux kill-pane -a -t dashboard:0`

---

## 14. 用語集
- **左下起点**：表示矩形が**左端 W 列 × 下端 H 行**に切り出されること。
- **W 列 / H 行**：タイルの幅（セル数）／高さ（行数）。
- **ANSI カラー**：SGR 制御文字列による色表現（TrueColor 含む）。
- **環境非汚染**：既存の tmux 設定・レイアウトに恒久的変更を与えない設計方針。

---

## 15. 開発環境・環境構築（uv）

本プロジェクトの Python 環境と依存関係管理は、Astral の「uv」を標準ツールとして採用する。

### 15.1 方針（WHAT）
- **公式採用**：開発・CI ともに `uv` を用いた環境構築・依存解決・ロック運用を行う。
- **再現性**：`uv.lock` をソース管理に含め、`uv sync --locked` により正確な再現を担保。
- **非侵襲**：ローカル venv はリポジトリ直下の `.venv`（既定）を使用。グローバル環境へはインストールしない。
- **互換**：プロジェクトのメタデータは `pyproject.toml` に集約し、PEP 準拠とする。

### 15.2 受け入れ基準
1. 初回セットアップが以下で完了すること。
   - macOS/Linux:
     - `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows:
     - `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. `uv --version` が実行可能である。
3. Python が未整備でも `uv python install <version>` で取得・切替できる（例：`uv python install 3.12`）。
4. `pyproject.toml` と `uv.lock` を基に `uv sync --locked` が成功し、`.venv` が作成される。
5. テスト・実行系が `uv run` 経由で問題なく動作する（例：`uv run pytest`、`uv run python -m tmux_dashboard ...`）。

### 15.3 開発者向けセットアップ手順（概要）
1. `uv` のインストール（推奨：スタンドアロンスクリプト）
   - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - 代替: Homebrew `brew install uv` / WinGet `winget install --id=astral-sh.uv -e` / Scoop `scoop install main/uv` / PyPI（推奨は pipx）`pipx install uv`
   - アップデート: `uv self update`
2. Python の用意（必要に応じて）
   - 例: `uv python install 3.12`／複数: `uv python install 3.11 3.12`
3. 依存関係の同期（初回／変更時）
   - `uv sync`（既定でプロジェクトを editable インストール）
   - 厳密再現: `uv sync --locked`
4. 実行・テスト
   - `uv run python -m tmux_dashboard --config <path>`
   - `uv run pytest`

### 15.4 運用上の約束事
- `uv.lock` を必ずコミットする。`.venv/` はコミットしない。
- 依存追加・削除は `uv add <pkg>` / `uv remove <pkg>` を使用し、必要に応じて `uv lock` を更新。
- 開発用依存（dev グループ）は `uv sync` で既定インストール。不要時は `--no-dev` を選択。
- CI では `uv sync --locked --all-extras --dev` を基本とし、実行は `uv run <cmd>` を用いる。

### 15.5 参考（公式ドキュメント準拠）
- インストール（macOS/Linux）: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- インストール（Windows）: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Python 管理: `uv python install <version>`／`uv python list`
- 同期: `uv sync`／ロック作成: `uv lock`／厳密同期: `uv sync --locked`
- 実行: `uv run <cmd>`／一時ツール: `uvx <tool>`

注: uv は頻繁に更新されるため、詳細・オプションは公式ドキュメントに従うこと（機能差分が出た場合は本節を適宜更新）。
