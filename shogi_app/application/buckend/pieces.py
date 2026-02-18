from typing import List, Tuple, Optional, Dict, Set
import copy

# ===== 型エイリアス =====
Position = Tuple[int, int]
Move = Tuple[int, int]
Board = List[List[str]]
EMPTY = "EMPTY"

PROMOTE_MAP: Dict[str, str] = {
    "FU": "TO",
    "KY": "NY",
    "KE": "NK",
    "GI": "NG",
    "HI": "RY",
    "KA": "UM",
}

DIRECTION_VECTORS: Dict[str, Move] = {
    "N": (-1, 0),
    "NE": (-1, 1),
    "E": (0, 1),
    "SE": (1, 1),
    "S": (1, 0),
    "SW": (1, -1),
    "W": (0, -1),
    "NW": (-1, -1),
    "NNE": (-2, 1),
    "NNW": (-2, -1),
}

BASE_MOVE_DIRECTIONS: Dict[str, List[str]] = {
    "FU": ["N"],
    "GI": ["N", "NE", "NW", "SE", "SW"],
    "KI": ["N", "E", "W", "S", "NE", "NW"],
    "TO": ["N", "E", "W", "S", "NE", "NW"],
    "NY": ["N", "E", "W", "S", "NE", "NW"],
    "NK": ["N", "E", "W", "S", "NE", "NW"],
    "NG": ["N", "E", "W", "S", "NE", "NW"],
    "OU": ["N", "E", "W", "S", "NE", "SE", "SW", "NW"],
    "KE": ["NNE", "NNW"],
    "KY": ["N"],
    "HI": ["N", "E", "S", "W"],
    "KA": ["NE", "SE", "SW", "NW"],
    "RY": ["N", "E", "S", "W", "NE", "SE", "SW", "NW"],
    "UM": ["N", "E", "S", "W", "NE", "SE", "SW", "NW"],
}

# ===== 駒タイプ =====
def get_piece_type(piece: str) -> str:
    base = piece.upper()
    if base in ("HI", "KA", "KY", "RY", "UM"):
        return "slide"
    elif base == "KE":
        return "jump"
    else:
        return "step"

# ===== 方向 → 移動ベクトル =====
def move_piece(direction: str) -> Move:
    if direction not in DIRECTION_VECTORS:
        raise ValueError(f"Unknown direction: {direction}")
    return DIRECTION_VECTORS[direction]


def _piece_directions(piece: str) -> List[str]:
    mapping = dict(BASE_MOVE_DIRECTIONS)
    mapping.update({key.lower(): value for key, value in BASE_MOVE_DIRECTIONS.items()})
    return mapping[piece]

# ===== 移動方向一覧 =====
def move_list(piece: str) -> List[Move]:
    return [move_piece(direction) for direction in _piece_directions(piece)]


def _unlimited_directions(piece: str) -> Set[str]:
    base = piece.upper()
    if base == "KY":
        return {"N"}
    if base == "HI":
        return {"N", "E", "S", "W"}
    if base == "KA":
        return {"NE", "SE", "SW", "NW"}
    if base == "RY":
        return {"N", "E", "S", "W"}
    if base == "UM":
        return {"NE", "SE", "SW", "NW"}
    return set()


def _move_specs(piece: str) -> List[Tuple[Move, Optional[int]]]:
    unlimited = _unlimited_directions(piece)

    specs: List[Tuple[Move, Optional[int]]] = []
    for direction in _piece_directions(piece):
        limit: Optional[int] = None if direction in unlimited else 1
        specs.append((move_piece(direction), limit))
    return specs

# ===== 盤面チェック =====
def is_on_board(row: int, col: int) -> bool:
    return 0 <= row < 9 and 0 <= col < 9

# ===== 方向補正 =====
def orient_move(dr: int, dc: int, piece: str) -> Move:
    # 後手（小文字）は前後を反転
    if piece.islower():
        return -dr, dc
    return dr, dc

# ==== 敵味方判定 ====
def classify_cell(piece: str, state: str) -> str:
    if state == EMPTY:
        return "empty"

    # moving_piece と同じ大小なら味方、違えば敵
    if piece.isupper() == state.isupper():
        return "friend"
    return "enemy"


def can_promote(piece: str) -> bool:
    base = piece.upper()
    return base in {"FU", "KY", "KE", "GI", "HI", "KA"}


def is_promote_zone(from_row: int, to_row: int, piece: str) -> bool:
    if (piece.isupper() and from_row <= 2) or (piece.isupper() and to_row <= 2):
        return True
    if (piece.islower() and from_row >= 6) or (piece.islower() and to_row >= 6):
        return True
    return False


def force_promote(to_row: int, piece: str) -> bool:
    base = piece.upper()
    if base in {"FU", "KY"}:
        if piece.isupper() and to_row == 0:
            return True
        if piece.islower() and to_row == 8:
            return True
    if base == "KE":
        if piece.isupper() and to_row <= 1:
            return True
        if piece.islower() and to_row >= 7:
            return True
    return False


def promotion(piece: str, promote: bool) -> str:
    piece_to_place = piece
    base = piece.upper()

    if promote:
        promoted_base = PROMOTE_MAP[base]
        piece_to_place = promoted_base.lower() if piece.islower() else promoted_base

    return piece_to_place


