---
種別: 設計書
機能ID: "fix-tmux-headless-layout"
機能名: "headless tmux でのレイアウト復旧"
関連Issue: ["tmux split-window headless failure analysis"]
状態: "draft"
作成者: "codex"
最終更新: "2026-03-30"
依存: ["requirement.md"]
---

# fix-tmux-headless-layout headless tmux でのレイアウト復旧 — 設計（HOW）

## 目的・制約（要件から転記・圧縮） (必須)
- 目的: headless / detached な tmux 環境でも dashboard の複数 pane レイアウトを安定構成し、失敗時の破壊的退行を防ぐ
- MUST:
  - `split-window -p` 依存を解消する
  - レイアウト失敗時に dashboard を単一 pane に壊さない
  - pane 数不足や分割失敗を可視化する
  - 初回 integrity ノイズを抑える
  - 再現条件をテストで担保する
- MUST NOT:
  - attach 必須運用へ仕様変更しない
  - dashboard 以外の tmux 設定へ侵襲しない
  - unrelated な renderer/UI 変更を混ぜない
- 非交渉制約:
  - 依存追加なし
  - CLI 互換維持
  - `uv run pytest -q` をグリーンにする
- 前提:
  - `-l` ベース分割は headless 実測で成功している
  - `@spec-lite/current/discussions/tmux-split-window-headless-analysis.md` を As-Is の根拠とする

---

## 既存実装/規約の調査結果（As-Is / 95%理解） (必須)
- 参照した規約/実装（根拠）:
  - `AGENTS.md`: spec-lite 運用、TDD、テストファースト、実装前理解ルール
  - `tmux_dashboard/tmuxio.py`: tmux driver 層の API と CLI/libtmux 実装
  - `tmux_dashboard/orchestrator.py`: レイアウト構築、整合性チェック、描画マッピング
  - `tests/test_tmuxio.py`: driver 単体テストの形
  - `tests/test_e2e_tmux.py`: headless E2E と `xfail` 条件
  - `@spec-lite/current/discussions/tmux-split-window-headless-analysis.md`: 実測・外部調査結果
- 観測した現状（事実）:
  - `CliDriver.split_window()` / `split_pane()` は `-p` 固定
  - `LibtmuxDriver.split_window()` / `split_pane()` も `-p` 固定
  - `apply_layout()` は `kill_other_panes()` を先に呼び、失敗時の rollback がない
  - `run_once()` は `zip(tiles_sorted, sessions)` で pane 数不足を黙殺する
  - `check_pane_integrity()` は `apply_titles()` 前に呼ばれる
- 採用するパターン（命名/責務/例外/DI/テストなど）:
  - driver abstraction は維持し、CLI/libtmux の両方に同じ契約を適用する
  - orchestrator は高レベル判断、tmuxio は tmux コマンド差分吸収に責務を分離する
  - 既存の `pytest` ベース単体テスト + headless E2E を拡張する
- 採用しない/変更しない（理由）:
  - renderer / tile プロセス起動ロジックの全面刷新はしない
  - session resolve ロジックや VS Code support のアルゴリズムは今回対象外
- 影響範囲（呼び出し元/関連コンポーネント）:
  - `tmux_dashboard/tmuxio.py`
  - `tmux_dashboard/orchestrator.py`
  - `tmux_dashboard/layout.py`
  - `tests/test_tmuxio.py`
  - `tests/test_orchestrator.py`
  - `tests/test_e2e_tmux.py`

## 主要フロー（テキスト：AC単位で短く） (任意)
- Flow for AC-001:
  1) orchestrator がセッション一覧とウィンドウサイズを取得する
  2) layout が列/行配分と分割長を算出する
  3) tmuxio が `-l` ベースで pane を分割する
  4) pane title を設定し、pane 数と session 数の一致を確認する
- Flow for AC-002:
  1) 既存 pane 詳細を保存する
  2) 新しい分割を段階的に試行する
  3) 途中失敗時は旧状態維持または明示失敗に倒す
  4) 成功時のみ新レイアウトを有効化する
- Flow for AC-003 / AC-004:
  1) 初回サイクルでは title 未設定を許容したうえでタイトル適用を先に行う
  2) その後に integrity を評価する
  3) pane 数不足や split failure は警告ではなく明示的失敗として扱う

## データ・バリデーション（必要最小限） (任意)
- MODEL-001: `SplitLength`
  - Fields: `direction`, `length`, `unit(percent|cells)`
  - Constraints/Validation: `length` は 1 以上、tmux に渡せる文字列へ変換可能であること
- MODEL-002: `LayoutApplyResult`
  - Fields: `success`, `pane_ids`, `error_message`
  - Constraints/Validation: 失敗時は `error_message` 必須

## 判断材料/トレードオフ（Decision / Trade-offs） (任意)
- 論点: `-p` 維持か `-l` 切替か
  - 選択肢A: `-p` 維持 + 起動条件回避
  - 選択肢B: `-l` ベースへ切替
  - 決定: B
  - 理由: 実測で成功し、運用前提を重くしないため
