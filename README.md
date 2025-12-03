# Internal AI Notebook (NotebookLM-like, Local LLM)

社内ネットワーク上で動作するNotebookLMライクなWebアプリケーションです。
ローカルLLM（Ollama/vLLM）とpgvectorベースのRAGを使用します。

## 機能

- **ノートブック管理**: プロジェクトごとにノートブックを作成・管理
- **ソースアップロード**: PDF/テキストファイルをアップロードしてRAG用にチャンク化
- **AIチャット**: アップロードした資料に基づいてAIと対話
- **ノート保存**: 重要な回答をノートとして保存
- **監査ログ**: ユーザーアクションの追跡・記録
- **JWT認証**: セキュアなユーザー認証

## 技術スタック

### Backend
- FastAPI + SQLAlchemy + Alembic
- PostgreSQL + pgvector（ベクトル検索）
- JWT認証（python-jose + passlib）

### Frontend
- Next.js 15 + React 19
- TypeScript + Tailwind CSS

### LLM/Embedding
- Ollama または vLLM（OpenAI互換API）
- 推奨モデル: gpt-oss-120b（LLM）、PLaMo-Embedding-1B（埋め込み）

## プロジェクト構造

```
.
├── docs/requirements.md    # 要件定義書
├── backend/                # FastAPI バックエンド
│   ├── app/
│   │   ├── api/v1/         # APIエンドポイント
│   │   ├── core/           # 設定・依存関係
│   │   ├── models/         # SQLAlchemyモデル
│   │   ├── schemas/        # Pydanticスキーマ
│   │   └── services/       # ビジネスロジック
│   └── alembic/            # DBマイグレーション
└── frontend/               # Next.js フロントエンド
    └── src/
        ├── app/            # ページコンポーネント
        └── lib/            # APIクライアント
```

## セットアップ

### 前提条件

1. **PostgreSQL** with pgvector extension
2. **Python 3.11+** with Poetry
3. **Node.js 18+**
4. **Ollama** or **vLLM** server

### 1. Ollama のセットアップ

```bash
# Ollamaインストール後、モデルを取得
ollama pull gpt-oss-120b
ollama pull plamo-embedding-1b

# Ollamaサーバー起動（デフォルトで11434ポート）
ollama serve
```

### 2. PostgreSQL + pgvector のセットアップ

```sql
-- PostgreSQLでpgvector拡張を有効化
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Backend のセットアップ

```bash
cd backend

# 依存関係インストール
poetry install

# 環境変数設定（.envファイルをコピーして編集）
cp .env.example .env

# .envを編集
# DATABASE_URL=postgresql://user:password@localhost:5432/notebooklm
# LLM_API_BASE=http://localhost:11434/v1
# LLM_MODEL=gpt-oss-120b
# EMBEDDING_API_BASE=http://localhost:11434/v1
# EMBEDDING_MODEL=plamo-embedding-1b
# JWT_SECRET_KEY=your-secure-secret-key

# マイグレーション実行
poetry run alembic upgrade head

# サーバー起動
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Frontend のセットアップ

```bash
cd frontend

# 依存関係インストール
npm install

# 開発サーバー起動
npm run dev
```

フロントエンドは http://localhost:3000 でアクセス可能です。

## 環境変数

### Backend (.env)

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| DATABASE_URL | PostgreSQL接続URL | - |
| LLM_PROVIDER | LLMプロバイダー（ollama/vllm） | ollama |
| LLM_API_BASE | LLM APIベースURL | http://localhost:11434/v1 |
| LLM_MODEL | 使用するLLMモデル | gpt-oss-120b |
| LLM_TIMEOUT | LLMリクエストタイムアウト（秒） | 120 |
| EMBEDDING_API_BASE | Embedding APIベースURL | http://localhost:11434/v1 |
| EMBEDDING_MODEL | 使用するEmbeddingモデル | plamo-embedding-1b |
| EMBEDDING_DIM | Embeddingベクトル次元数 | 2048 |
| JWT_SECRET_KEY | JWT署名用シークレットキー | - |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | トークン有効期限（分） | 1440 |

## API エンドポイント

### 認証
- `POST /api/v1/auth/register` - ユーザー登録
- `POST /api/v1/auth/login` - ログイン
- `POST /api/v1/auth/logout` - ログアウト

### ヘルスチェック
- `GET /api/v1/health` - 基本ヘルスチェック
- `GET /api/v1/health/llm` - LLM接続チェック
- `GET /api/v1/health/embedding` - Embedding接続チェック
- `GET /api/v1/health/full` - 全体ヘルスチェック

### ノートブック
- `GET /api/v1/notebooks` - ノートブック一覧
- `POST /api/v1/notebooks` - ノートブック作成
- `GET /api/v1/notebooks/{id}` - ノートブック詳細
- `DELETE /api/v1/notebooks/{id}` - ノートブック削除

### ソース
- `POST /api/v1/sources/upload/{notebook_id}` - ファイルアップロード
- `GET /api/v1/sources/notebook/{notebook_id}` - ソース一覧
- `DELETE /api/v1/sources/{source_id}` - ソース削除

### チャット
- `POST /api/v1/chat/{notebook_id}` - チャット送信
- `GET /api/v1/chat/history/{notebook_id}` - チャット履歴取得
- `DELETE /api/v1/chat/history/{notebook_id}` - チャット履歴削除

### ノート
- `GET /api/v1/notes/notebook/{notebook_id}` - ノート一覧
- `POST /api/v1/notes/{notebook_id}` - ノート作成
- `GET /api/v1/notes/{note_id}` - ノート詳細
- `DELETE /api/v1/notes/{note_id}` - ノート削除

## vLLM への移行

Ollamaからvllmへ移行する場合は、`.env`を以下のように変更します：

```env
LLM_PROVIDER=vllm
LLM_API_BASE=http://localhost:8080/v1
LLM_MODEL=your-vllm-model-name

EMBEDDING_API_BASE=http://localhost:8081/v1
EMBEDDING_MODEL=your-embedding-model
```

vLLMサーバーはOpenAI互換APIを提供するため、コード変更は不要です。

## 開発時の注意

1. **Embedding次元数**: PLaMo-Embedding-1Bは2048次元を使用します。他のモデルを使用する場合は`EMBEDDING_DIM`を適切に設定してください。

2. **マイグレーション**: Embedding次元を変更する場合は、既存のチャンクデータを再生成する必要があります。

3. **JWT Secret**: 本番環境では強力なシークレットキーを使用してください。

## ライセンス

社内利用専用
