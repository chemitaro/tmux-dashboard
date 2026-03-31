---
種別: 設計書
機能ID: "fix-tmux-headless-layout"
機能名: "headless tmux でのレイアウト復旧"
関連Issue: ["tmux split-window headless failure analysis", "wrapper create window root cause analysis", "wrapper create-window acceptance review 20260331"]
状態: "draft"
作成者: "codex"
最終更新: "2026-03-31"
依存: ["requirement.md"]
---

# fix-tmux-headless-layout headless tmux でのレイアウト復旧 — 設計（HOW）

## 目的・制約（要件から転記・圧縮） (必須)
- 目的: headless / detached な tmux 環境でも dashboard の複数 pane レイアウトを安定構成し、失敗時の破壊的退行を防ぐ
- MUST:
  - `split-window -p` 依存を解消する
  - wrapper 経路でも `create_window()` が正しく staging window を作れるようにする
  - レイアウト失敗時に dashboard を単一 pane に壊さない
  - pane 数不足や分割失敗を可視化する
  - 初回 integrity ノイズを抑える
  - 再現条件をテストで担保する
  - `swap-window` / `kill-window` failure を default driver でも fail-closed に扱う
  - create failure 後に ghost residual target を残さない
  - 0 セッション収束後の pane title を stale session 名のまま残さない
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
  - `@spec-lite/current/discussions/wrapper-create-window-root-cause-20260331.md` の raw tmux 実験を wrapper 経路の一次原因根拠とする

---

## 既存実装/規約の調査結果（As-Is / 95%理解） (必須)
- 参照した規約/実装（根拠）:
  - `AGENTS.md`: spec-lite 運用、TDD、テストファースト、実装前理解ルール
  - `tmux_dashboard/tmuxio.py`: tmux driver 層の API と CLI/libtmux 実装
  - `tmux_dashboard/orchestrator.py`: レイアウト構築、整合性チェック、描画マッピング
  - `tmux-dashboard`: wrapper の session/window/runner 構成
  - `tests/test_tmuxio.py`: driver 単体テストの形
  - `tests/test_e2e_tmux.py`: headless E2E と `xfail` 条件
  - `@spec-lite/current/discussions/tmux-split-window-headless-analysis.md`: 実測・外部調査結果
  - `@spec-lite/current/discussions/wrapper-create-window-root-cause-20260331.md`: wrapper 固有 root cause の実測
  - `@spec-lite/current/discussions/acceptance-review-wrapper-fix-20260331.md`: 追加修正が必要な受け入れ findings
- 観測した現状（事実）:
  - `CliDriver.split_window()` / `split_pane()` は `-p` 固定
  - `LibtmuxDriver.split_window()` / `split_pane()` も `-p` 固定
  - `CliDriver.create_window()` / `LibtmuxDriver.create_window()` は `new-window -t session_name` を使っている
  - wrapper は `dashboard` session と visible window `dashboard` を作るため、`new-window -t dashboard` が曖昧になり `index 0 in use` で失敗する
  - `LibtmuxDriver.create_window()` は `returncode` / `stderr` を見ず、window が未作成でも requested target を返し得る
  - `LibtmuxDriver.swap_window()` / `kill_window()` も `returncode` / `stderr` を見ず、tmux command failure を silent success にし得る
  - `apply_layout()` は `kill_other_panes()` を先に呼び、失敗時の rollback がない
  - `run_once()` は `zip(tiles_sorted, sessions)` で pane 数不足を黙殺する
  - `check_pane_integrity()` は `apply_titles()` 前に呼ばれる
  - 0 セッション short-circuit は pane 数を 1 つに戻すが、pane title は直前セッション名のまま残り得る
  - create failure path は存在しない staging target でも cleanup / residual 登録を試みる
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
  - `tmux-dashboard`
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
- Flow for AC-005 / AC-006:
  1) wrapper が `dashboard` visible window と runner window を作る
  2) orchestrator が staging 用 window を `create_window()` で確保する
  3) driver は `session:window_index` target で作成し、tmux 戻り値と実在 window を検証する
  4) 作成に失敗した場合は phantom target を返さず、orchestrator が明示失敗として扱う
