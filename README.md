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

## デプロイ用 ZIP

バックエンド ZIP は以下に生成済みです。

- `deploy/shogi_app_backend.zip`

S3 アップロード例:

```powershell
aws s3 cp deploy/shogi_app_backend.zip s3://shogi-app-packages-203553641035/releases/shogi_app_backend.zip
```
