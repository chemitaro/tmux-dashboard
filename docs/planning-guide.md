# Planning Directory Guide

## 概要

プロジェクト開発は要件定義から実装報告まで4つのドキュメントで管理され、明確な進捗管理と品質保証を実現します。

## ディレクトリ構造

```
/planning/
├── master_requirement.md    # 大規模プロジェクトの全体要件（オプション）
├── master_plan.md           # 大規模プロジェクトの進捗管理（オプション）
├── current/                 # アクティブな作業ドキュメント
│   ├── requirement.md       # 要件定義（AI作成、人間承認）
│   ├── design.md            # 設計書（AI管理）
│   ├── task.md              # 実装計画（AI管理）
│   └── report.md            # 実装報告（AI管理）
├── templates/               # ドキュメントテンプレート
│   ├── requirement.md
│   ├── design.md
│   ├── task.md
│   └── report.md
└── completed/               # アーカイブ
    └── YYYYMMDD_HHMM_task_name/
        ├── requirement.md
        ├── design.md
        ├── task.md
        └── report.md
```

## 4ドキュメントシステム

### 1. requirement.md（要件定義）
- **作成者**: AI (Claude Code等)
- **承認者**: 人間
- **内容**: 何を作るか、ユーザーストーリー、受け入れ基準
- **更新**: 人間の承認が必要
- **テンプレート**: @planning/templates/requirement.md

### 2. design.md（設計書）
- **管理者**: AI
- **内容**: どのように実装するか、データモデル、API仕様
- **更新**: 実装中の発見に基づいて更新可能
- **テンプレート**: @planning/templates/design.md

### 3. task.md（実装計画）
- **管理者**: AI
- **内容**: TDDベースのタスク分解、進捗チェックボックス、見積もり
- **更新**: 進捗に応じて継続的に更新
- **テンプレート**: @planning/templates/task.md

### 4. report.md（実装報告）
- **管理者**: AI
- **内容**: 作業ログ（タイムスタンプ付き）、技術的決定、問題と解決策
- **更新**: リアルタイムで記録
- **テンプレート**: @planning/templates/report.md

## ワークフロー

### 1. 開始
```bash
# テンプレートから現在の作業ファイルを作成
cp planning/templates/requirement.md planning/current/requirement.md
```

### 2. 要件定義
- ユーザー要件を聞き取り、要件書を作成
- **次に進む前に人間の承認が必須**

### 3. 設計と計画
```bash
cp planning/templates/design.md planning/current/design.md
cp planning/templates/task.md planning/current/task.md
cp planning/templates/report.md planning/current/report.md
```

### 4. 実装
- TDDサイクルを実行（Red→Green→Refactor）
- task.mdのチェックボックスを更新
- report.mdに作業を記録

### 5. 完了とアーカイブ
```bash
# 現在の日時でディレクトリを作成し、4つのファイルをすべて一緒にアーカイブ
mkdir planning/completed/$(date +%Y%m%d_%H%M)_task_name/
cp planning/current/*.md planning/completed/$(date +%Y%m%d_%H%M)_task_name/
```

## アーカイブルール

### 命名形式
- **フォルダ名**: `YYYYMMDD_HHMM_task_name/`
- **例**: `20250615_0900_implement_user_authentication/`

### アーカイブ条件
- タスク完了
- 30日以上非アクティブ
- 計画キャンセル

### 重要事項
- **常に4つのファイルをセットでアーカイブ**
- **テンプレート形式を維持**（変更しない）
- **ファイル名は英語、内容は任意の言語**

## 2層タスク管理

1. **task.md** - 戦略レベル（フェーズ、マイルストーン、チェックボックス）
2. **report.md** - 実行レベル（詳細ログ、技術的決定、テスト結果）

## クイックリファレンス

### 新しいタスクを開始
```bash
cp planning/templates/requirement.md planning/current/requirement.md
```

### すべてのファイルを準備
```bash
cp planning/templates/*.md planning/current/
```

### アーカイブ
```bash
mkdir planning/completed/$(date +%Y%m%d_%H%M)_task_name/
cp planning/current/*.md planning/completed/$(date +%Y%m%d_%H%M)_task_name/
```

### ルートファイルからの参照
- `@planning/current/requirement.md`
- `@planning/current/design.md`
- `@planning/current/task.md`
- `@planning/current/report.md`

## 原則

1. **進行順序**: 要件 → 設計 → 実装計画 → 実装報告
2. **単一責任**: 各ドキュメントは1つの目的のみを果たす
3. **重複なし**: 同じ情報を複数のドキュメントに書かない
4. **トレーサビリティ**: すべてのドキュメントは要件から追跡可能

## ベストプラクティス

### 要件定義
- 明確で測定可能な受け入れ基準を書く
- ユーザーの視点から記述
- 技術的実装詳細は含めない

### 設計
- 要件を満たすための技術的解決策に焦点を当てる
- 主要なトレードオフを文書化
- テスト戦略を含める

### タスク管理
- 各タスクは15-30分で完了可能な単位に分解
- TDDサイクルを明示的に記載
- 依存関係を明確にする

### 報告
- タイムスタンプ付きで記録
- 問題と解決策を詳細に文書化
- 学んだことを記録

## トラブルシューティング

### ドキュメントの不整合
- 常に要件を真実の源として扱う
- 設計と実装の乖離は report.md に記録
- 大きな変更は要件の再承認を検討

### アーカイブの管理
- 定期的に古いアーカイブを確認
- 重要な学びは別途ナレッジベースに転記
- ディスク容量に注意

## まとめ

仕様書駆動開発は、明確な文書化と段階的な進行により、高品質なソフトウェア開発を実現します。4つのドキュメントシステムを厳密に守ることで、プロジェクトの透明性と追跡可能性が確保されます。