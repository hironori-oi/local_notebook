# Janus-Pro-7B Image Generation Server

DeepSeek Janus-Pro-7B を使用した Text-to-Image 生成サーバー。

## 概要

- **モデル**: [deepseek-ai/Janus-Pro-7B](https://huggingface.co/deepseek-ai/Janus-Pro-7B)
- **機能**: テキストプロンプトから画像を生成
- **出力サイズ**: 384x384 ピクセル
- **必要GPU**: 24GB VRAM（RTX 3090/4090, A5000, A6000等）

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/health` | ヘルスチェック |
| POST | `/generate` | 画像生成（1枚） |
| POST | `/generate/batch` | バッチ画像生成 |

### POST /generate

```json
{
  "prompt": "A beautiful sunset over mountains, digital art style",
  "width": 384,
  "height": 384,
  "cfg_weight": 5.0,
  "temperature": 1.0,
  "seed": null
}
```

**レスポンス:**
```json
{
  "images": ["base64_encoded_png..."],
  "width": 384,
  "height": 384
}
```

---

## dt004.improver.work へのデプロイ手順

### 前提条件

- NVIDIA GPU（24GB VRAM以上）
- Docker + NVIDIA Container Toolkit
- CUDA 12.1+

### 1. NVIDIA Container Toolkit のインストール（未インストールの場合）

```bash
# Distribution を設定
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)

# GPG キーを追加
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -

# リポジトリを追加
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# インストール
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Docker を再起動
sudo systemctl restart docker

# 確認
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

### 2. プロジェクトの配置

```bash
# dt004 にログイン
ssh dt004.improver.work

# ディレクトリ作成
mkdir -p ~/janus-server
cd ~/janus-server

# ファイルをコピー（ローカルから）
# またはリポジトリからクローン
```

**必要なファイル:**
```
janus-server/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── generator.py
│   └── main.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

### 3. 環境設定

```bash
# .env ファイル作成
cp .env.example .env

# 必要に応じて編集
nano .env
```

### 4. Docker イメージのビルド

```bash
cd ~/janus-server

# イメージをビルド（初回は10-15分程度）
docker-compose build

# または直接ビルド
docker build -t janus-server .
```

### 5. サーバー起動

```bash
# Docker Compose で起動
docker-compose up -d

# ログ確認（モデルロードに2-3分かかります）
docker-compose logs -f
```

**起動ログの例:**
```
janus-server  | Starting Janus-Pro-7B Image Generation Server...
janus-server  | Loading Janus model: deepseek-ai/Janus-Pro-7B
janus-server  | Downloading model files... (初回のみ)
janus-server  | Processor loaded successfully
janus-server  | Model loaded successfully on cuda
janus-server  | Server ready!
janus-server  | Uvicorn running on http://0.0.0.0:9000
```

### 6. 動作確認

```bash
# ヘルスチェック
curl http://localhost:9000/health

# 画像生成テスト
curl -X POST http://localhost:9000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A cute cat sitting on a chair, digital art"}' \
  | jq -r '.images[0]' | base64 -d > test.png

# 生成された画像を確認
ls -la test.png
```

### 7. 外部からのアクセス確認

```bash
# ファイアウォールでポート9000を開放（必要な場合）
sudo ufw allow 9000/tcp

# 外部から確認
curl http://dt004.improver.work:9000/health
```

---

## Docker を使わない場合（直接実行）

### 1. Python 環境のセットアップ

```bash
# Python 3.11 推奨
python3.11 -m venv venv
source venv/bin/activate

# PyTorch インストール（CUDA 12.1）
pip install torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu121

# 依存関係インストール
pip install -r requirements.txt
```

### 2. サーバー起動

```bash
source venv/bin/activate
cd janus-server

# 起動
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000

# または
python -m app.main
```

### 3. systemd サービスとして登録（オプション）

```bash
sudo nano /etc/systemd/system/janus-server.service
```

```ini
[Unit]
Description=Janus-Pro-7B Image Generation Server
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/janus-server
Environment="PATH=/home/your_username/janus-server/venv/bin"
ExecStart=/home/your_username/janus-server/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable janus-server
sudo systemctl start janus-server
sudo systemctl status janus-server
```

---

## トラブルシューティング

### GPU メモリ不足

```
torch.cuda.OutOfMemoryError: CUDA out of memory
```

**対処法:**
- 他のGPUプロセスを終了
- `nvidia-smi` でメモリ使用状況を確認
- バッチサイズを1に制限（デフォルト）

### モデルダウンロードが遅い

```bash
# Hugging Face ミラーを使用
export HF_ENDPOINT=https://hf-mirror.com
```

### CUDA バージョンの不一致

```bash
# PyTorch と CUDA バージョンを確認
python -c "import torch; print(torch.version.cuda)"
nvidia-smi
```

---

## パフォーマンス

| 項目 | 値 |
|------|-----|
| モデルロード時間 | 約2-3分（初回ダウンロード除く） |
| 画像生成時間 | 約30-60秒/枚（384x384） |
| GPU メモリ使用量 | 約14-16GB |
| 推奨GPU | RTX 3090/4090, A5000, A6000 |

---

## ライセンス

- Janus-Pro-7B: [DeepSeek License](https://github.com/deepseek-ai/Janus/blob/main/LICENSE)
- このサーバー実装: プロジェクトライセンスに従う
