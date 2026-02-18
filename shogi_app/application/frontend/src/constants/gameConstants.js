export const EMPTY = "EMPTY";

export const PIECE_IMAGE_MAP = {
  OU: "/pieces/ou.png",
  HI: "/pieces/hi.png",
  RY: "/pieces/ry.png",
  KA: "/pieces/ka.png",
  UM: "/pieces/um.png",
  KI: "/pieces/ki.png",
  GI: "/pieces/gi.png",
  NG: "/pieces/ng.png",
  KE: "/pieces/ke.png",
  NK: "/pieces/nk.png",
  KY: "/pieces/ky.png",
  NY: "/pieces/ny.png",
  FU: "/pieces/fu.png",
  TO: "/pieces/to.png",
};

export const initialBoard = [
  ["ky", "ke", "gi", "ki", "ou", "ki", "gi", "ke", "ky"],
  [EMPTY, "hi", EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, "ka", EMPTY],
  Array(9).fill("fu"),
  Array(9).fill(EMPTY),
  Array(9).fill(EMPTY),
  Array(9).fill(EMPTY),
  Array(9).fill("FU"),
  [EMPTY, "KA", EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, "HI", EMPTY],
  ["KY", "KE", "GI", "KI", "OU", "KI", "GI", "KE", "KY"],
];
