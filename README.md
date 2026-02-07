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