- 論点: `-l` の長さ指定を `%` 優先にするか absolute-cell 優先にするか
  - 選択肢A: `%` 優先
  - 選択肢B: absolute-cell 優先、異常値時のみ `%` fallback
  - 決定: B
  - 理由: `min_tile_width` などセル単位制約と整合し、配分が決定的になるため
- 論点: pane 数不足時の挙動
  - 選択肢A: fail-fast
  - 選択肢B: 縮退継続
  - 決定: 内部処理は A、CLI ループは既存方針に合わせてログ化して継続
  - 理由: テストで確実に失敗検知しつつ、CLI は落ちすぎないほうが利用者体験に合うため
- 論点: 非破壊 apply の実現方式
  - 選択肢A: 同一 window 上で split first / prune last を厳密実装する
  - 選択肢B: dashboard session 内に staging window を作って構築し、成功後に `dashboard:0` と入れ替える
  - 決定: B
  - 理由: tmux の live mutation を避けやすく、失敗時に既存 `dashboard:0` をそのまま保持できるため

## インターフェース契約（ここで固定） (任意)
### 関数・クラス境界（重要なものだけ）
- IF-001: `tmux_dashboard.layout.build_split_lengths(total: int, segments: int) -> list[str]`
  - Input: total width/height と分割数
  - Output: tmux `-l` に渡せる長さ文字列の配列。既定は absolute-cell 文字列（例: `["40", "40"]`）、セル数が不正になる場合のみ `%` fallback を返してよい
  - Errors/Exceptions: 不正な `segments` や `total` に対して `ValueError`
- IF-002: `TmuxIO.split_window(window_target: str, direction: str, length: str) -> None`
  - Input: target, direction, tmux `-l` 互換の長さ文字列
  - Output: なし
  - Errors/Exceptions: tmux コマンド失敗時は driver 由来例外
- IF-003: `TmuxIO.split_pane(pane_id: str, direction: str, length: str) -> None`
  - Input: pane id, direction, tmux `-l` 互換の長さ文字列
  - Output: なし
  - Errors/Exceptions: tmux コマンド失敗時は driver 由来例外
- IF-004: `Orchestrator.apply_layout(window_target: str, columns: int, rows: int) -> LayoutApplyResult`
  - Input: target window と目標 columns/rows
  - Output: success / pane_ids / error_message を持つ結果
  - Errors/Exceptions: 原則 result で返し、異常系は `run_once()` が判断できる形にする
- IF-005: `Orchestrator.validate_mapping(tiles: list[str], sessions: list[str]) -> None`
  - Input: pane id 一覧と session 一覧
  - Output: なし
  - Errors/Exceptions: pane 数不足時に `RuntimeError`

## 変更計画（ファイルパス単位） (必須)
- 追加（Add）:
  - 該当なし
- 変更（Modify）:
  - `tmux_dashboard/layout.py`: absolute-cell 既定 / `%` fallback の `-l` ベース分割長算出関数を追加し、percent split 前提を更新
  - `tmux_dashboard/tmuxio.py`: split API を `length` 指定へ変更し、CLI/libtmux 両方で `-l` を使う
  - `tmux_dashboard/orchestrator.py`: staging window ベースの非破壊レイアウト適用、失敗結果処理、integrity チェック順序、mapping 検証を修正
  - `tests/test_tmuxio.py`: split 呼び出しの期待値を `-l` ベースへ更新
  - `tests/test_orchestrator.py`: apply_layout の非破壊性、pane 数不足、integrity 順序のテストを追加
  - `tests/test_e2e_tmux.py`: headless 条件で `-l` 経路が通ることを検証するケースを追加 / `xfail` を縮小
  - `spec-lite/current/report.md`: 実装ログを追記
- 削除（Delete）:
  - 該当なし
- 移動/リネーム（Move/Rename）:
  - 該当なし
- 参照（Read only / context）:
  - `@spec-lite/current/discussions/tmux-split-window-headless-analysis.md`: 調査結果の参照
  - `tests/test_pane_integrity.py`: 既存 integrity テストの参考

## 主要アルゴリズム / 適用方式 (必須)
- 分割長算出:
  - 既定は absolute-cell を採用する
  - `layout.py` は現在の pane width / height と分割数から各 split の長さをセル数で算出する
  - 算出結果が 0 以下になる場合のみ `%` 文字列へ fallback する
- 非破壊 apply:
  1) `dashboard` session 内に staging 用の一時 window を作成する（例: index 99 または一時名称）
  2) staging window で目標レイアウトを `-l` ベースで構築する
  3) pane 数、pane title 設定可能性、必要な split 成功を確認する
  4) 成功時のみ staging window を `dashboard:0` と入れ替え、旧 window を削除する
  5) 失敗時は staging window を破棄し、既存 `dashboard:0` を保持する
- mapping 検証:
  - staging 完了後に pane 一覧と session 一覧の件数一致を確認する
  - 一致しない場合は swap せず失敗扱いにする
