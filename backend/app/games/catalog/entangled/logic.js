// Pure game logic for Entangled — the exact mirror of game.py in this folder
// (board topology, tile rotation, path stepping, fibonacci scoring). Keep the
// two in sync. No imports: the renderer uses it in the browser and it can be
// exercised standalone (e.g. with node) to check parity with the backend.

export const RADIUS = 3;
export const HAND = 2;
export const FIB_CAP = 40;
// Axial directions, clockwise from East; side i of a tile faces DIRS[i].
export const DIRS = [[1, 0], [0, 1], [-1, 1], [-1, 0], [0, -1], [1, -1]];

/** Fibonacci with fib(1) = fib(2) = 1; fib(0) = 0. */
export function fib(n) {
  n = Math.max(0, Math.min(n, FIB_CAP));
  let a = 0, b = 1;
  for (let i = 0; i < n; i++) [a, b] = [b, a + b];
  return a;
}

export function inBoard(q, r) {
  return Math.max(Math.abs(q), Math.abs(r), Math.abs(q + r)) <= RADIUS;
}

/** All 37 board cells as [q, r] pairs. */
export function cells() {
  const out = [];
  for (let q = -RADIUS; q <= RADIUS; q++) {
    for (let r = -RADIUS; r <= RADIUS; r++) if (inBoard(q, r)) out.push([q, r]);
  }
  return out;
}

/** The tile's links after `rot` clockwise 60° steps. */
export function rotated(links, rot) {
  const out = new Array(12);
  for (let a = 0; a < 12; a++) out[(a + 2 * rot) % 12] = (links[a] + 2 * rot) % 12;
  return out;
}

/** The neighbour's entry point matching exit point `p`. */
export function mirror(p) {
  const side = p >> 1, offset = p & 1;
  return 2 * ((side + 3) % 6) + (1 - offset);
}

/** Cross the edge at exit point `p`: [[q, r] of the neighbour, entry point]. */
export function step([q, r], p) {
  const [dq, dr] = DIRS[p >> 1];
  return [[q + dq, r + dr], mirror(p)];
}

/** Canonical id of a tile line: cell key + the line's lowest point. */
export const segId = (cellKey, a, b) => cellKey + ":" + Math.min(a, b);

/**
 * Follow the lines from `entry` of `cell` through the placed tiles.
 * `tiles` maps "q,r" cell keys to effective (already rotated) links.
 * Returns { segments: [[cellKey, entryPoint, exitPoint], ...], ended }
 * with ended one of "open" (an empty cell), "border" or "center".
 */
export function walkFrom(tiles, cell, entry, cap = 500) {
  const segments = [];
  let ended = "open";
  for (let i = 0; i < cap; i++) {
    const links = tiles.get(cell.join(","));
    if (!links) break;
    const exit = links[entry];
    segments.push([cell.join(","), entry, exit]);
    [cell, entry] = step(cell, exit);
    if (cell[0] === 0 && cell[1] === 0) { ended = "center"; break; }
    if (!inBoard(cell[0], cell[1])) { ended = "border"; break; }
  }
  return { segments, ended };
}

/**
 * The "dead branches" of the board: every untraversed line belonging to a
 * chain that terminates on the outer border or on the centre tile — the
 * path entering such a chain would end the game. `traversed` holds the
 * segId of the lines already walked by the live path (they form their own
 * chain and are never dead). Returns [[cellKey, a, b], ...].
 */
export function deadSegments(tiles, traversed = new Set()) {
  const dead = [];
  const seen = new Set();
  for (const [cellKey, links] of tiles) {
    for (let a = 0; a < 12; a++) {
      const b = links[a];
      if (a > b) continue;
      const id = segId(cellKey, a, b);
      if (seen.has(id) || traversed.has(id)) continue;
      // Explore the whole chain this line belongs to, out of both ends.
      const chain = [[cellKey, a, b]];
      const chainIds = new Set([id]);
      let isDead = false;
      for (const end of [a, b]) {
        let cell = cellKey.split(",").map(Number);
        let point = end;
        for (let guard = 0; guard < 500; guard++) {
          const [ncell, nentry] = step(cell, point);
          if (ncell[0] === 0 && ncell[1] === 0) { isDead = true; break; }
          if (!inBoard(ncell[0], ncell[1])) { isDead = true; break; }
          const nkey = ncell.join(",");
          const nlinks = tiles.get(nkey);
          if (!nlinks) break;                     // open end: still alive
          const nb = nlinks[nentry];
          const nid = segId(nkey, nentry, nb);
          if (chainIds.has(nid) || traversed.has(nid)) break;
          chainIds.add(nid);
          chain.push([nkey, nentry, nb]);
          cell = ncell;
          point = nb;
        }
      }
      chainIds.forEach((cid) => seen.add(cid));
      if (isDead) dead.push(...chain);
    }
  }
  return dead;
}

/**
 * Replay a whole game (same semantics as game.py's simulate): returns
 * { score, gains, moves_played, ended } with ended one of "border",
 * "center" or "pending". Malformed/impossible moves stop the replay.
 */
export function simulate(start, draws, moves) {
  const tiles = new Map();
  const hand = [draws[0], draws[1]];
  let nextDraw = HAND;
  let [cell, entry] = step([0, 0], start);
  let ended = null;
  const gains = [];
  for (const move of moves) {
    if (ended) break;
    const choice = move && move.choice;
    const rot = (move && move.rotation) || 0;
    if ((choice !== 0 && choice !== 1) || rot < 0 || rot > 5 || !hand[choice]) break;
    tiles.set(cell.join(","), rotated(hand[choice], rot));
    hand[choice] = nextDraw < draws.length ? draws[nextDraw] : null;
    nextDraw += 1;
    let crossings = 0;
    while (!ended && tiles.has(cell.join(","))) {
      const exit = tiles.get(cell.join(","))[entry];
      crossings += 1;
      [cell, entry] = step(cell, exit);
      if (cell[0] === 0 && cell[1] === 0) ended = "center";
      else if (!inBoard(cell[0], cell[1])) ended = "border";
    }
    gains.push(fib(crossings));
  }
  return {
    score: gains.reduce((s, g) => s + g, 0),
    gains,
    moves_played: gains.length,
    ended: ended || "pending",
  };
}