- Flow for EC-001:
  1) `run_once()` が表示対象 session 0 件を検出する
  2) staging は作らず、`kill_other_panes(window_target)` を実行して `dashboard:0` を明示的に単一 pane へ収束させる
  3) 単一 pane の pane title を空文字に明示更新する
  4) warning を出さず成功扱いで plan を返す
- Flow for EC-008:
  1) `create_window()` が window 未作成のまま失敗する
  2) orchestrator は予測 staging target の実在有無を確認する
  3) 実在しない target には cleanup / residual 登録を行わない
  4) 既存 dashboard を保持したまま error log を残して次サイクルへ戻る

## データ・バリデーション（必要最小限） (任意)
- MODEL-001: `SplitLength`
  - Fields: `direction`, `length`, `unit(percent|cells)`
  - Constraints/Validation: `length` は 1 以上、tmux に渡せる文字列へ変換可能であること
- MODEL-002: `LayoutApplyResult`
  - Fields: `success`, `pane_ids`, `error_message`, `warning_message`, `residual_window_target`
  - Constraints/Validation: 失敗時は `error_message` 必須。swap 後 cleanup 失敗の成功系では `success=True`, `warning_message` 必須, `residual_window_target` に残置した旧 window target を入れる

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
- 論点: wrapper 根本原因への対処
  - 選択肢A: wrapper の visible window 名を変えて曖昧条件を避ける
  - 選択肢B: `create_window()` の tmux target 指定と失敗検知を修正して根治する
  - 決定: B
  - 理由: visible window 名を変えずに direct runner / wrapper の経路差をなくし、driver 契約としても正しくなるため

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
  - Errors/Exceptions: 原則 result で返し、異常系は `run_once()` が判断できる形にする。0 セッション時は `run_once()` 側で short-circuit し、`apply_layout()` に入らない。swap 後 cleanup 失敗は `success=True` と `warning_message` / `residual_window_target` で返す
- IF-005: `Orchestrator.validate_mapping(tiles: list[str], sessions: list[str]) -> None`
  - Input: pane id 一覧と session 一覧
  - Output: なし
  - Errors/Exceptions: pane 数不足時に `RuntimeError`
- IF-006: `TmuxIO.create_window(session_name: str, window_index: int, detached: bool = True, *, width: int | None = None, height: int | None = None) -> str`
  - Input: session 名, 目標 window index, 任意の size
  - Output: 実在する created window target
  - Errors/Exceptions: tmux / libtmux の `new-window` が失敗した場合、または作成後に対象 window 実在確認が取れない場合は例外
  - 契約: `new-window` には `session_name:window_index` target を渡し、phantom target を返さない
- IF-006a: `TmuxIO.swap_window(source_target: str, destination_target: str) -> None`
  - Input: source / destination window target
  - Output: なし
  - Errors/Exceptions: tmux / libtmux の `swap-window` failure は driver 層で必ず例外化する
- IF-006b: `TmuxIO.kill_window(window_target: str) -> None`
  - Input: cleanup 対象 window target
  - Output: なし
  - Errors/Exceptions: tmux / libtmux の `kill-window` failure は driver 層で必ず例外化する
- IF-007: `Orchestrator.run_once(window_target: str = "dashboard:0") -> dict`
  - Input: target window
  - Output: 現在の plan 相当辞書
  - Errors/Exceptions: layout / create / swap failure は内部で捕捉し、dashboard 不変のまま明示ログを残して plan を返す。swap 後 cleanup 失敗は warning を出しつつ成功扱いで進める。0 セッション時は `kill_other_panes(window_target)` により 1 pane へ収束させ、pane title を空文字へ更新したうえで warning なしに short-circuit する
