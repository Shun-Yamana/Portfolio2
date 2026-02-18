# Portfolio2

将棋アプリ（`shogi_app`）とインフラ定義（`infrastructure`）を含むリポジトリです。

## アプリ内容

このアプリは、Web 上で 9x9 の将棋対局を行うためのシンプルな実装です。  
フロントエンド（React）が盤面UIを担当し、バックエンド（Flask）が合法手判定や対局状態管理を担当します。

現在はアプリケーションのルール実装（合法手、禁じ手、王手/詰み判定）を中心に完成しており、永続化やインフラ連携は拡張予定です。

### 主な機能

- 盤面表示、手番表示、持ち駒表示
- 駒選択時の合法手ハイライト
- 成り/不成の選択
- 駒打ち（持ち駒からの打ち）
- 王手・詰み判定
- リセット機能

### ルール対応（実装済み）

- 自玉が王手になる手（自殺手）の禁止
- 二歩の禁止
- 行き場のない駒打ちの禁止（歩/香の最終段、桂の最終2段）
- 打ち歩詰めの禁止

## 構成

- `shogi_app/`
  - `application/backend/`: Flask API（盤面管理・合法手・着手）
  - `application/frontend/`: React + Vite フロントエンド
- `infrastructure/`: AWS 用 YAML などのインフラ関連ファイル

## ローカル起動

### 1. バックエンド（Flask）

```powershell
cd shogi_app/application
python -m backend.api.app
```

デフォルトでは `http://127.0.0.1:5000` で API が起動します。

### 2. フロントエンド（React + Vite）

```powershell
cd shogi_app/application/frontend
npm install
npm run dev
```

Vite 開発サーバー起動後、表示された URL にアクセスしてください。

## 基本操作

1. 自分の駒をクリックして選択
2. ハイライト先をクリックして移動
3. 成れる場合は「はい/いいえ」を選択
4. 持ち駒を打つ場合は、持ち駒ボタンを選択後、打てるマスをクリック
5. 「リセット」で初期局面に戻す

## 主要 API

- `GET /api/state`: 盤面・手番・持ち駒・王手/詰み状態を取得
- `POST /api/legal_moves`: 指定駒の合法手を取得
- `POST /api/move`: 通常移動/捕獲/駒打ちを実行
- `POST /api/reset`: 対局状態を初期化
- `GET /api/board`: 盤面のみ取得

## API リクエスト/レスポンス例（JSON）

### `GET /api/state`

レスポンス:

```json
{
  "board": [["...省略..."]],
  "side_to_move": "upper",
  "hands": { "upper": [], "lower": [] },
  "check_status": { "upper": false, "lower": false },
  "checkmate_status": { "upper": false, "lower": false },
  "game_status": { "state": "ongoing", "winner": null, "reason": null }
}
```

### `POST /api/legal_moves`

リクエスト:

```json
{
  "board": [["...省略..."]],
  "row": 6,
  "col": 4,
  "piece": "FU"
}
```

レスポンス:

```json
{
  "legal_moves": [
    { "row": 5, "col": 4, "type": "move", "promote": false }
  ]
}
```

### `POST /api/move`（通常移動）

リクエスト:

```json
{
  "board": [["...省略..."]],
  "from_pos": [6, 4],
  "to_pos": [5, 4],
  "move_type": "move",
  "piece": "FU",
  "promote": false
}
```

レスポンス:

```json
{
  "success": true,
  "captured_piece": null,
  "promoted": false,
  "board": [["...省略..."]],
  "side_to_move": "lower",
  "hands": { "upper": [], "lower": [] },
  "check_status": { "upper": false, "lower": false },
  "checkmate_status": { "upper": false, "lower": false },
  "game_status": { "state": "ongoing", "winner": null, "reason": null }
}
```

### `POST /api/move`（駒打ち）

リクエスト:

```json
{
  "board": [["...省略..."]],
  "move_type": "drop",
  "drop_piece": "FU",
  "to_pos": [4, 4]
}
```

エラーレスポンス例（二歩）:

```json
{
  "success": false,
  "error": "Nifu is not allowed."
}
```

### `POST /api/reset`

レスポンス:

```json
{
  "success": true,
  "board": [["...省略..."]],
  "side_to_move": "upper",
  "hands": { "upper": [], "lower": [] },
  "check_status": { "upper": false, "lower": false },
  "checkmate_status": { "upper": false, "lower": false },
  "game_status": { "state": "ongoing", "winner": null, "reason": null }
}
```

## 実装で難しかった点

- 合法手の生成
- 打ち駒の打てる範囲の計算
- 詰み、王手のロジック

## 技術スタック

- Frontend: React, Vite
- Backend: Python, Flask
- Infrastructure: AWS（予定）

## 今後の拡張予定

- DB 連携による盤面状態の永続化（対局の保存/再開、履歴管理）
- インフラ構成の完成（デプロイ構成、運用導線、監視/ログ整理）
- 認証やユーザー単位の対局管理機能の追加

## 備考

- フロントエンドは `/api/*` をバックエンドへ呼び出します。
- 現在はルール部分のみ完成しています。
