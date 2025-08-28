# Specification-Driven Development Template

仕様書駆動開発のためのプロジェクトテンプレートです。要件定義から実装報告まで、4つのドキュメントで開発プロセスを管理します。

## 📋 概要

このテンプレートは、以下の開発プロセスを標準化します：

1. **要件定義** - 何を作るかを明確に定義
2. **設計** - どのように実現するかを設計
3. **実装計画** - TDDベースでタスクを計画
4. **実装報告** - 作業記録と学びの文書化

## 🚀 使い方

### 1. プロジェクトの初期化

このテンプレートリポジトリをクローンして、新しいプロジェクトを開始します：

```bash
# テンプレートをクローン
git clone https://github.com/chemitaro/spec-driven-development-template.git your-project-name

# プロジェクトディレクトリに移動
cd your-project-name

# Gitの履歴をリセット（新しいプロジェクトとして開始）
rm -rf .git
git init
git add .
git commit -m "Initial commit from spec-driven-development template"

# 自分のリポジトリを設定
git remote add origin https://github.com/[your-username]/[your-project-name].git
git push -u origin main
```

または、GitHubの「Use this template」機能を使用：

1. テンプレートリポジトリのGitHubページにアクセス
2. 「Use this template」ボタンをクリック
3. 新しいリポジトリ名を入力して作成
4. 作成されたリポジトリをローカルにクローン

### 2. プロジェクト設定

以下のファイルをプロジェクトに合わせて編集します：

1. **AGENTS.md** - プロジェクト概要セクションを記入
2. **CLAUDE.md** - Claude Code固有の設定を追加（使用する場合）

### 3. 開発開始

#### 新しいタスクの開始

```bash
# 要件テンプレートをコピー
cp planning/templates/requirement.md planning/current/requirement.md
```

要件を記載し、承認を得た後：

```bash
# すべてのドキュメントを準備
cp planning/templates/*.md planning/current/
```

#### 実装フロー

1. **要件定義** (`requirement.md`)
   - ユーザーストーリーを記載
   - 受け入れ基準を定義
   - 人間の承認を得る

2. **設計** (`design.md`)
   - アーキテクチャを設計
   - インターフェースを定義
   - テスト戦略を策定

3. **実装** (`task.md` + `report.md`)
   - TDDサイクルで実装
   - 進捗をチェックボックスで管理
   - 作業記録をリアルタイムで記録

#### タスクの完了とアーカイブ

```bash
# アーカイブディレクトリを作成
mkdir planning/completed/$(date +%Y%m%d_%H%M)_task_name/

# 4つのドキュメントをアーカイブ
cp planning/current/*.md planning/completed/$(date +%Y%m%d_%H%M)_task_name/
```

## 📂 ディレクトリ構造

```
.
├── AGENTS.md                 # AI Coding Agent向けガイド（汎用）
├── CLAUDE.md                 # Claude Code固有設定
├── README.md                 # このファイル
├── planning/
│   ├── templates/           # ドキュメントテンプレート
│   │   ├── requirement.md   # 要件定義テンプレート
│   │   ├── design.md        # 設計書テンプレート
│   │   ├── task.md          # 実装計画テンプレート
│   │   └── report.md        # 実装報告テンプレート
│   ├── current/             # 現在作業中のドキュメント
│   └── completed/           # アーカイブ済みドキュメント
└── docs/                    # 追加ドキュメント（必要に応じて）
    ├── planning-guide.md    # プランニングガイド
    └── development-workflow.md # 開発ワークフロー
```

## 🎯 コア原則

### 95% Understanding Rule
実装前に95%の理解と95%の自信を獲得する

### Test-Driven Development (TDD)
1. **Red** - 失敗するテストを書く
2. **Green** - テストを通す最小限のコードを書く  
3. **Refactor** - コードを改善する

### 4-Document System
すべての開発は4つのドキュメントで管理される

## 🤖 AI Coding Agent サポート

このテンプレートは以下のAI Coding Agentで使用できます：

- **Claude Code** (Anthropic) - `CLAUDE.md`を参照
- **OpenAI Codex CLI** - `AGENTS.md`を参照  
- **Windsurf** (Codeium) - `AGENTS.md`を参照
- **Cursor** - `AGENTS.md`を参照
- **GitHub Copilot Workspace** - `AGENTS.md`を参照
- その他のAIアシスタント - `AGENTS.md`を参照

※ `CLAUDE.md`と`AGENTS.md`は同じ内容です。異なるAI Agentが異なるファイル名を期待する場合があるため、両方のファイルを提供しています。

## 📚 詳細ドキュメント

- [Planning Guide](docs/planning-guide.md) - プランニングの詳細ガイド
- [Development Workflow](docs/development-workflow.md) - 開発ワークフローの説明

## 🔧 カスタマイズ

### プロジェクト固有の設定

1. **AGENTS.md**の`Project Overview`セクションを更新
2. **CLAUDE.md**に環境固有の設定を追加
3. テンプレートを必要に応じて調整（ただし基本構造は維持）

### 言語対応

デフォルトでは日本語ですが、以下の部分を変更可能：
- ドキュメントの内容言語
- コミットメッセージ
- コメント

ただし、ファイル名とディレクトリ名は英語を維持してください。

## 📄 ライセンス

MIT License - 自由に使用・改変可能です。

## 🤝 コントリビューション

改善提案やバグ報告は歓迎します。Issue や Pull Request でお知らせください。

## 🔄 テンプレートの更新

テンプレートが更新された場合、既存のプロジェクトに最新の改善を取り込むことができます：

```bash
# テンプレートリポジトリをupstreamとして追加
git remote add template https://github.com/[your-username]/spec-driven-development-template.git

# テンプレートの更新を取得
git fetch template

# 必要に応じて特定のファイルをマージ
git checkout template/main -- AGENTS.md
git checkout template/main -- planning/templates/
```

---

**Happy Spec-Driven Development! 🚀**