def find_king_position(board: Board, target: str) -> Optional[Position]:
    king = "OU" if target == "upper" else "ou"
    for row in range(9):
        for col in range(9):
            if board[row][col] == king:
                return (row, col)
    return None


def is_in_check(board: Board, target: str) -> bool:
    king_pos = find_king_position(board, target)
    if king_pos is None:
        return False

    for row in range(9):
        for col in range(9):
            piece = board[row][col]
            if piece == EMPTY:
                continue
            if target == "upper" and piece.islower():
                moves = generate_legal_moves(board, (row, col), piece)
                for move_pos, _ in moves:
                    if move_pos == king_pos:
                        return True
            elif target == "lower" and piece.isupper():
                moves = generate_legal_moves(board, (row, col), piece)
                for move_pos, _ in moves:
                    if move_pos == king_pos:
                        return True
    return False

# ===== 合法手の生成 =====
def generate_legal_moves(
    board: Board,
    current_position: Position,
    piece: str,
) -> List[Tuple[Position, str]]:

    legal_moves: List[Tuple[Position, str]] = []

    row, col = current_position
    move_specs = _move_specs(piece)

    for (dr, dc), limit in move_specs:
        dr, dc = orient_move(dr, dc, piece)
        i = 1

        while True:
            new_row = row + dr * i
            new_col = col + dc * i

            if not is_on_board(new_row, new_col):
                break

            state = board[new_row][new_col]
            cell_class = classify_cell(piece, state)

            if cell_class == "empty":
                legal_moves.append(((new_row, new_col), "move"))
            elif cell_class == "enemy":
                legal_moves.append(((new_row, new_col), "capture"))
                break
            else:  # friend
                break

            if limit == 1:
                break

            i += 1

    return legal_moves

def apply_move(
    board: Board,
    from_pos: Position,
    to_pos: Position,
    move_type: str,
    piece: str
) -> Tuple[Board, Optional[str]]:

    updated_board = copy.deepcopy(board)
    captured_piece: Optional[str] = None

    if move_type == "capture":
        captured_piece = updated_board[to_pos[0]][to_pos[1]]
        # 捕獲された駒を処理するロジックを追加できます

    updated_board[to_pos[0]][to_pos[1]] = piece
    updated_board[from_pos[0]][from_pos[1]] = EMPTY

    return updated_board, captured_piece


def _can_drop_piece(board: Board, target: str, hand_piece: str, to_pos: Position) -> bool:
    row, col = to_pos
    if not is_on_board(row, col):
        return False
    if board[row][col] != EMPTY:
        return False

    base = hand_piece.upper()
    # 二歩
    if base == "FU":
        own_fu = "FU" if target == "upper" else "fu"
        for r in range(9):
            if board[r][col] == own_fu:
                return False

    # 行き場のない打ち駒
    if base in ("FU", "KY"):
        if target == "upper" and row == 0:
            return False
        if target == "lower" and row == 8:
            return False
    if base == "KE":
        if target == "upper" and row <= 1:
            return False
        if target == "lower" and row >= 7:
            return False

    return True


def _can_escape_by_drop(board: Board, target: str, hands: Dict[str, List[str]]) -> bool:
    # target側の持ち駒で王手回避できる手があるか探索
    for raw_piece in hands.get(target, []):
        hand_piece = raw_piece.upper() if target == "upper" else raw_piece.lower()
        for row in range(9):
            for col in range(9):
                if not _can_drop_piece(board, target, hand_piece, (row, col)):
                    continue
                new_board = copy.deepcopy(board)
                new_board[row][col] = hand_piece
                if not is_in_check(new_board, target):
                    return True
    return False


def is_checkmate(board: Board, target: str, hands: Optional[Dict[str, List[str]]] = None) -> bool:
    # 王手中でなければ詰みではない
    if not is_in_check(board, target):
        return False

    friends: List[Tuple[int, int, str]] = []
    for row in range(9):
        for col in range(9):
            piece = board[row][col]
            if piece == EMPTY:
                continue
            if target == "upper" and piece.isupper():
                friends.append((row, col, piece))
            elif target == "lower" and piece.islower():
                friends.append((row, col, piece))

    for friend_row, friend_col, friend_piece in friends:
        moves = generate_legal_moves(board, (friend_row, friend_col), friend_piece)
        for move_pos, move_type in moves:
            can = can_promote(friend_piece)
            in_zone = is_promote_zone(friend_row, move_pos[0], friend_piece)
            forced = force_promote(move_pos[0], friend_piece)

            if can and in_zone and forced:
                promote_options = [True]
            elif can and in_zone:
                promote_options = [False, True]
            else:
                promote_options = [False]

            for promote_option in promote_options:
                piece_to_place = promotion(friend_piece, promote_option)
                new_board, _ = apply_move(
                    board,
                    (friend_row, friend_col),
                    move_pos,
                    move_type,
                    piece_to_place,
                )
                if not is_in_check(new_board, target):
                    return False

    # 盤上移動で回避できない場合、持ち駒による受けも確認
    if hands is not None and _can_escape_by_drop(board, target, hands):
        return False

    return True



    

  
        
