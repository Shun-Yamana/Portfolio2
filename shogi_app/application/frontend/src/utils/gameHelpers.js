import { EMPTY, PIECE_IMAGE_MAP } from "../constants/gameConstants";

// 手番表示の文言を返す。
export const sideLabel = (side) => {
  if (side === "upper") return "先手";
  if (side === "lower") return "後手";
  return "なし";
};

// 持ち駒配列を駒種ごとの個数に集計する。
export const handCounts = (arr) => {
  const counts = {};
  for (const piece of arr || []) {
    counts[piece] = (counts[piece] || 0) + 1;
  }
  return counts;
};

// 駒文字列から画像URLを返す。
export const getPieceImageSrc = (piece) => {
  if (!piece || piece === EMPTY) return null;
  if (piece === "ou") return "/pieces/gyoku.png";
  return PIECE_IMAGE_MAP[piece.toUpperCase()] || null;
};

// 駒打ち可能なマスを列挙する。
export const computeDropTargets = (board, sideToMove, piece) => {
  if (!piece) return [];

  const handPiece = sideToMove === "upper" ? piece.toUpperCase() : piece.toLowerCase();
  const base = handPiece.toUpperCase();
  const targets = [];

  for (let row = 0; row < 9; row += 1) {
    for (let col = 0; col < 9; col += 1) {
      if (board[row][col] !== EMPTY) continue;

      if (base === "FU") {
        const ownFu = sideToMove === "upper" ? "FU" : "fu";
        let hasNifu = false;
        for (let checkRow = 0; checkRow < 9; checkRow += 1) {
          if (board[checkRow][col] === ownFu) {
            hasNifu = true;
            break;
          }
        }
        if (hasNifu) continue;
      }

      if (base === "FU" || base === "KY") {
        if (sideToMove === "upper" && row === 0) continue;
        if (sideToMove === "lower" && row === 8) continue;
      }
      if (base === "KE") {
        if (sideToMove === "upper" && row <= 1) continue;
        if (sideToMove === "lower" && row >= 7) continue;
      }

      targets.push(`${row},${col}`);
    }
  }

  return targets;
};
