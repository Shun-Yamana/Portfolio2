from typing import Any, Dict, List, Optional, Tuple

from ..pieces import (
    EMPTY,
    Board,
    can_promote,
    force_promote,
    is_checkmate,
    is_in_check,
    is_promote_zone,
)

Position = Tuple[Optional[int], Optional[int]]
MoveOption = Dict[str, object]

UNPROMOTE_MAP = {
    "TO": "FU",
    "NY": "KY",
    "NK": "KE",
    "NG": "GI",
    "UM": "KA",
    "RY": "HI",
}


# 初期盤面を生成する。
def create_initial_board() -> Board:
    initial = [[EMPTY for _ in range(9)] for _ in range(9)]
    initial[0] = ["ky", "ke", "gi", "ki", "ou", "ki", "gi", "ke", "ky"]
    initial[1][1] = "hi"
    initial[1][7] = "ka"
    initial[2] = ["fu"] * 9
    initial[6] = ["FU"] * 9
    initial[7][1] = "KA"
    initial[7][7] = "HI"
    initial[8] = ["KY", "KE", "GI", "KI", "OU", "KI", "GI", "KE", "KY"]
    return initial


# 盤面形式の入力かを判定する。
def is_board_payload(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 9


# 王手状態をまとめて返す。
def build_check_status(current_board: Board) -> Dict[str, bool]:
    return {
        "upper": is_in_check(current_board, "upper"),
        "lower": is_in_check(current_board, "lower"),
    }


# 詰み状態をまとめて返す。
def build_checkmate_status(current_board: Board, hands: Dict[str, List[str]]) -> Dict[str, bool]:
    return {
        "upper": is_checkmate(current_board, "upper", hands),
        "lower": is_checkmate(current_board, "lower", hands),
    }


# 対局状態をレスポンス用に整形する。
def build_game_status(checkmate_status: Dict[str, bool]) -> Dict[str, Optional[str]]:
    game_status: Dict[str, Optional[str]] = {"state": "ongoing", "winner": None, "reason": None}
    if checkmate_status["upper"]:
        game_status["state"] = "ended"
        game_status["winner"] = "lower"
        game_status["reason"] = "checkmate"
    elif checkmate_status["lower"]:
        game_status["state"] = "ended"
        game_status["winner"] = "upper"
        game_status["reason"] = "checkmate"
    return game_status


# 指し手入力の座標を正規化する。
def parse_position(data: Dict[str, Any], key: str) -> Position:
    raw = data.get(f"{key}_pos")
    if isinstance(raw, list) and len(raw) == 2:
        return raw[0], raw[1]
    return data.get(f"{key}_row"), data.get(f"{key}_col")


# 合法手を成り候補付きの形式へ展開する。
def expand_legal_moves(raw_moves: List[Tuple[Tuple[int, int], str]], from_row: int, piece: str) -> List[MoveOption]:
    expanded_moves: List[MoveOption] = []
    for (to_row, to_col), move_type in raw_moves:
        can = can_promote(piece)
        in_zone = is_promote_zone(from_row, to_row, piece)
        forced = force_promote(to_row, piece)

        if can and in_zone and forced:
            expanded_moves.append({"row": to_row, "col": to_col, "type": move_type, "promote": True})
            continue
        if can and in_zone:
            expanded_moves.append({"row": to_row, "col": to_col, "type": move_type, "promote": False})
            expanded_moves.append({"row": to_row, "col": to_col, "type": move_type, "promote": True})
            continue
        expanded_moves.append({"row": to_row, "col": to_col, "type": move_type, "promote": False})
    return expanded_moves


# 手番を交代する。
def switch_side(side_to_move: str) -> str:
    return "lower" if side_to_move == "upper" else "upper"


# 捕獲駒を持ち駒へ追加する。
def add_captured_to_hands(hands: Dict[str, List[str]], captured_piece: str, mover_side: str) -> None:
    captured_base = UNPROMOTE_MAP.get(captured_piece.upper(), captured_piece.upper())
    if mover_side == "upper":
        hands["upper"].append(captured_base)
        return
    hands["lower"].append(captured_base.lower())


# 盤面更新を参照維持で反映する。
def sync_board(board: Board, new_board: Board) -> None:
    for row in range(9):
        board[row] = new_board[row]


# 打ち歩詰め判定で詰み成立かを確認する。
def is_drop_checkmate(new_board: Board, mover_side: str, hands: Dict[str, List[str]]) -> bool:
    opponent = switch_side(mover_side)
    if not is_in_check(new_board, opponent):
        return False
    return is_checkmate(new_board, opponent, hands)


# 打ち歩詰め禁じ手を判定する。
def is_uchifuzume_allowed(new_board: Board, mover_side: str, hand_piece: str, hands: Dict[str, List[str]]) -> bool:
    if hand_piece not in ("FU", "fu"):
        return True
    return not is_drop_checkmate(new_board, mover_side, hands)


# 駒打ちに関する制約違反を返す。
def validate_drop_constraints(
    target_board: Board,
    to_pos: Tuple[int, int],
    side_to_move: str,
    hand_piece: str,
) -> Optional[str]:
    if target_board[to_pos[0]][to_pos[1]] != EMPTY:
        return "Drop target must be empty."

    if hand_piece in ("FU", "fu"):
        own_fu = "FU" if side_to_move == "upper" else "fu"
        for row in range(9):
            if target_board[row][to_pos[1]] == own_fu:
                return "Nifu is not allowed."

    base = hand_piece.upper()
    to_row = to_pos[0]
    if base in ("FU", "KY"):
        if side_to_move == "upper" and to_row == 0:
            return "FU/KY cannot be dropped on last rank."
        if side_to_move == "lower" and to_row == 8:
            return "FU/KY cannot be dropped on last rank."
    if base == "KE":
        if side_to_move == "upper" and to_row <= 1:
            return "KE cannot be dropped on last two ranks."
        if side_to_move == "lower" and to_row >= 7:
            return "KE cannot be dropped on last two ranks."
    return None
