# NotebookLM Local App

社内ネットワーク上で動作するNotebookLMライクなWebアプリケーションです。
ローカルLLM（Ollama/vLLM）とpgvectorベースのRAGを使用します。

## 機能

### コア機能
- **ノートブック管理**: プロジェクトごとにノートブックを作成・管理
- **ソースアップロード**: PDF/DOCX/TXT/PPTX/Markdownファイルをアップロードしてベクトル化
- **フォルダ管理**: ソースファイルをフォルダで整理
- **AIチャット**: アップロードした資料に基づいてRAGでAIと対話
- **会話セッション管理**: 会話履歴をセッションごとに管理・保存
- **ノート保存**: 重要な回答をノートとして保存・編集

### 議事録・会議管理
- **議事録作成**: テキストベースの議事録を作成・管理
- **議事録フォーマット**: LLMによる自動整形・要約生成
- **ドキュメント紐付け**: 議事録に関連資料をリンク

### 議会・審議会管理（Council）
- **議会管理**: 複数の議会・審議会を管理
- **会議管理**: 会議の日程・議題を管理
- **議事検索**: 議会資料の横断検索
- **議会チャット**: 議会資料に基づくRAGチャット
- **議会メモ**: 議会ごとのメモ管理
- **インフォグラフィック**: 議会資料からの視覚化

### 生成・出力機能
- **インフォグラフィック生成**: ソースから構造化データを自動生成
- **スライド生成**: AIによるプレゼンテーションスライド生成
- **メール生成**: 資料に基づくメール文面の自動生成
- **エクスポート**: ノートブック・チャット履歴のエクスポート

### 入力・処理機能
- **YouTube文字起こし**: Whisperサーバーと連携した動画文字起こし
- **ドキュメントチェッカー**: PowerPointファイルの品質チェック
- **コンテンツ処理**: バックグラウンドでの自動フォーマット・要約

### 管理・設定機能
- **グローバル検索**: ノートブック・資料・議事録を横断検索
- **LLM設定**: モデル・パラメータのカスタマイズ
- **管理者機能**: ユーザー管理・システム統計
- **監査ログ**: ユーザーアクションの追跡・記録
- **JWT認証**: セキュアなユーザー認証とレート制限

## 技術スタック

### Backend
- FastAPI 0.115 + SQLAlchemy 2.0 + Alembic
- PostgreSQL 16 + pgvector（ベクトル検索）
- Celery 5.3 + Redis 7（非同期タスクキュー）
- JWT認証（python-jose + passlib + bcrypt）
- pytest + pytest-cov（テスト）

### Frontend
- Next.js 15 + React 19
- TypeScript + Tailwind CSS
- Vitest + React Testing Library（テスト）

### LLM/Embedding
- Ollama または vLLM（OpenAI互換API）
- 推奨モデル: llama3.1:8b または gpt-oss-120b（LLM）
- 推奨モデル: nomic-embed-text (768次元) または PLaMo-Embedding-1B (2048次元)

### 外部サービス（オプション）
- Whisper Server: 音声文字起こし用（別マシンで稼働）

## プロジェクト構造

```
.
├── docker-compose.yml      # Docker Compose設定
├── .env.example            # 環境変数テンプレート
├── .github/workflows/      # CI/CD設定
├── docs/                   # ドキュメント
├── backend/                # FastAPI バックエンド
│   ├── app/
│   │   ├── api/v1/         # APIエンドポイント
│   │   ├── celery_app/     # Celeryタスク定義
│   │   │   └── tasks/      # 各種バックグラウンドタスク
│   │   ├── core/           # 設定・依存関係・例外・レート制限
│   │   ├── models/         # SQLAlchemyモデル
│   │   ├── schemas/        # Pydanticスキーマ
│   │   └── services/       # ビジネスロジック
│   ├── alembic/            # DBマイグレーション
│   ├── tests/              # pytestテスト
│   └── Dockerfile
├── frontend/               # Next.js フロントエンド
│   ├── src/
│   │   ├── app/            # ページコンポーネント
│   │   ├── components/     # UIコンポーネント
│   │   ├── hooks/          # カスタムフック
│   │   └── lib/            # APIクライアント
│   ├── vitest.config.ts    # Vitestテスト設定
│   └── Dockerfile
└── whisper-server/         # Whisperサーバー（オプション）
```

