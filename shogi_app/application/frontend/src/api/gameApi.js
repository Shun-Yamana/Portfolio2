// JSON APIを共通フォーマットで実行する。
const requestJson = async (url, options = {}) => {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  return { ok: response.ok, status: response.status, data };
};

// 現在の対局状態を取得する。
export const fetchGameState = () => requestJson("/api/state");

// 合法手を取得する。
export const fetchLegalMoves = (payload) =>
  requestJson("/api/legal_moves", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

// 指し手または駒打ちを送信する。
export const postMove = (payload) =>
  requestJson("/api/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

// 対局状態をリセットする。
export const resetGame = () => requestJson("/api/reset", { method: "POST" });
