import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

GameState = Dict[str, Any]
GameRecord = Dict[str, Any]

TABLE_NAME = os.getenv("SHOGI_TABLE", "ShogiGames")
DEFAULT_GAME_ID = os.getenv("DEFAULT_GAME_ID", "game-1")
BACKEND = os.getenv("SHOGI_REPOSITORY_BACKEND", "memory").lower()

_memory_record: Optional[GameRecord] = None

_dynamodb_resource = None
_dynamodb_table = None
_dynamodb_client_error = None

if BACKEND == "dynamodb":
    try:
        import boto3
        from botocore.exceptions import ClientError

        _dynamodb_resource = boto3.resource("dynamodb")
        _dynamodb_table = _dynamodb_resource.Table(TABLE_NAME)
        _dynamodb_client_error = ClientError
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "DynamoDB backend is enabled, but boto3 initialization failed. "
            "Install boto3 and set AWS credentials/region."
        ) from exc


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_record(initial_state: GameState, game_id: str) -> GameRecord:
    return {
        "game_id": game_id,
        "current_state": deepcopy(initial_state),
        "previous_state": None,
        "version": 0,
        "updated_at": _now_iso(),
    }


def _get_record(game_id: str = DEFAULT_GAME_ID) -> GameRecord:
    if BACKEND == "memory":
        if _memory_record is None:
            raise KeyError("game_not_found")
        if _memory_record["game_id"] != game_id:
            raise KeyError("game_not_found")
        return deepcopy(_memory_record)

    response = _dynamodb_table.get_item(Key={"game_id": game_id}, ConsistentRead=True)
    item = response.get("Item")
    if not item:
        raise KeyError("game_not_found")
    return item


def create_game(initial_state: GameState, game_id: str = DEFAULT_GAME_ID) -> None:
    if BACKEND == "memory":
        global _memory_record
        if _memory_record is not None and _memory_record["game_id"] == game_id:
            raise ValueError("game_already_exists")
        _memory_record = _empty_record(initial_state, game_id)
        return

    try:
        _dynamodb_table.put_item(
            Item=_empty_record(initial_state, game_id),
            ConditionExpression="attribute_not_exists(game_id)",
        )
    except _dynamodb_client_error as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            raise ValueError("game_already_exists") from exc
        raise


def get_game(game_id: str = DEFAULT_GAME_ID) -> GameRecord:
    return deepcopy(_get_record(game_id))


def update_game(record: GameRecord, game_id: str = DEFAULT_GAME_ID) -> None:
    if BACKEND == "memory":
        global _memory_record
        _memory_record = {
            "game_id": game_id,
            "current_state": deepcopy(record["current_state"]),
            "previous_state": deepcopy(record.get("previous_state")),
            "version": int(record["version"]),
            "updated_at": record.get("updated_at") or _now_iso(),
        }
        return

    _dynamodb_table.put_item(
        Item={
            "game_id": game_id,
            "current_state": deepcopy(record["current_state"]),
            "previous_state": deepcopy(record.get("previous_state")),
            "version": int(record["version"]),
            "updated_at": record.get("updated_at") or _now_iso(),
        }
    )


def reset_game(initial_state: GameState, game_id: str = DEFAULT_GAME_ID) -> None:
    if BACKEND == "memory":
        global _memory_record
        if _memory_record is None or _memory_record["game_id"] != game_id:
            raise KeyError("game_not_found")
        _memory_record["current_state"] = deepcopy(initial_state)
        _memory_record["previous_state"] = None
        _memory_record["version"] = 0
        _memory_record["updated_at"] = _now_iso()
        return

    _dynamodb_table.update_item(
        Key={"game_id": game_id},
        UpdateExpression="SET current_state=:c, previous_state=:p, version=:v, updated_at=:u",
        ExpressionAttributeValues={
            ":c": deepcopy(initial_state),
            ":p": None,
            ":v": 0,
            ":u": _now_iso(),
        },
    )


def initialize(initial_state: GameState, game_id: str = DEFAULT_GAME_ID) -> None:
    try:
        create_game(initial_state, game_id)
    except ValueError:
        # 既存対局がある場合は初期化をスキップして継続する。
        return


def get_current_state(game_id: str = DEFAULT_GAME_ID) -> GameState:
    return deepcopy(_get_record(game_id)["current_state"])


def set_current_state(new_state: GameState, game_id: str = DEFAULT_GAME_ID) -> None:
    record = _get_record(game_id)
    record["current_state"] = deepcopy(new_state)
    record["updated_at"] = _now_iso()
    update_game(record, game_id)


def snapshot_previous_state(game_id: str = DEFAULT_GAME_ID) -> None:
    record = _get_record(game_id)
    record["previous_state"] = deepcopy(record["current_state"])
    record["updated_at"] = _now_iso()
    update_game(record, game_id)


def get_previous_state(game_id: str = DEFAULT_GAME_ID) -> Optional[GameState]:
    previous = _get_record(game_id).get("previous_state")
    return deepcopy(previous) if previous is not None else None


def clear_previous_state(game_id: str = DEFAULT_GAME_ID) -> None:
    record = _get_record(game_id)
    record["previous_state"] = None
    record["updated_at"] = _now_iso()
    update_game(record, game_id)


def increment_version(game_id: str = DEFAULT_GAME_ID) -> int:
    if BACKEND == "memory":
        record = _get_record(game_id)
        record["version"] = int(record["version"]) + 1
        record["updated_at"] = _now_iso()
        update_game(record, game_id)
        return int(record["version"])

    response = _dynamodb_table.update_item(
        Key={"game_id": game_id},
        UpdateExpression="SET version = version + :one, updated_at=:u",
        ExpressionAttributeValues={":one": 1, ":u": _now_iso()},
        ReturnValues="UPDATED_NEW",
    )
    return int(response["Attributes"]["version"])


def get_version(game_id: str = DEFAULT_GAME_ID) -> int:
    return int(_get_record(game_id)["version"])


def reset(initial_state: GameState, game_id: str = DEFAULT_GAME_ID) -> None:
    reset_game(initial_state, game_id)