## クイックスタート（Docker Compose）

### 前提条件

1. **Docker** と **Docker Compose** がインストールされていること
2. **Ollama** がホストマシンで起動していること（または別のLLMサーバー）

### 1. 環境変数の設定

```bash
# .envファイルを作成
cp .env.example .env

# .envを編集してJWT_SECRET_KEYを設定（必須）
# 以下のコマンドでシークレットキーを生成できます
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Ollamaの準備（ホストマシン）

```bash
# Ollamaインストール後、モデルを取得
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# Ollamaサーバー起動（デフォルトで11434ポート）
ollama serve
```

### 3. Docker Composeで起動

```bash
# すべてのサービスをビルドして起動
docker-compose up -d --build

# ログを確認
docker-compose logs -f

# 起動状態を確認
docker-compose ps
```

### 4. アプリケーションにアクセス

- **フロントエンド**: http://localhost:3000
- **バックエンドAPI**: http://localhost:8000
- **API ドキュメント（開発時のみ）**: http://localhost:8000/api/docs
- **Flower（タスクモニタリング）**: http://localhost:5555 (admin/admin)

### 5. 初回セットアップ

1. http://localhost:3000 にアクセス
2. 「新規登録」からユーザーを作成
3. ログイン後、ノートブックを作成
4. ドキュメントをアップロードしてチャットを開始

## Docker Compose コマンド

```bash
# 起動
docker-compose up -d

# 停止
docker-compose down

# ログ確認
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f celery-worker

# 再ビルド
docker-compose up -d --build

# データを含めて完全削除
docker-compose down -v

# 個別サービスの再起動
docker-compose restart backend
docker-compose restart celery-worker
```

## Celery バックグラウンドタスク

### タスクキュー構成

| キュー | タイムアウト | タスク |
|--------|-------------|--------|
| transcription | 1時間 | YouTube文字起こし |
| content | 10分 | ソース処理、議事録処理、議会アジェンダ |
| llm | 10分 | 文書チェック、スライド生成 |
| chat | 2分 | チャット応答 |

### 機能

- **タスク永続化**: Redis によるタスクキューの永続化
- **自動リカバリー**: ワーカー再起動時に中断されたタスクを自動復旧
- **自動リトライ**: 接続エラー時に exponential backoff で最大3回リトライ
- **モニタリング**: Flower ダッシュボードでタスク状況を監視

### Flower ダッシュボード

http://localhost:5555 でタスクの監視が可能です。
- タスク成功/失敗率
- キュー別待機数
- ワーカー稼働状況

デフォルト認証: `FLOWER_USER` / `FLOWER_PASSWORD`（.env で設定）

## ローカル開発（Docker不使用）

### 前提条件

1. **PostgreSQL 16+** with pgvector extension
2. **Python 3.11+** with Poetry
3. **Node.js 20+**
4. **Ollama** server

### 1. PostgreSQL + pgvector のセットアップ

```sql
-- PostgreSQLでpgvector拡張を有効化
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. Backend のセットアップ

```bash
cd backend

# 依存関係インストール
poetry install

# 環境変数設定
cp ../.env.example .env
# .envを編集

# マイグレーション実行
poetry run alembic upgrade head

# サーバー起動
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend のセットアップ

```bash
cd frontend

# 依存関係インストール
npm install

# 開発サーバー起動
npm run dev
```

### 4. テストの実行

```bash
# バックエンドテスト
cd backend
poetry run pytest tests/ -v --cov=app