- IF-008: `tmux_dashboard.__main__.main(argv: list[str] | None = None) -> int`
  - Input: CLI 引数
  - Output: exit code
  - Errors/Exceptions: `--once` と通常ループのどちらでも個別サイクル失敗はログ化して継続 / exit 0 とし、KeyboardInterrupt のみ正常終了扱いで 0 を返す

## 変更計画（ファイルパス単位） (必須)
- 追加（Add）:
  - 該当なし
- 変更（Modify）:
  - `tmux_dashboard/layout.py`: absolute-cell 既定 / `%` fallback の `-l` ベース分割長算出関数を追加し、percent split 前提を更新
  - `tmux_dashboard/tmuxio.py`: split API を `length` 指定へ変更し、CLI/libtmux 両方で `-l` を使う。追加で `create_window()` の target 指定と失敗検知を修正する
  - `tmux_dashboard/orchestrator.py`: staging window ベースの非破壊レイアウト適用、失敗結果処理、integrity チェック順序、mapping 検証を修正し、staging 作成失敗を explicit に扱う。追加で ghost residual target 回避と 0 セッション時 title クリアを実装する
  - `tmux-dashboard`: 原則 read-only。wrapper actual-path E2E の再現前提として現行 session/window/runner 構成を維持し、今回の追加修正では変更対象にしない
  - `tests/test_tmuxio.py`: split 呼び出しの期待値を `-l` ベースへ更新し、`create_window()` の契約を追加検証する
  - `tests/test_orchestrator.py`: apply_layout の非破壊性、pane 数不足、integrity 順序、staging 作成失敗のテストを追加
  - `tests/test_e2e_tmux.py`: headless 条件で `-l` 経路が通ることに加え、wrapper と同じ session/window 同名条件を検証するケースを追加する
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
  1) `dashboard` session 内に staging 用の未使用 window index を `_pick_staging_window_index()` で選んで作成する
  2) staging window で目標レイアウトを `-l` ベースで構築する
  3) pane 数、pane title 設定可能性、必要な split 成功を確認する
  4) 成功時のみ `swap-window -s staging_target -t dashboard:0` を行い、swap 後に staging index 側へ移った旧 `dashboard:0` を `kill-window` する
  5) `swap-window` 失敗は swap 前失敗として扱い、新規 staging window を破棄して既存 `dashboard:0` と runner window を保持する
  6) `kill-window` 失敗は swap 後 cleanup 失敗として扱い、新 `dashboard:0` は成功扱いのまま残し、旧 window 残置を warning で観測する
  7) 成功後の invariant は `dashboard:0` が可視 dashboard、runner window は存続、staging 一時 window は cleanup 成功時のみ消える。cleanup 失敗時は旧 window 残置が warning と一致している、の 4 点とする
- residual window retry:
  - cleanup warning で残置した旧 window target は orchestrator が 1 件だけ記憶し、次サイクル冒頭で best-effort に再 `kill-window` を試す
  - 再cleanup 成功時は記憶を消す
  - 再cleanup 失敗時は warning を再記録しつつ、新しい staging は別の未使用 index を選んで進める
  - create failure 直後は `window_exists(target)` 相当の存在確認を通った target だけを residual 対象にする。missing target は warning 補足はしても queue へ積まない
- staging window 作成:
  - `create_window()` は `requested_target = f"{session_name}:{window_index}"` を tmux の `-t` にそのまま渡す
  - CLI driver は subprocess 失敗をそのまま例外化する
  - libtmux driver は `returncode != 0` または `stderr` 非空の失敗を検出し、created target 実在確認を行う
  - created target 実在確認は `list-windows` または `list-panes` で 1 pane 以上あることを確認し、取れなければ例外にする
- mapping 検証:
  - staging 完了後に pane 一覧と session 一覧の件数一致を確認する
  - 一致しない場合は swap せず失敗扱いにする
