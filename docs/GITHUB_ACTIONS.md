# GitHub Actions ワークフロー

このプロジェクトには以下のGitHub Actionsワークフローが含まれています。

## 1. Docker Build & Test (`docker-build.yml`)

### トリガー
- `master`, `main`, `develop` ブランチへのプッシュ
- `master`, `main` ブランチへのプルリクエスト

### ジョブ

#### `build-app`
- メインアプリケーション（Web/Worker）のDockerイメージをビルド
- Buildxキャッシュを使用してビルド時間を短縮
- イメージはプッシュせずビルドのみ（CI検証）

#### `build-proton-bridge`
- Proton Mail BridgeのDockerイメージをビルド
- 独立したキャッシュを使用

#### `test`
- PostgreSQL 18をサービスコンテナとして起動
- Python依存関係をインストール
- Alembic migrationsを実行してデータベーススキーマを検証

## 2. Docker Publish (`docker-publish.yml`)

### トリガー
- リリースが公開されたとき
- 手動実行（workflow_dispatch）

### ジョブ

#### `publish-app`
- アプリケーションイメージをGitHub Container Registry (ghcr.io) に公開
- マルチプラットフォーム対応（linux/amd64, linux/arm64）
- セマンティックバージョニング対応

#### `publish-bridge`
- Proton Bridge イメージをGitHub Container Registry に公開
- amd64のみ（.debパッケージの制約）

### イメージタグ戦略

- `latest`: デフォルトブランチへのプッシュ時
- `v1.2.3`: リリースタグから自動抽出
- `v1.2`: メジャー.マイナーバージョン
- ブランチ名/PR番号

## セットアップ

### GitHub Container Registryへのアクセス

ワークフローは自動的に `GITHUB_TOKEN` を使用してGitHub Container Registryにログインします。
追加の設定は不要です。

### ローカルでイメージを取得

```bash
# ログイン
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# イメージを取得
docker pull ghcr.io/YOUR_USERNAME/mail-notifier/app:latest
docker pull ghcr.io/YOUR_USERNAME/mail-notifier/proton-bridge:latest
```

### docker-compose.ymlでの使用

ビルド済みイメージを使用する場合：

```yaml
services:
  web:
    image: ghcr.io/YOUR_USERNAME/mail-notifier/app:latest
    # build セクションを削除

  worker:
    image: ghcr.io/YOUR_USERNAME/mail-notifier/app:latest
    # build セクションを削除

  mail-bridge:
    image: ghcr.io/YOUR_USERNAME/mail-notifier/proton-bridge:latest
    # build セクションを削除
```

## キャッシュ管理

### ビルドキャッシュ

- `docker-build.yml`: ローカルキャッシュを使用（CI環境で高速化）
- `docker-publish.yml`: GitHub Actions キャッシュ（gha）を使用

### キャッシュのクリア

キャッシュが破損した場合、リポジトリの Settings > Actions > Caches から削除できます。

## トラブルシューティング

### ビルドが失敗する場合

1. ローカルでビルドを試す：
   ```bash
   docker build -f Dockerfile -t test:local .
   docker build -f Dockerfile.protonmail-bridge -t bridge:local .
   ```

2. 依存関係を確認：
   ```bash
   pip install -r requirements.txt
   ```

3. ログを確認：
   - GitHub Actions タブでワークフロー実行ログを確認

### イメージのプッシュが失敗する場合

- リポジトリの Settings > Actions > General で「Workflow permissions」が「Read and write permissions」に設定されているか確認
- GitHub Container Registry の可視性設定を確認（Private/Public）

## ベストプラクティス

1. **セキュリティ**
   - 機密情報（パスワード、APIキー）はGitHub Secretsに保存
   - `GITHUB_TOKEN` はワークフロー実行時のみ有効

2. **パフォーマンス**
   - キャッシュを活用してビルド時間を短縮
   - 並列ジョブで複数イメージを同時ビルド

3. **バージョン管理**
   - セマンティックバージョニング（v1.2.3）を使用
   - リリースタグでイメージを公開
