# タイル配置順序の変更分析（横優先から縦優先へ）

## 現在の実装の理解（95%以上の理解度）

### 1. 現在の配置ロジック

#### 配置順序：行優先（Row-Major）
```
3列×2行の例:
+---+---+---+
| A | B | C |  ← 1行目を左から右へ
+---+---+---+
| D | E |     |  ← 2行目を左から右へ
+---+---+---+
```

#### 実装箇所
1. **layout.py**
   - `tile_positions()`: 行優先で(row, col)座標を生成
   ```python
   for r in range(rows):      # 外側ループ：行
       for c in range(columns): # 内側ループ：列
   ```

2. **orchestrator.py**
   - paneソート: `sorted(details, key=lambda x: (x[2], x[1]))`
   - x[2]=top（Y座標）、x[1]=left（X座標）
   - (top, left)順 = 行優先でソート

### 2. tmux pane分割の仕組み

#### 分割順序
1. 水平分割（`split-window -h`）で列を作成
2. 各列で垂直分割（`split-window -v`）で行を作成

#### pane座標システム
- `pane_left`: 左端からのX座標
- `pane_top`: 上端からのY座標
- `pane_id`: %番号形式の一意識別子

## 要望：列優先（Column-Major）配置

### 期待される配置
```
3列×2行の例:
+---+---+---+
| A | C | E |  ← 各列の上から下へ
+---+---+---+
| B | D |     |  ← 続きを次の列へ
+---+---+---+
```

## 技術的な解決方法の比較

### 方法1: 完全な列優先実装（推奨度：★★★★★）

**変更内容:**
1. `layout.tile_positions()`を列優先に変更
2. paneソートを`(left, top)`に変更
3. テストを更新

**利点:**
- ロジックが一貫している
- コードの意図が明確
- 保守性が高い

**欠点:**
- テストの更新が必要（ただし軽微）

**実装の詳細:**
```python
# layout.py
def tile_positions(n: int, columns: int, rows: int) -> List[Tuple[int, int]]:
    """列優先（上→下、左→右）で N 個の (row, col) を返す。"""
    out = []
    count = 0
    for c in range(columns):    # 外側：列
        for r in range(rows):    # 内側：行
            if count >= n:
                return out
            out.append((r, c))
            count += 1
    return out

# orchestrator.py (2箇所)
panes_sorted = sorted(details, key=lambda x: (x[1], x[2]))  # (left, top)
```

### 方法2: paneソートのみ変更（推奨度：★★☆☆☆）

**変更内容:**
- paneソートのみ`(left, top)`に変更
- `tile_positions`は変更しない

**利点:**
- 変更箇所が最小限
- 既存テストへの影響なし

**欠点:**
- ロジックの不整合（tile_positionsは行優先、実際の配置は列優先）
- コードの意図が不明確
- 将来の保守で混乱を招く

### 方法3: 設定オプション追加（推奨度：★★★☆☆）

**変更内容:**
- configに`tile_ordering: "row-major" | "column-major"`を追加
- 両方のロジックを実装

**利点:**
- ユーザーが選択可能
- 後方互換性を保持

**欠点:**
- コードの複雑性が増す
- テストケースが倍増
- 実装・保守コストが高い

## ベストプラクティスの提案

### 推奨：方法1（完全な列優先実装）

**理由:**
1. **コードの一貫性**: tile_positionsとpaneソートの両方が列優先で統一
2. **明確な意図**: コメントとコードが一致し、理解しやすい
3. **保守性**: 将来の開発者が混乱しない
4. **シンプル**: 条件分岐がなく、実装が簡潔

**実装計画:**
1. `layout.tile_positions()`のループ順序を変更
2. `orchestrator.py`の2箇所でソートキーを変更
3. コメントを「列優先」に更新
4. テストケースを列優先に更新
5. 統合テストで動作確認

**影響範囲:**
- layout.py: 1関数
- orchestrator.py: 2箇所（同一パターン）
- test_layout.py: 1テストケース
- ドキュメント: コメントの更新

この方法により、要望通りの縦方向優先（列優先）配置が実現され、コードの品質と保守性も向上します。