# フロントエンドテスト
cd frontend
npm run test
npm run test:coverage
```

## 環境変数

### 必須設定

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| JWT_SECRET_KEY | JWT署名用シークレットキー（32文字以上） | - |
| DATABASE_URL | PostgreSQL接続URL | postgresql://notebooklm:notebooklm_password@postgres:5432/notebooklm |

### LLM/Embedding設定

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| LLM_PROVIDER | LLMプロバイダー（ollama/vllm） | ollama |
| LLM_API_BASE | LLM APIベースURL | http://localhost:11434/v1 |
| LLM_MODEL | 使用するLLMモデル | llama3.1:8b |
| LLM_TIMEOUT | LLMリクエストタイムアウト（秒） | 120 |
| GENERATION_LLM_MODEL | 生成用LLMモデル（空の場合LLM_MODELを使用） | - |
| EMBEDDING_API_BASE | Embedding APIベースURL | http://localhost:11434/v1 |
| EMBEDDING_MODEL | 使用するEmbeddingモデル | nomic-embed-text |
| EMBEDDING_DIM | Embeddingベクトル次元数 | 768 |

### 認証・セキュリティ設定

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| JWT_ALGORITHM | JWT暗号化アルゴリズム | HS256 |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | トークン有効期限（分） | 1440 (24時間) |
| RATE_LIMIT_AUTH_REQUESTS | 認証エンドポイントのレート制限 | 5回/15分 |
| RATE_LIMIT_API_REQUESTS | 一般APIのレート制限 | 100回/分 |
| TRUSTED_PROXIES | 信頼するプロキシIP（カンマ区切り） | - |
| TRUST_PROXY_HEADERS | X-Forwarded-Forヘッダーを信頼 | false |

### アプリケーション設定

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| ENV | 環境モード（development/production） | development |
| CORS_ORIGINS | 許可するオリジン（カンマ区切り） | http://localhost:3000 |
| MAX_UPLOAD_SIZE_MB | 最大アップロードサイズ（MB） | 50 |
| MAX_CHAT_HISTORY_MESSAGES | チャット履歴の最大メッセージ数 | 20 |
| MAX_CHAT_HISTORY_CHARS | チャット履歴の最大文字数 | 8000 |

### Redis/Celery設定

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| REDIS_URL | Redis接続URL | redis://localhost:6379/0 |
| CELERY_BROKER_URL | Celeryブローカー（未設定時REDIS_URL使用） | - |
| CELERY_RESULT_BACKEND | Celery結果バックエンド（未設定時REDIS_URL使用） | - |
| FLOWER_USER | Flower認証ユーザー名 | admin |
| FLOWER_PASSWORD | Flower認証パスワード | admin |

### 外部サービス設定

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| WHISPER_SERVER_URL | Whisperサーバーの URL | - |
| MAX_VIDEO_DURATION_MINUTES | 最大動画長（分） | 60 |

## API エンドポイント

### 認証
- `POST /api/v1/auth/register` - ユーザー登録
- `POST /api/v1/auth/login` - ログイン
- `POST /api/v1/auth/logout` - ログアウト
- `GET /api/v1/auth/me` - 現在のユーザー情報
- `PUT /api/v1/auth/password` - パスワード変更

### ヘルスチェック
- `GET /api/v1/health` - 基本ヘルスチェック
- `GET /api/v1/health/llm` - LLM接続チェック
- `GET /api/v1/health/embedding` - Embedding接続チェック
- `GET /api/v1/health/full` - 全体ヘルスチェック

### ノートブック
- `GET /api/v1/notebooks` - ノートブック一覧
- `POST /api/v1/notebooks` - ノートブック作成
- `GET /api/v1/notebooks/{id}` - ノートブック詳細
- `PUT /api/v1/notebooks/{id}` - ノートブック更新
- `DELETE /api/v1/notebooks/{id}` - ノートブック削除

### ソース・フォルダ
- `POST /api/v1/sources/upload` - ファイルアップロード
- `GET /api/v1/sources/notebook/{notebook_id}` - ソース一覧
- `PUT /api/v1/sources/{source_id}` - ソース更新
- `DELETE /api/v1/sources/{source_id}` - ソース削除
- `GET /api/v1/folders/notebook/{notebook_id}` - フォルダ一覧
- `POST /api/v1/folders/notebook/{notebook_id}` - フォルダ作成
- `PUT /api/v1/folders/{folder_id}` - フォルダ更新
- `DELETE /api/v1/folders/{folder_id}` - フォルダ削除

### チャット
- `POST /api/v1/chat` - チャット送信（RAG対応）
- `GET /api/v1/chat/sessions/{notebook_id}` - セッション一覧
- `POST /api/v1/chat/sessions/{notebook_id}` - セッション作成
- `GET /api/v1/chat/sessions/{session_id}/history` - セッション履歴
- `PUT /api/v1/chat/sessions/{session_id}` - セッション更新
- `DELETE /api/v1/chat/sessions/{session_id}` - セッション削除

### ノート
- `GET /api/v1/notes/notebook/{notebook_id}` - ノート一覧
- `POST /api/v1/notes/{notebook_id}` - ノート作成
- `GET /api/v1/notes/{note_id}` - ノート詳細
- `PATCH /api/v1/notes/{note_id}` - ノート更新
- `DELETE /api/v1/notes/{note_id}` - ノート削除

### 議事録
- `GET /api/v1/minutes/notebook/{notebook_id}` - 議事録一覧
- `POST /api/v1/minutes/notebook/{notebook_id}` - 議事録作成
- `GET /api/v1/minutes/{minute_id}` - 議事録詳細
- `PATCH /api/v1/minutes/{minute_id}` - 議事録更新
- `DELETE /api/v1/minutes/{minute_id}` - 議事録削除
- `GET /api/v1/minutes/{minute_id}/detail` - 議事録詳細（要約含む）

### 議会管理（Council）
- `GET /api/v1/councils` - 議会一覧
- `POST /api/v1/councils` - 議会作成
- `GET /api/v1/councils/{council_id}` - 議会詳細
- `PUT /api/v1/councils/{council_id}` - 議会更新
- `DELETE /api/v1/councils/{council_id}` - 議会削除
- `GET /api/v1/councils/{council_id}/meetings` - 会議一覧
- `POST /api/v1/councils/{council_id}/meetings` - 会議作成
- `GET /api/v1/council-chat/sessions/{council_id}` - 議会チャットセッション
- `POST /api/v1/council-chat` - 議会チャット送信
- `GET /api/v1/council-search` - 議会検索

### 生成機能
- `POST /api/v1/infographics/{notebook_id}` - インフォグラフィック生成
- `GET /api/v1/infographics/{notebook_id}` - インフォグラフィック一覧
- `DELETE /api/v1/infographics/{infographic_id}` - インフォグラフィック削除
- `POST /api/v1/slide-generator/projects` - スライドプロジェクト作成
- `GET /api/v1/slide-generator/projects` - プロジェクト一覧
- `POST /api/v1/slide-generator/projects/{project_id}/generate` - スライド生成
- `POST /api/v1/email/generate` - メール生成

### その他
- `GET /api/v1/search/global` - グローバル検索
- `GET /api/v1/search/recent` - 最近のアイテム
- `POST /api/v1/transcription` - 動画文字起こし
- `POST /api/v1/document-checker/upload` - ドキュメントチェック
- `GET /api/v1/export/{notebook_id}` - エクスポート
- `GET /api/v1/processing/status` - 処理状況確認
- `GET /api/v1/llm-settings` - LLM設定取得
- `PUT /api/v1/llm-settings` - LLM設定更新

### 管理者
- `GET /api/v1/admin/users` - ユーザー一覧
- `GET /api/v1/admin/stats` - システム統計
- `GET /api/v1/admin/audit-logs` - 監査ログ

## vLLM への移行

OllamaからvLLMへ移行する場合は、`.env`を以下のように変更します：

```env
LLM_PROVIDER=vllm
LLM_API_BASE=http://localhost:8080/v1
LLM_MODEL=your-vllm-model-name

