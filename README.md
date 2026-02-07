# Mail Notifier

IMAP メールを定期ポーリングし、ルールに基づいて Discord Webhook へ通知するアプリケーションです。

## 機能

- **IMAP 対応**: Proton Mail Bridge / Gmail など複数アカウント
- **ルールベース通知**: 送信元・件名・受信アカウントの AND 条件
- **マッチタイプ**: 前方一致 / 後方一致 / 部分一致 / 正規表現（Python `re`）
- **ルール優先順位**: ドラッグ&ドロップで並び替え、最初の一致で停止
- **失敗ログ**: Discord 送信失敗を 30 日間保持
- **ワーカー制御**: Web UI からの停止・再開・ポーリング間隔変更
- **Tailscale**: Tailscale Serve 経由で HTTPS 公開

## セットアップ

### 1. 環境変数

```bash
cp .env.example .env
# .env を編集して以下を設定:
#   TS_AUTHKEY   – Tailscale の Auth Key
#   DB_PASSWORD  – PostgreSQL パスワード
#   SECRET_KEY   – Flask のシークレットキー
#   POLL_INTERVAL – ポーリング間隔（秒、デフォルト 60）
```

### 2. 起動

```bash
docker compose up -d
```

初回起動時に自動で DB マイグレーションが実行されます。

### 3. アクセス

Tailscale ネットワーク内から `https://mail-notifier.<tailnet名>` でアクセスできます。

## アーキテクチャ

| サービス | 説明 |
|----------|------|
| `tailscale` | Tailscale Serve でリバースプロキシ |
| `web` | Flask (Gunicorn) – ルール管理 UI |
| `worker` | IMAP ポーリングデーモン |
| `db` | PostgreSQL 18 |

## Web UI

- `/rules` – 通知ルール管理（ドラッグ&ドロップ並び替え）
- `/accounts` – IMAP アカウント管理
- `/maintenance` – ワーカー制御・失敗ログ閲覧
- `/notification_formats` – 通知フォーマット管理・編集

## 通知フォーマットのカスタマイズ

- `/notification_formats` 画面で通知フォーマット（テンプレート）を作成・編集できます。
- 各ルールごとに通知フォーマットを選択可能です。
- テンプレートには以下の変数が利用できます:
    - `{account_name}`: アカウント名
    - `{from_address}`: 送信元メールアドレス
    - `{subject}`: 件名
    - `{rule_name}`: ルール名
- 例:
    ```
    {account_name} に新着メール: {subject} ({from_address})
    ルール: {rule_name}
    ```
- フォーマットを選択しない場合はデフォルトの通知内容になります。

## 失敗ログについて

- IMAP接続や認証失敗、Discord通知失敗などは `/maintenance` 画面で確認できます。
- 失敗ログは FailureLog テーブルに記録され、30日間保持されます。

## アップデート手順

### GHCR（GitHub Container Registry）を使用する場合

docker-compose.yml で `ghcr.io/nananek/mail-notifier/app:latest` を使用している場合:

#### 通常のアップデート（マイグレーションなし）

```bash
cd /path/to/mail-notifier
docker compose pull
docker compose up -d
```

#### マイグレーションが必要な場合

```bash
# 1. 最新イメージを取得
cd /path/to/mail-notifier
docker compose pull

# 2. マイグレーションを実行
docker compose run --rm web flask db upgrade

# 3. すべてのサービスを再起動
docker compose up -d
```

### ローカルビルドを使用する場合

docker-compose.yml で `build: .` を使用している場合:

#### 通常のアップデート（マイグレーションなし）

```bash
cd /path/to/mail-notifier
git pull
docker compose build
docker compose up -d
```

#### マイグレーションが必要な場合

```bash
# 1. コードを最新化
cd /path/to/mail-notifier
git pull

# 2. イメージを再ビルド
docker compose build

# 3. webコンテナでマイグレーションを実行
docker compose run --rm web flask db upgrade

# 4. すべてのサービスを再起動
docker compose up -d
```

**注意事項:**
- マイグレーションは必ず web コンテナが停止している状態、または `docker compose run --rm` で実行してください。
- マイグレーション失敗時は、データベースのバックアップから復元してください。
- 本番環境では事前にバックアップを取得することを推奨します:
  ```bash
  docker compose exec db pg_dump -U postgres mail_notifier > backup.sql
  ```

### マイグレーション履歴の確認

現在適用されているマイグレーションを確認:

```bash
docker compose exec web flask db current
```

マイグレーション履歴を確認:

```bash
docker compose exec web flask db history
```
