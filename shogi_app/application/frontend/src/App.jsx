import { useEffect, useRef, useState } from "react";
import "./App.css";
import { fetchGameState, fetchLegalMoves, postMove, resetGame } from "./api/gameApi";
import { EMPTY, initialBoard } from "./constants/gameConstants";
import { computeDropTargets, getPieceImageSrc, handCounts, sideLabel } from "./utils/gameHelpers";

function App() {
  const boardRef = useRef(null);
  const [board, setBoard] = useState(initialBoard);
  const [sideToMove, setSideToMove] = useState("upper");
  const [hands, setHands] = useState({ upper: [], lower: [] });
  const [checkStatus, setCheckStatus] = useState({ upper: false, lower: false });
  const [checkmateStatus, setCheckmateStatus] = useState({ upper: false, lower: false });
  const [gameStatus, setGameStatus] = useState({ state: "ongoing", winner: null, reason: null });
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [legalMoves, setLegalMoves] = useState([]);
  const [pendingPromotion, setPendingPromotion] = useState(null);
  const [selectedHandPiece, setSelectedHandPiece] = useState(null);
  const [dropTargets, setDropTargets] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");

  // サーバー状態をまとめて画面へ反映する。
  const applyServerState = (data) => {
    if (!data) return;
    if (data.board) setBoard(data.board);
    if (data.side_to_move) setSideToMove(data.side_to_move);
    if (data.hands) setHands(data.hands);
    if (data.check_status) setCheckStatus(data.check_status);
    if (data.checkmate_status) setCheckmateStatus(data.checkmate_status);
    if (data.game_status) setGameStatus(data.game_status);
  };

  // 選択中の盤上駒情報を初期化する。
  const clearSelection = () => {
    setSelectedPosition(null);
    setLegalMoves([]);
  };

  // 駒を画像または文字として描画する。
  const renderPiece = (piece) => {
    const src = getPieceImageSrc(piece);
    if (!src) return piece;
    return (
      <img
        className={`piece-image ${piece === piece.toLowerCase() ? "piece-lower" : ""}`}
        src={src}
        alt={piece}
      />
    );
  };

  // 持ち駒一覧を操作可能なボタン群で描画する。
  const renderHandPieces = (side) => {
    const entries = Object.entries(handCounts(hands[side] || []));
    if (entries.length === 0) return "なし";
    return entries.map(([piece, count]) => (
      <button
        key={`${side}-${piece}`}
        type="button"
        className={`hand-piece-chip ${selectedHandPiece === piece ? "active-hand-piece" : ""}`}
        disabled={gameStatus.state === "ended" || side !== sideToMove}
        onClick={() => {
          if (selectedHandPiece === piece) {
            setSelectedHandPiece(null);
            setDropTargets([]);
            return;
          }
          setSelectedHandPiece(piece);
          setDropTargets(computeDropTargets(board, sideToMove, piece));
          clearSelection();
        }}
      >
        {renderPiece(piece)} x{count}
      </button>
    ));
  };

  // 通常着手をサーバーへ送信して結果を反映する。
  const executeMove = async (from, piece, row, col, chosen) => {
    setErrorMessage("");
    const result = await postMove({
      board,
      from_pos: [from.row, from.col],
      to_pos: [row, col],
      move_type: chosen.type,
      piece,
      promote: Boolean(chosen.promote),
    });
    if (!result.ok) {
      setErrorMessage(result.data.error || "着手に失敗しました。");
      if (result.data.game_status) setGameStatus(result.data.game_status);
      clearSelection();
      setPendingPromotion(null);
      return;
    }

    applyServerState(result.data);
    setPendingPromotion(null);
    clearSelection();
  };

  // 成り選択結果を着手処理へ変換する。
  const choosePromotion = async (wantsPromote) => {
    if (!pendingPromotion) return;
    const { candidates, from, piece, row, col } = pendingPromotion;
    const found = candidates.find((move) => move.promote === wantsPromote);
    const chosen = found || candidates[0];
    await executeMove(from, piece, row, col, chosen);
  };

  // 盤外クリック時に駒打ち選択を解除する。
  useEffect(() => {
    const handleOutsideBoardClick = (event) => {
      if (!selectedHandPiece) return;
      if (boardRef.current && boardRef.current.contains(event.target)) return;
      setSelectedHandPiece(null);
      setDropTargets([]);
    };

    document.addEventListener("mousedown", handleOutsideBoardClick);
    return () => {
      document.removeEventListener("mousedown", handleOutsideBoardClick);
    };
  }, [selectedHandPiece]);

  // 初回表示で対局状態を読み込む。
  useEffect(() => {
    const loadState = async () => {
      const result = await fetchGameState();
      if (!result.ok) return;
      applyServerState(result.data);
    };
    loadState();
  }, []);

  // 盤面状態を初期化する。
  const handleReset = async () => {
    setErrorMessage("");
    const result = await resetGame();
    if (!result.ok) {
      setErrorMessage(result.data.error || "リセットに失敗しました。");
      return;
    }
    applyServerState(result.data);
    setSelectedHandPiece(null);
    setDropTargets([]);
    setPendingPromotion(null);
    clearSelection();
  };

  // マスクリック時の選択・着手・駒打ちを制御する。
  const handleClick = async (row, col) => {
    if (gameStatus.state === "ended" || pendingPromotion) return;

    const cell = board[row][col];

    if (selectedHandPiece) {
      if (!dropTargets.includes(`${row},${col}`)) {
        setSelectedHandPiece(null);
        setDropTargets([]);
        return;
      }
      if (cell !== EMPTY) return;

      setErrorMessage("");
      const dropResult = await postMove({
        board,
        move_type: "drop",
        drop_piece: selectedHandPiece,
        to_pos: [row, col],
      });
      if (!dropResult.ok) {
        setErrorMessage(dropResult.data.error || "駒打ちに失敗しました。");
        if (dropResult.data.game_status) setGameStatus(dropResult.data.game_status);
        setSelectedHandPiece(null);
        setDropTargets([]);
        clearSelection();
        return;
      }

      applyServerState(dropResult.data);
      setSelectedHandPiece(null);
      setDropTargets([]);
      clearSelection();
      return;
    }

    if (!selectedPosition && cell !== EMPTY) {
      const isOwnPiece =
        (sideToMove === "upper" && cell === cell.toUpperCase()) ||
        (sideToMove === "lower" && cell === cell.toLowerCase());
      if (!isOwnPiece) return;

      setSelectedPosition({ row, col });
      const legalResult = await fetchLegalMoves({ board, row, col, piece: cell });
      if (!legalResult.ok) {
        setErrorMessage(legalResult.data.error || "合法手の取得に失敗しました。");
        setSelectedPosition(null);
        setLegalMoves([]);
        return;
      }

      setLegalMoves(legalResult.data.legal_moves || []);
      return;
    }

    if (selectedPosition) {
      const from = selectedPosition;
      const piece = board[from.row][from.col];
      const candidates = legalMoves.filter((move) => move.row === row && move.col === col);

      if (candidates.length === 0) {
        clearSelection();
        return;
      }
      if (candidates.length > 1) {
        setPendingPromotion({ from, piece, row, col, candidates });
        return;
      }
      await executeMove(from, piece, row, col, candidates[0]);
    }
  };

  return (
    <div className="App">
      <h1>将棋</h1>
      <div className="status-strip">
        <p className="status-line">手番: {sideLabel(sideToMove)}</p>
        <button type="button" className="reset-btn" onClick={handleReset}>
          リセット
        </button>
      </div>
      {gameStatus.state === "ended" && (
        <p className="game-end-text">対局終了: 勝者 {sideLabel(gameStatus.winner)}</p>
      )}
      {checkStatus.upper && <p className="status-line event-line">先手が王手されています</p>}
      {checkStatus.lower && <p className="status-line event-line">後手が王手されています</p>}
      {checkmateStatus.upper && <p className="status-line event-line checkmate-line">先手が詰みです</p>}
      {checkmateStatus.lower && <p className="status-line event-line checkmate-line">後手が詰みです</p>}
      {errorMessage && <p className="error-text">{errorMessage}</p>}
      {pendingPromotion && (
        <div className="promotion-overlay">
          <div className="promotion-choice">
            <span>成りますか？</span>
            <button type="button" onClick={() => choosePromotion(true)} disabled={gameStatus.state === "ended"}>
              はい
            </button>
            <button type="button" onClick={() => choosePromotion(false)} disabled={gameStatus.state === "ended"}>
              いいえ
            </button>
          </div>
        </div>
      )}
      <div className="board-area">
        <div className="hands-row hands-lower">
          <span className="hands-label">後手持ち駒</span>
          <div className="hands-content">{renderHandPieces("lower")}</div>
        </div>
        <div ref={boardRef} className={`board ${gameStatus.state === "ended" ? "board-ended" : ""}`}>
          {board.map((rowArray, rowIndex) => (
            <div key={rowIndex} className="row">
              {rowArray.map((cell, colIndex) => {
                const isLegal = legalMoves.some((move) => move.row === rowIndex && move.col === colIndex);
                const isDropTarget = Boolean(selectedHandPiece) && dropTargets.includes(`${rowIndex},${colIndex}`);
                const isSelected =
                  selectedPosition &&
                  selectedPosition.row === rowIndex &&
                  selectedPosition.col === colIndex;

                return (
                  <div
                    key={colIndex}
                    className={`cell ${isLegal ? "highlight" : ""} ${isSelected ? "selected" : ""} ${
                      isDropTarget ? "drop-target" : ""
                    }`}
                    onClick={() => handleClick(rowIndex, colIndex)}
                  >
                    {cell === EMPTY ? "" : renderPiece(cell)}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div className="hands-row hands-upper">
          <span className="hands-label">先手持ち駒</span>
          <div className="hands-content">{renderHandPieces("upper")}</div>
        </div>
      </div>
    </div>
  );
}

export default App;