EMBEDDING_API_BASE=http://localhost:8081/v1
EMBEDDING_MODEL=your-embedding-model
```

vLLMサーバーはOpenAI互換APIを提供するため、コード変更は不要です。

## Whisperサーバーのセットアップ

YouTube動画の文字起こし機能を使用する場合、GPUを搭載した別マシンでWhisperサーバーを起動する必要があります。

```bash
cd whisper-server
# READMEを参照してセットアップ
```

`.env`でWhisperサーバーのURLを設定:
```env
WHISPER_SERVER_URL=http://192.168.1.100:8001
```

## トラブルシューティング

### Docker関連

**コンテナが起動しない場合**
```bash
# ログを確認
docker-compose logs backend
docker-compose logs frontend

# コンテナの状態確認
docker-compose ps
```

**データベース接続エラー**
```bash
# PostgreSQLコンテナが健全か確認
docker-compose logs postgres

# マイグレーションを再実行
docker-compose run --rm migrations alembic upgrade head
```

**ホストのOllamaに接続できない場合**
- Docker Desktop for Windows/Macでは `host.docker.internal` でホストにアクセス可能
- Linuxの場合は `--add-host=host.docker.internal:host-gateway` を追加

### Celery/Redis関連

**タスクが実行されない場合**
```bash
# Celeryワーカーの状態確認
docker-compose logs celery-worker

