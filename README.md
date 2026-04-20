# Portfolio2

将棋アプリ（`shogi_app`）と AWS インフラ定義（`infrastructure`）を含むリポジトリです。

## 概要

9x9 将棋の Web アプリです。

- フロントエンド: React + Vite
- バックエンド: Flask
- 状態管理: `current_state` + `previous_state`（1手待った）
- 永続化: `repository` 経由（`memory` / `dynamodb` 切替）

## 主な機能

- 盤面表示、手番表示、持ち駒表示
- 合法手ハイライト
- 成り/不成
- 駒打ち
- 王手/詰み判定
- リセット
- 待った（1手戻し）

## ルール対応

- 自玉が王手になる手（自殺手）の禁止
- 二歩の禁止
- 行き場のない駒打ちの禁止（歩/香の最終段、桂の最終2段）
- 打ち歩詰めの禁止

## ディレクトリ構成

- `shogi_app/application/backend`: Flask API
- `shogi_app/application/frontend`: React + Vite
- `infrastructure/yaml_files`: AWS リソース定義

## ローカル起動

### バックエンド

```powershell
cd shogi_app/application
python -m backend.api.app
```

### フロントエンド

```powershell
cd shogi_app/application/frontend
npm install
npm run dev
```

## DynamoDB バックエンド利用

`repository.py` は環境変数で保存先を切り替えます。

- `SHOGI_REPOSITORY_BACKEND=memory`（デフォルト）
- `SHOGI_REPOSITORY_BACKEND=dynamodb`
- `SHOGI_TABLE=ShogiGames`
- `AWS_REGION`（例: `ap-northeast-1`）

起動例:

```powershell
cd shogi_app/application
$env:SHOGI_REPOSITORY_BACKEND="dynamodb"
$env:SHOGI_TABLE="ShogiGames"
$env:AWS_REGION="ap-northeast-1"
python -m backend.api.app
```

## API

- `GET /api/state`: 現在状態を取得
- `GET /api/board`: 盤面のみ取得
- `POST /api/legal_moves`: 合法手取得
- `POST /api/move`: 着手（通常移動/捕獲/駒打ち）
- `POST /api/undo`: 1手待った
- `POST /api/reset`: 初期局面へリセット

### `GET /api/state` レスポンス例

```json
{
  "success": true,
  "board": [["..."]],
  "side_to_move": "upper",
  "hands": { "upper": [], "lower": [] },
  "check_status": { "upper": false, "lower": false },
  "checkmate_status": { "upper": false, "lower": false },
  "game_status": { "state": "ongoing", "winner": null, "reason": null },
  "version": 0
}
```

### `POST /api/move` リクエスト例（通常移動）

```json
{
  "from_pos": [6, 4],
  "to_pos": [5, 4],
  "move_type": "move",
  "piece": "FU",
  "promote": false
}
```

### `POST /api/undo` レスポンス例

```json
{
  "success": true,
  "board": [["..."]],
  "side_to_move": "upper",
  "hands": { "upper": [], "lower": [] },
  "check_status": { "upper": false, "lower": false },
  "checkmate_status": { "upper": false, "lower": false },
  "game_status": { "state": "ongoing", "winner": null, "reason": null },
  "version": 2
}
```

`previous_state` がない場合は `400` で `No move to undo.` を返します。

## AWS インフラ構成

CloudFormation で管理する完全サーバーレス対応の本番インフラです。

### アーキテクチャ概要

```
Internet
   │
   ▼
[Elastic IP] ← Lambda Failover が切り替え
   │
   ├─ Primary EC2 (t3.micro, Private Subnet)
   └─ Standby EC2 (t3.micro, Private Subnet, 通常停止中)
          │
          ▼
     [DynamoDB: ShogiGames]
          │
     [S3: shogi-app-packages-{AccountId}]
```

- EC2 は **プライベートサブネット**に配置し、パブリック IP なし
- 管理アクセスはすべて **SSM Session Manager** 経由（SSH ポート不要）
- NAT Gateway 経由でアウトバウンド通信
- SSM / S3 / DynamoDB は VPC Endpoint 経由（インターネット非経由）

### CloudFormation スタック一覧・デプロイ順序

