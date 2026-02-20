current_state = (board, side_to_move, hands, check_status, checkmate_status, game_status) 
previous_state = (board, side_to_move, hands, check_status, checkmate_status, game_status) = (None, None, None, None, None, None)
version = (number: int) = (0)

@app.route("/api/undo", methods=["POST"])
def undo_move():
    global board, side_to_move, hands, check_status, checkmate_status, game_status, version
    if previous_state == (None, None, None, None, None, None):
        return jsonify({"success": False, "message": "No move to undo."}), 400

    # 現在の状態をprevious_stateに保存
    current_state = (board, side_to_move, hands, check_status, checkmate_status, game_status)

    # previous_stateから状態を復元
    board, side_to_move, hands, check_status, checkmate_status, game_status = previous_state
    
    previous_state = (None, None, None, None, None, None)  # previous_stateをリセット

    version += 1
    return jsonify({"success": True, **_state_payload(board), "version": version})


# move成功時,盤面更新前
    previous_state = (board, side_to_move, hands, check_status, checkmate_status, game_status)
    board, side_to_move, hands, check_status, checkmate_status, game_status = current_state#着手前
    current_state = (new_board, new_side_to_move, new_hands, new_check_status, new_checkmate_status, new_game_status)#引数名は後で確認
    version += 1