# Redisの状態確認
docker-compose exec redis redis-cli ping

# タスクキューの確認（Flower経由）
# http://localhost:5555 にアクセス
```

**タスクが "processing" のまま止まっている場合**
- コンテナ再起動により中断された可能性があります
- ワーカー再起動時に自動リカバリーされます
```bash
docker-compose restart celery-worker
```

**Flower にアクセスできない場合**
```bash
# Flowerコンテナの確認
docker-compose logs flower

# 認証情報の確認（.env）
# FLOWER_USER, FLOWER_PASSWORD
```

### LLM関連

**LLMの応答が遅い・タイムアウトする場合**
- `LLM_TIMEOUT` を増やす（デフォルト120秒）
- より軽量なモデルを使用する

**Embeddingエラーが発生する場合**
- `EMBEDDING_DIM` がモデルの出力次元と一致しているか確認
  - nomic-embed-text: 768
  - PLaMo-Embedding-1B: 2048

### エラーコード

APIエラーレスポンスには `error_code` フィールドが含まれます：

| エラーコード | 説明 |
|-------------|------|
| UNAUTHORIZED | 認証が必要 |
| FORBIDDEN | アクセス拒否 |
| NOT_FOUND | リソースが見つからない |
| BAD_REQUEST | 不正なリクエスト |
| VALIDATION_ERROR | バリデーションエラー |
| LLM_CONNECTION_ERROR | LLMサーバー接続エラー |
| EMBEDDING_ERROR | Embedding生成エラー |
| RATE_LIMIT_EXCEEDED | レート制限超過 |

## 開発時の注意

1. **Embedding次元数**: モデルによって次元数が異なります。変更時は既存データの再生成が必要です。

2. **JWT Secret**: 本番環境では必ず強力なシークレットキーを使用してください。

3. **レート制限**: 認証エンドポイントは5回/15分、一般APIは100回/分に制限されています。

4. **テスト**: プルリクエスト前にテストを実行してください。
   ```bash
   # バックエンド
   cd backend && poetry run pytest

   # フロントエンド
   cd frontend && npm run test
   ```

5. **マイグレーション**: モデル変更後は必ずマイグレーションを作成・適用してください。
   ```bash
   cd backend
   poetry run alembic revision --autogenerate -m "description"
   poetry run alembic upgrade head
   ```

## ライセンス

社内利用専用