- integrity 判定:
  - title 適用後の staging window に対して判定する
  - 初回起動直後の既定 title は異常扱いしない
- wrapper 経路:
  - visible window 名 `dashboard` は維持する
  - 修正対象は wrapper 命名ではなく driver 契約と orchestrator の失敗ハンドリングに限定する
- failure observability:
  - driver failure は unit test で例外を観測する
  - `run_once()` failure は dashboard 不変と明示ログで観測する
  - `run_once()` cleanup warning は新 `dashboard:0` 維持 + warning ログ + 残置 window target で観測する
  - CLI failure は `--once` / 通常ループとも exit 0 を維持しつつログで観測する
  - 0 セッション short-circuit は pane 数 1 と pane title 空文字を UI 観測点として固定する
- log contract:
  - create/split/pane-shortage/swap 前 failure は `ERROR` とし、少なくとも `window_target`, `staging_target`（存在する場合）, 根本エラー文字列を含める
  - cleanup warning は `WARNING` とし、少なくとも `window_target`, `residual_window_target`, 根本エラー文字列を含める
  - 0 セッション short-circuit は `WARNING` / `ERROR` を出さず、必要なら `DEBUG` のみとする

## マッピング（要件 → 設計） (必須)
- AC-001 → IF-001, IF-002, IF-003, IF-004, `tmux_dashboard/layout.py`, `tmux_dashboard/tmuxio.py`, `tests/test_e2e_tmux.py`
- AC-002 → IF-004, IF-006a, IF-006b, `tmux_dashboard/orchestrator.py`, `tests/test_orchestrator.py`
- AC-003 → `tmux_dashboard/orchestrator.py`（integrity 順序変更）, `tests/test_pane_integrity.py`, `tests/test_orchestrator.py`
- AC-004 → IF-005, `tmux_dashboard/orchestrator.py`, `tests/test_orchestrator.py`
- AC-005 → IF-006, `tmux-dashboard`, `tmux_dashboard/tmuxio.py`, `tests/test_e2e_tmux.py`
- AC-006 → IF-006, IF-006a, IF-006b, `tmux_dashboard/tmuxio.py`, `tmux_dashboard/orchestrator.py`, `tests/test_tmuxio.py`, `tests/test_orchestrator.py`
- AC-007 → IF-007, `tmux_dashboard/orchestrator.py`, `tests/test_orchestrator.py`, `tests/test_e2e_tmux.py`
- EC-001 → `tmux_dashboard/orchestrator.py`, `tests/test_orchestrator.py`
- EC-002 → IF-004, IF-005, `tests/test_orchestrator.py`, `tests/test_e2e_tmux.py`
- EC-003 → `tmux_dashboard/orchestrator.py`, `tests/test_pane_integrity.py`
- EC-004 → `tmux_dashboard/tmuxio.py`, `tests/test_e2e_tmux.py`
- EC-005 → IF-006, `tmux_dashboard/tmuxio.py`, `tests/test_tmuxio.py`, `tests/test_e2e_tmux.py`
- EC-006 → IF-006, `tmux_dashboard/tmuxio.py`, `tmux_dashboard/orchestrator.py`, `tests/test_tmuxio.py`, `tests/test_orchestrator.py`
- EC-007 → `tmux_dashboard/orchestrator.py`, `tests/test_orchestrator.py`
- EC-008 → IF-006, IF-007, `tmux_dashboard/orchestrator.py`, `tests/test_orchestrator.py`
- 非交渉制約 → 依存追加なし、CLI 互換維持、TDD を plan / tests で担保

