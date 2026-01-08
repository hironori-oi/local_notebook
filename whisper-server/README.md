# Whisper Server

YouTube動画の音声を文字起こしするためのWhisperサーバーです。
別PCでGPUを使用して高速な文字起こしを実現します。

## システム要件

### GPU使用時（推奨）
- NVIDIA GPU（VRAM 8GB以上推奨、large-v3モデル使用時）
- NVIDIA Driver 525.60.13以上
- Docker with NVIDIA Container Toolkit
- Docker Compose v2.0以上

### CPU使用時
- メモリ 16GB以上（large-v3モデル使用時）
- Docker & Docker Compose

## セットアップ

### 1. このディレクトリをWhisperサーバー用PCにコピー

```bash
# SCP等でコピー
scp -r whisper-server/ user@whisper-server-pc:/path/to/whisper-server/
```

### 2. 環境変数を設定

```bash
cd whisper-server
cp .env.example .env
# 必要に応じて.envを編集
```

### 3. サーバーを起動

**GPU使用時:**
```bash
docker compose up -d
```

**CPU使用時:**
```bash
# docker-compose.ymlのdeploy.resources部分をコメントアウトしてから
# .envを編集：
#   WHISPER_DEVICE=cpu
#   WHISPER_COMPUTE_TYPE=int8
docker compose up -d
```

### 4. 起動確認

```bash
# ヘルスチェック
curl http://localhost:8001/health

# 期待される応答:
# {"status":"ok","model":"large-v3","device":"cuda","model_loaded":true}
```

## メインアプリケーションとの接続

メインアプリケーション側の`.env`に以下を設定:

```env
# WhisperサーバーのIPアドレスとポートを指定
WHISPER_SERVER_URL=http://192.168.1.100:8001
```

※ `192.168.1.100`はWhisperサーバーのIPアドレスに置き換えてください

## API エンドポイント

### POST /transcribe

音声ファイルを文字起こしします。

**リクエスト:**
- `file`: 音声ファイル（MP3, WAV, M4A, OGG, FLAC, WEBM）
- `language`: 言語コード（デフォルト: `ja`）

**レスポンス:**
```json
{
  "text": "文字起こしされたテキスト",
  "language": "ja",
  "language_probability": 0.98,
  "duration": 120.5
}
```

### GET /health

サーバーの状態を確認します。

**レスポンス:**
```json
{
  "status": "ok",
  "model": "large-v3",
  "device": "cuda",
  "model_loaded": true
}
```

## モデルについて

| モデル | VRAM | 精度 | 速度 |
|--------|------|------|------|
| tiny | ~1GB | 低 | 最速 |
| base | ~1GB | 低-中 | 速い |
| small | ~2GB | 中 | 普通 |
| medium | ~5GB | 中-高 | やや遅い |
| large-v2 | ~10GB | 高 | 遅い |
| large-v3 | ~10GB | 最高 | 遅い |

日本語の文字起こしには `large-v3` を推奨します。

## トラブルシューティング

### GPUが認識されない

```bash
# NVIDIAドライバー確認
nvidia-smi

# NVIDIA Container Toolkit確認
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

### モデルのダウンロードに失敗する

初回起動時にHugging Faceからモデルをダウンロードします。
ネットワーク環境を確認してください。

```bash
# ログを確認
docker compose logs -f whisper-server
```

### メモリ不足

より小さいモデル（`medium`や`small`）を使用してください:

```env
WHISPER_MODEL=medium
```

## ログの確認

```bash
docker compose logs -f whisper-server
```

## 停止

```bash
docker compose down
```

## ファイアウォール設定

外部からアクセスする場合、ポート8001を開放してください:

```bash
# Ubuntu/Debian
sudo ufw allow 8001/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --reload
```