| 順序 | ファイル | 説明 |
|------|----------|------|
| 1 | `network.yaml` | VPC / サブネット / IGW / NAT GW / SG / VPC Endpoints |
| 2 | `iam.yaml` | 各サービス用 IAM ロール / インスタンスプロファイル |
| 3 | `s3.yaml` | Python パッケージ配布用 S3 バケット |
| 4 | `dynamodb.yaml` | ゲーム状態管理 DynamoDB テーブル |
| 5 | `ec2.yaml` | Primary EC2 / SSM Patch Baseline / DLM スナップショット |
| 6 | `lambda_patch.yaml` | パッチ適用 Lambda（本番用・Install） |
| 7 | `lambda_patch_test.yaml` | パッチスキャン Lambda（テスト用・Scan のみ） |
| 8 | `eventbridge.yaml` | 週次パッチスケジュール（毎週日曜 14:00 JST） |
| 9 | `lambda_eip.yaml` | 自動フェイルオーバー一式（Standby EC2 / EIP / CloudWatch Alarm） |

### 各スタック詳細

#### network.yaml
- VPC: `10.0.0.0/16`（DNS ホスト名有効）
- Private Subnet: `10.0.1.0/24`（EC2 配置先、パブリック IP なし）
- Public Subnet: `10.0.2.0/24`（NAT Gateway 配置先）
- VPC Interface Endpoints: `ssm` / `ssmmessages` / `ec2messages`（SSM 通信のインターネット非経由化）
- VPC Gateway Endpoint: `s3`（S3 アクセスのインターネット非経由化）
- Security Group: VPC 内からの HTTPS (443) のみ許可

#### iam.yaml
| ロール | 用途 |
|--------|------|
| `EC2-SSM-ManagedRole` | EC2 用。SSM マネージド + S3 読み取り + DynamoDB CRUD |
| `PatchCommanderLambdaRole` | パッチ Lambda 用。EC2 Describe + SSM SendCommand |
| `Lambda-EIP-Switch-Role` | フェイルオーバー Lambda 用。EC2 EIP 操作 + インスタンス起動停止 |
| `DLM-EC2-Snapshot-Role` | EBS スナップショット自動管理用 |

#### s3.yaml
- バケット名: `shogi-app-packages-{AccountId}`
- パブリックアクセス完全ブロック、バージョニング有効、AES-256 暗号化
- EC2 上へのアプリデプロイ（ZIP パッケージ）に使用

#### dynamodb.yaml
- テーブル名: `ShogiGames`、パーティションキー: `game_id`（String）
- プロビジョンドキャパシティ（1 RCU/WCU）+ Auto Scaling（1〜5、使用率 70% で拡張）
- PITR（ポイントインタイムリカバリ）有効、`DeletionPolicy: Retain`

#### ec2.yaml
- AMI: Amazon Linux 2（SSM パラメータストアから最新版を自動取得）
- インスタンスタイプ: t3.micro、ルートボリューム: gp3 / 30 GiB / 暗号化
- **SSM Patch Baseline**: Security・Bugfix カテゴリの Critical/Important パッチを 7 日後に自動承認（カーネルパッチは除外）
- **DLM スナップショット**: 毎日 03:00 JST にスナップショット取得、7 世代保持

#### lambda_patch.yaml / lambda_patch_test.yaml
- `PatchCommander`（本番）: `AWS-RunPatchBaseline` を `Install` モードで実行。パッチ適用後に必要に応じて再起動。
- `PatchCommanderScan`（テスト）: `Scan` モードのみ。実際の適用・再起動なし。

#### eventbridge.yaml
- EventBridge ルール: 毎週日曜 14:00 JST に `PatchCommander` Lambda を起動
- `ShogiEC2PatchGroup` タグを持つ実行中 EC2 を自動検出して実行

#### lambda_eip.yaml（自動フェイルオーバー）
- **Standby EC2**: 通常は停止状態で待機。フェイルオーバー時に自動起動。
- **Service EIP**: Primary / Standby 間で共有する固定 IP。Lambda が付け替えることでフェイルオーバー。
- **Emergency EIP**: 緊急時の直接アクセス用。
- **CloudWatch Composite Alarm**: 以下の条件が揃った場合にアラーム発火
  - `(StatusCheck 5 分間失敗 OR CPU 0% 以下が 3 分間) AND NetworkOut 0 が 3 分間`
- **フロー**:
  1. CloudWatch Alarm → SNS → Lambda 起動
  2. `ALARM`: Standby 起動 → EIP を Standby に付け替え（フェイルオーバー）
  3. `OK`: Primary 起動 → EIP を Primary に戻し、Standby 停止（フェイルバック）

### デプロイ用 ZIP

バックエンド ZIP は以下に生成済みです。

- `deploy/shogi_app_backend.zip`

S3 アップロード例:

```powershell
aws s3 cp deploy/shogi_app_backend.zip s3://shogi-app-packages-203553641035/releases/shogi_app_backend.zip
```