## テスト戦略（最低限ここまで具体化） (任意)
- 追加/更新するテスト:
  - Unit:
    - `tests/test_layout.py`: `-l` 用分割長の算出と端数配分
    - `tests/test_tmuxio.py`: CLI/libtmux の split コマンドが `-l` を使う
    - `tests/test_tmuxio.py`: `create_window()` が `session:window_index` target を使い、libtmux 失敗を phantom target にしない
    - `tests/test_orchestrator.py`: apply_layout 非破壊性、pane 数不足の明示失敗、integrity 順序、staging 作成失敗
    - `tests/test_orchestrator.py`: `swap-window` 成功後に `kill-window` が失敗した場合、`LayoutApplyResult.warning_message` と `residual_window_target` を返しつつ新 `dashboard:0` を維持する
    - `tests/test_orchestrator.py`: 残置 window を次サイクルで best-effort cleanup し、再失敗でも新規 staging 適用を妨げない
    - `tests/test_tmuxio.py`: libtmux `swap_window()` / `kill_window()` が tmux failure を例外化する
    - `tests/test_orchestrator.py`: create failure で missing staging target を residual queue に積まない
    - `tests/test_orchestrator.py`: 0 セッション時に pane title が空文字へクリアされる
  - Integration:
    - `tests/test_e2e_tmux.py`: headless で `-l` ベース分割により pane が増えること
    - `tests/test_e2e_tmux.py`: wrapper と同じ `session/window same-name` 条件でも direct runner と wrapper の両方が通ること
    - `tests/test_e2e_tmux.py`: wrapper 起動後に全対象セッションを削除すると `dashboard:0` が 1 pane かつ空 title へ収束すること
  - Frontend: 該当なし
- どのAC/ECをどのテストで保証するか:
  - AC-001 → `tests/test_tmuxio.py`, `tests/test_e2e_tmux.py`
  - AC-002 → `tests/test_orchestrator.py`
  - AC-002 → `tests/test_orchestrator.py`（swap 前 failure / swap 後 cleanup warning の両分岐）
  - AC-003 → `tests/test_orchestrator.py`, `tests/test_pane_integrity.py`
  - AC-004 → `tests/test_orchestrator.py`
  - AC-005 → `tests/test_e2e_tmux.py`
  - AC-006 → `tests/test_tmuxio.py`, `tests/test_orchestrator.py`
  - AC-007 → `tests/test_orchestrator.py`, `tests/test_e2e_tmux.py`
  - EC-001 → `tests/test_orchestrator.py`
  - EC-002 → `tests/test_orchestrator.py`, `tests/test_e2e_tmux.py`
  - EC-003 → `tests/test_pane_integrity.py`, `tests/test_orchestrator.py`
  - EC-004 → `tests/test_e2e_tmux.py`
  - EC-005 → `tests/test_tmuxio.py`, `tests/test_e2e_tmux.py`
  - EC-006 → `tests/test_tmuxio.py`, `tests/test_orchestrator.py`
  - EC-007 → `tests/test_orchestrator.py`
  - EC-008 → `tests/test_orchestrator.py`
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
- R-004: wrapper と direct runner の起動経路差を十分にテストしないと、今後も片側だけ壊れる可能性

## 未確定事項（TBD） (必須)
- 該当なし

---

## ディレクトリ/ファイル構成図（変更点の見取り図） (任意)
```text
<repo-root>/
├── tmux_dashboard/
│   ├── layout.py          # Modify: -l ベース分割長算出
│   ├── orchestrator.py    # Modify: staging window / mapping 検証 / integrity 順序 / create failure handling
│   └── tmuxio.py          # Modify: split API と staging window 作成契約
├── tests/
│   ├── test_e2e_tmux.py   # Modify: headless -l E2E + wrapper same-name regression
│   ├── test_layout.py     # Modify: 分割長算出テスト
│   ├── test_orchestrator.py # Modify: 非破壊 apply / pane不足 / create failure
│   └── test_tmuxio.py     # Modify: -l コマンド期待値 + create_window 契約
└── spec-lite/
    └── current/
        └── report.md      # Modify: 実装ログ
```

## 省略/例外メモ (必須)
- UML 図は今回の変更がローカルな tmux orchestration に閉じており、主要フローをテキストで追えるため省略する
