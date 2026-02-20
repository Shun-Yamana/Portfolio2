from flask import Flask, jsonify, request
import copy

from ..pieces import (
    Board,
    apply_move,
    can_promote,
    force_promote,
    generate_legal_moves,
    is_in_check,
    is_on_board,
    is_promote_zone,
    promotion,
)
from .game_helpers import (
    add_captured_to_hands,
    build_check_status,
    build_checkmate_status,
    build_game_status,
    expand_legal_moves,
    is_uchifuzume_allowed,
    parse_position,
    switch_side,
    validate_drop_constraints,
)

from .state import (
    get_current_state,
    set_current_state,
    snapshot_previous_state,
    get_previous_state,
    clear_previous_state,   
    increment_version,
    get_version,
    reset_state,
)

app = Flask(__name__)

# 状態を初期化する。
def _reset_game_state() -> None:
    reset_state()


def _build_state_payload(board: Board, side_to_move: str, hands: dict):
    check_status = build_check_status(board)
    checkmate_status = build_checkmate_status(board, hands)
    return {
        "board": board,
        "side_to_move": side_to_move,
        "hands": hands,
        "check_status": check_status,
        "checkmate_status": checkmate_status,
        "game_status": build_game_status(checkmate_status),
    }

# 共通の状態ペイロードを返す。
def _state_payload(current_state: dict):
    return {
        "board": current_state["board"],
        "side_to_move": current_state["side_to_move"],
        "hands": current_state["hands"],
        "check_status": current_state["check_status"],
        "checkmate_status": current_state["checkmate_status"],
        "game_status": current_state["game_status"],
    }

@app.route("/api/board", methods=["GET"])
def get_board():
    return jsonify(get_current_state()["board"])


@app.route("/api/state", methods=["GET"])
def get_state():
    state = get_current_state()
    return jsonify({
        "success": True,
        **_state_payload(state),
        "version": get_version(),
    })


@app.route("/api/reset", methods=["POST"])
def reset_game():
    _reset_game_state()
    state = get_current_state()
    return jsonify({"success": True, **_state_payload(state), "version": get_version()})


@app.route("/api/legal_moves", methods=["POST"])
def legal_moves():
    state = get_current_state()
    data = request.get_json(silent=True) or {}
    row = data.get("row")
    col = data.get("col")
    piece = data.get("piece")

    target_board = state["board"]

    if row is None or col is None or piece is None:
        return jsonify({
            "legal_moves": [],
            "error": "Invalid request. Required: row, col, piece."
        }), 400

    if not is_on_board(row, col):
        return jsonify({
            "legal_moves": [],
            "error": "Position is out of board."
        }), 400

    moving_piece = target_board[row][col]
    if moving_piece != piece:
        return jsonify({
            "legal_moves": [],
            "error": "Piece mismatch at selected position."
        }), 400

    if state["side_to_move"] == "upper" and not moving_piece.isupper():
        return jsonify({"legal_moves": []})
    if state["side_to_move"] == "lower" and not moving_piece.islower():
        return jsonify({"legal_moves": []})

    raw_moves = generate_legal_moves(target_board, (row, col), piece)
    return jsonify({"legal_moves": expand_legal_moves(raw_moves, row, piece)})