- integrity 判定:
  - title 適用後の staging window に対して判定する
  - 初回起動直後の既定 title は異常扱いしない

## マッピング（要件 → 設計） (必須)
- AC-001 → IF-001, IF-002, IF-003, IF-004, `tmux_dashboard/layout.py`, `tmux_dashboard/tmuxio.py`, `tests/test_e2e_tmux.py`
- AC-002 → IF-004, `tmux_dashboard/orchestrator.py`, `tests/test_orchestrator.py`
- AC-003 → `tmux_dashboard/orchestrator.py`（integrity 順序変更）, `tests/test_pane_integrity.py`, `tests/test_orchestrator.py`
- AC-004 → IF-005, `tmux_dashboard/orchestrator.py`, `tests/test_orchestrator.py`
- EC-001 → `tmux_dashboard/orchestrator.py`, `tests/test_orchestrator.py`
- EC-002 → IF-004, IF-005, `tests/test_orchestrator.py`, `tests/test_e2e_tmux.py`
- EC-003 → `tmux_dashboard/orchestrator.py`, `tests/test_pane_integrity.py`
- EC-004 → `tmux_dashboard/tmuxio.py`, `tests/test_e2e_tmux.py`
- 非交渉制約 → 依存追加なし、CLI 互換維持、TDD を plan / tests で担保

## テスト戦略（最低限ここまで具体化） (任意)
- 追加/更新するテスト:
  - Unit:
    - `tests/test_layout.py`: `-l` 用分割長の算出と端数配分
    - `tests/test_tmuxio.py`: CLI/libtmux の split コマンドが `-l` を使う
    - `tests/test_orchestrator.py`: apply_layout 非破壊性、pane 数不足の明示失敗、integrity 順序
  - Integration:
    - `tests/test_e2e_tmux.py`: headless で `-l` ベース分割により pane が増えること
  - Frontend: 該当なし
- どのAC/ECをどのテストで保証するか:
  - AC-001 → `tests/test_tmuxio.py`, `tests/test_e2e_tmux.py`
  - AC-002 → `tests/test_orchestrator.py`
  - AC-003 → `tests/test_orchestrator.py`, `tests/test_pane_integrity.py`
  - AC-004 → `tests/test_orchestrator.py`
  - EC-001 → `tests/test_orchestrator.py`
  - EC-002 → `tests/test_orchestrator.py`, `tests/test_e2e_tmux.py`
  - EC-003 → `tests/test_pane_integrity.py`, `tests/test_orchestrator.py`
  - EC-004 → `tests/test_e2e_tmux.py`
- 非交渉制約（requirement.md）をどう検証するか:
  - 制約: 依存追加なし
    - 検証方法: `pyproject.toml` を変更しない
  - 制約: CLI 互換維持
    - 検証方法: 既存 CLI テストを回帰させない
  - 制約: グローバル tmux 設定非侵襲
    - 検証方法: 既存 `set-option -w` 系テストを維持
- 実行コマンド（該当するものを記載）:
  - `uv run pytest -q`
  - 必要に応じて `uv run pytest tests/test_tmuxio.py tests/test_orchestrator.py tests/test_e2e_tmux.py -q`
- 変更後の運用（必要なら）:
  - 移行手順: なし
  - ロールバック: 旧 `-p` 経路に戻すのではなく、git 差分単位で戻す
  - Feature flag: なし

## リスク/懸念（Risks） (任意)
- R-001: `-l` の絶対値/比率使い分けが複雑化し、テスト不備があると端数バグを埋め込みやすい
- R-002: libtmux 経由での `-l` 文字列渡しが CLI と微妙に異なる可能性
- R-003: E2E が tmux 環境依存で flake する可能性

## 未確定事項（TBD） (必須)
- Q-001:
  - 質問: staging window の index / name を固定値にするか、一時名称にするか
  - 選択肢:
    - A: 固定 index（例: 99）
    - B: 一時名称ベースで動的に確保する
  - 推奨案（暫定）: B
  - 影響範囲: IF-004 / `orchestrator.py` / `tests/test_orchestrator.py`, `tests/test_e2e_tmux.py`

---

## ディレクトリ/ファイル構成図（変更点の見取り図） (任意)
```text
<repo-root>/
├── tmux_dashboard/
│   ├── layout.py          # Modify: -l ベース分割長算出
│   ├── orchestrator.py    # Modify: staging window / mapping 検証 / integrity 順序
│   └── tmuxio.py          # Modify: split API と staging window 操作
├── tests/
│   ├── test_e2e_tmux.py   # Modify: headless -l E2E
│   ├── test_layout.py     # Modify: 分割長算出テスト
│   ├── test_orchestrator.py # Modify: 非破壊 apply / pane不足
│   └── test_tmuxio.py     # Modify: -l コマンド期待値
└── spec-lite/
    └── current/
        └── report.md      # Modify: 実装ログ
```

## 省略/例外メモ (必須)
- UML 図は今回の変更がローカルな tmux orchestration に閉じており、主要フローをテキストで追えるため省略する
