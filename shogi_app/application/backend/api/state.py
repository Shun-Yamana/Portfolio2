from typing import Any, Dict, Optional

from ..pieces import Board
from .game_helpers import (
    build_check_status,
    build_checkmate_status,
    build_game_status,
    create_initial_board,
)
from . import repository

GameState = Dict[str, Any]


def _make_initial_state() -> GameState:
    board: Board = create_initial_board()
    side_to_move = "upper"
    hands = {"upper": [], "lower": []}
    check_status = build_check_status(board)
    checkmate_status = build_checkmate_status(board, hands)
    game_status = build_game_status(checkmate_status)

    return {
        "board": board,
        "side_to_move": side_to_move,
        "hands": hands,
        "check_status": check_status,
        "checkmate_status": checkmate_status,
        "game_status": game_status,
    }


# 初期化
repository.initialize(_make_initial_state())


def get_current_state() -> GameState:
    return repository.get_current_state()


def set_current_state(new_state: GameState) -> None:
    repository.set_current_state(new_state)


def snapshot_previous_state() -> None:
    repository.snapshot_previous_state()


def get_previous_state() -> Optional[GameState]:
    return repository.get_previous_state()


def clear_previous_state() -> None:
    repository.clear_previous_state()


def increment_version() -> int:
    return repository.increment_version()


def get_version() -> int:
    return repository.get_version()


def reset_state() -> None:
    repository.reset(_make_initial_state())