@app.route("/api/move", methods=["POST"])
def move():
    state = get_current_state()
    board = state["board"]
    side_to_move = state["side_to_move"]
    hands = copy.deepcopy(state["hands"])

    current_checkmate = build_checkmate_status(board, hands)
    current_game_status = build_game_status(current_checkmate)
    if current_game_status["state"] == "ended":
        return jsonify({
            "success": False,
            "error": "Game already ended.",
            "game_status": current_game_status,
        }), 409

    data = request.get_json(silent=True) or {}

    from_pos = parse_position(data, "from")
    to_pos = parse_position(data, "to")

    piece = data.get("piece")
    drop_piece = data.get("drop_piece")
    move_type = data.get("move_type")
    promote = bool(data.get("promote", False))
    target_board = board

    if to_pos[0] is None or to_pos[1] is None or move_type not in ("move", "capture", "drop"):
        return jsonify({
            "success": False,
            "error": "Invalid request. Required: move_type and to_pos."
        }), 400

    if not is_on_board(to_pos[0], to_pos[1]):
        return jsonify({
            "success": False,
            "error": "Position is out of board."
        }), 400

    if move_type == "drop":
        if not drop_piece:
            return jsonify({
                "success": False,
                "error": "drop_piece is required for drop move."
            }), 400

        hand_piece = drop_piece.upper() if side_to_move == "upper" else drop_piece.lower()
        if hand_piece not in hands[side_to_move]:
            return jsonify({
                "success": False,
                "error": "Selected piece is not in hand."
            }), 400

        drop_error = validate_drop_constraints(target_board, to_pos, side_to_move, hand_piece)
        if drop_error:
            return jsonify({"success": False, "error": drop_error}), 400

        new_board = copy.deepcopy(target_board)
        new_board[to_pos[0]][to_pos[1]] = hand_piece
        if is_in_check(new_board, side_to_move):
            return jsonify({
                "success": False,
                "error": "Self-check is not allowed."
            }), 400
        if not is_uchifuzume_allowed(new_board, side_to_move, hand_piece, hands):
            return jsonify({
                "success": False,
                "error": "Uchifuzume is not allowed."
            }), 400

        hands[side_to_move].remove(hand_piece)
        new_side = switch_side(side_to_move)
        new_state = _build_state_payload(new_board, new_side, hands)
        snapshot_previous_state()
        set_current_state(new_state)
        increment_version()
        return jsonify({
            "success": True,
            "captured_piece": None,
            "promoted": False,
            **_state_payload(new_state),
            "version": get_version(),
        })

    if (
        from_pos[0] is None
        or from_pos[1] is None
        or piece is None
    ):
        return jsonify({
            "success": False,
            "error": "Invalid request. Required: piece and from_pos for move/capture."
        }), 400

    if not is_on_board(from_pos[0], from_pos[1]):
        return jsonify({
            "success": False,
            "error": "Position is out of board."
        }), 400

    if target_board[from_pos[0]][from_pos[1]] != piece:
        return jsonify({
            "success": False,
            "error": "Piece mismatch at from_pos."
        }), 400

    moving_piece = target_board[from_pos[0]][from_pos[1]]
    if side_to_move == "upper" and not moving_piece.isupper():
        return jsonify({
            "success": False,
            "error": "Not upper's turn piece."
        }), 400
    if side_to_move == "lower" and not moving_piece.islower():
        return jsonify({
            "success": False,
            "error": "Not lower's turn piece."
        }), 400

    legal_moves = generate_legal_moves(target_board, from_pos, piece)
    matched = next((m for m in legal_moves if m[0] == to_pos), None)
    if matched is None:
        return jsonify({
            "success": False,
            "error": "Illegal move."
        }), 400

    if move_type != matched[1]:
        return jsonify({
            "success": False,
            "error": "move_type does not match legal move type."
        }), 400

    from_row = from_pos[0]
    to_row = to_pos[0]
    if promote and not can_promote(piece):
        return jsonify({
            "success": False,
            "error": "This piece cannot promote."
        }), 400
    if promote and not is_promote_zone(from_row, to_row, piece):
        return jsonify({
            "success": False,
            "error": "Promotion is not allowed outside promotion zone."
        }), 400
    if (not promote) and force_promote(to_row, piece):
        return jsonify({
            "success": False,
            "error": "This move requires promotion."
        }), 400

    piece_to_place = promotion(piece, promote)

    new_board, captured_piece = apply_move(
        board=target_board,
        from_pos=from_pos,
        to_pos=to_pos,
        move_type=move_type,
        piece=piece_to_place,
    )

    if is_in_check(new_board, side_to_move):
        return jsonify({
            "success": False,
            "error": "Self-check is not allowed."
        }), 400

    if captured_piece is not None:
        add_captured_to_hands(hands, captured_piece, side_to_move)

    new_side = switch_side(side_to_move)
    new_state = _build_state_payload(new_board, new_side, hands)
    snapshot_previous_state()
    set_current_state(new_state)
    increment_version()
    return jsonify({
        "success": True,
        "captured_piece": captured_piece if move_type == "capture" else None,
        "promoted": promote,
        **_state_payload(new_state),
        "version": get_version(),
    })

@app.route("/api/undo", methods=["POST"])
def undo_move():  
    prev = get_previous_state()  
    if prev is None:
        return jsonify({"success": False, "message": "No move to undo."}), 400
    set_current_state(prev)
    clear_previous_state()
    increment_version()
    return jsonify({"success": True, **_state_payload(get_current_state()), "version": get_version()})

if __name__ == "__main__":
    app.run(debug=True)
