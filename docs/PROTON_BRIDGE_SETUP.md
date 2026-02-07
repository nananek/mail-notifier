# Proton Mail Bridge セットアップガイド

このガイドでは、Proton Mail BridgeをDocker環境でHeadlessモードで動作させるための手順を説明します。

## 前提条件

- Docker Compose がインストールされていること
- Proton Mail のアカウントを持っていること

## 1. コンテナのビルドと起動

```bash
cd /mnt/docker/mail-notifier
sudo docker compose up -d --build mail-bridge
```

## 2. GPGとpassの初期化

コンテナにアタッチします：

```bash
sudo docker attach mail-bridge
```

### 2.1 GPG鍵の生成

Bridge CLIプロンプトが表示されたら、一旦 Ctrl+C で抜けて、以下のコマンドを実行します：

```bash
gpg --batch --passphrase '' --quick-gen-key 'Proton Bridge' default default never
```

### 2.2 GPG鍵IDの確認

```bash
gpg --list-secret-keys --keyid-format LONG
```

出力例：
```
sec   rsa3072/XXXXXXXXXXXXXXXX 2024-01-01 [SC]
      YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
uid           [ultimate] Proton Bridge
```

`XXXXXXXXXXXXXXXX` の部分が鍵IDです。

### 2.3 passの初期化

上記で確認した鍵IDを使用してpassを初期化します：

```bash
pass init XXXXXXXXXXXXXXXX
```

## 3. Proton Mail Bridgeへのログイン

コンテナを再起動してBridge CLIに戻ります：

```bash
# 一旦デタッチ: Ctrl+P → Ctrl+Q
exit

# コンテナ再起動
sudo docker compose restart mail-bridge
sudo docker attach mail-bridge
```

Bridge CLIプロンプト (`>>>`) が表示されたら、ログインコマンドを実行します：

```
>>> login
```

指示に従ってProton Mailのメールアドレスとパスワードを入力します。
2FAを有効にしている場合は、6桁のコードも入力してください。

## 4. 接続情報の確認

ログイン成功後、接続情報を確認します：

```
>>> info
```

出力例：
```
Configuration for your_email@protonmail.com

IMAP Settings
-------------
Address:   127.0.0.1
IMAP port: 1143
Username:  your_email@protonmail.com
Password:  <GENERATED_PASSWORD>
Security:  STARTTLS

SMTP Settings
-------------
Address:   127.0.0.1
SMTP port: 1025
Username:  your_email@protonmail.com
Password:  <GENERATED_PASSWORD>
Security:  STARTTLS
```

**重要**: `<GENERATED_PASSWORD>` は自動生成されたBridge用アプリパスワードです。
このパスワードをメモしてください。

## 5. アプリケーションからの接続設定

### 5.1 環境変数での管理（推奨）

`.env` ファイルに以下を追加：

```env
# Proton Mail Bridge
PROTON_IMAP_HOST=mail-bridge
PROTON_IMAP_PORT=1143
PROTON_IMAP_USER=your_email@protonmail.com
PROTON_IMAP_PASSWORD=<GENERATED_PASSWORD>
```

### 5.2 アカウント管理画面での設定

Web UIの「アカウント管理」画面で以下のように設定します：

- **名前**: Proton Mail
- **IMAPホスト**: `mail-bridge`
- **IMAPポート**: `1143`
- **ユーザー名**: `your_email@protonmail.com`
- **パスワード**: `<GENERATED_PASSWORD>`
- **SSL使用**: ✅ チェック（STARTTLSを使用）
- **メールボックス名**: `INBOX`（または任意のフォルダ）

## 6. デタッチ

Bridge CLIから抜けるには：

```
Ctrl+P → Ctrl+Q
```

これでコンテナをバックグラウンドで実行したまま、シェルに戻ります。

## トラブルシューティング

### コンテナが起動しない場合

ログを確認：
```bash
sudo docker compose logs mail-bridge
```

### GPG/pass関連のエラー

ボリュームをクリアして再セットアップ：
```bash
sudo rm -rf volumes/protonmail-bridge volumes/gnupg
sudo docker compose up -d --build mail-bridge
# 上記の手順2から再実行
```

### パスワードを忘れた場合

Bridge CLIで `info` コマンドを再実行してパスワードを確認できます：
```bash
sudo docker attach mail-bridge
>>> info
```

## セキュリティに関する注意事項

- `<GENERATED_PASSWORD>` は外部に漏らさないこと
- `.env` ファイルは必ず `.gitignore` に含めること
- 本番環境では Docker Secrets や他のシークレット管理ツールの使用を検討すること
