// Renderer for "entangled" activities: a hexagonal board where the player
// grows a path by placing random tiles. Bundled with the game (served from
// /api/games/entangled/renderer.js), so shared helpers are imported with
// absolute paths and the game rules come from ./logic.js (the exact mirror
// of the backend's game.py — the server replays the moves authoritatively).
//
// Input: tap a tile to pick it (tap it again to rotate), ↻ rotates, ✓ — or a
// tap on the previewed tile in the target cell — places it. Keyboard: 1/2
// pick a tile, ←/→ rotate, Space/Enter places.
//
// Reading the board: gold is the path already walked, solid green is what
// the path would walk if the picked tile were placed as previewed, and dark
// lines are dead branches — chains that end on the border or on the black
// tile, where the path would die (shown on the previewed tile too).
import { sfx } from "/js/sound.js";
import { celebrate, clear, el, wait } from "/js/ui.js";
import { deadSegments, fib, inBoard, cells, rotated, segId, step, walkFrom } from "./logic.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const S = 10;                        // hex circumradius in viewBox units
const GOLD = "#f6b93b";              // the path (stands out on any theme)
const LINE = "#8b90b3";              // idle tile lines
const DEAD = "#454965";              // dead branches (end on border/centre)
const GHOST_LINE = "#d0d3e4";        // previewed tile's neutral lines (washed
                                     // out by color, not by opacity, so its
                                     // dead branches stay the same full DEAD)
const PREVIEW = "#27ae60";           // what the path would walk if placed
const key = ([q, r]) => q + "," + r;

// --- geometry: pointy-top hexes, side i faces DIRS[i] (clockwise from E) --- //
const cellCenter = ([q, r]) => [S * Math.sqrt(3) * (q + r / 2), S * 1.5 * r];

function corner(cx, cy, k, s = S) {
  const a = (Math.PI / 180) * (-90 + 60 * k);
  return [cx + s * Math.cos(a), cy + s * Math.sin(a)];
}

/** Position of tile point p (side p>>1, first/second along the edge). */
function pointAt(cx, cy, p, s = S) {
  const [ax, ay] = corner(cx, cy, (p >> 1) + 1, s);
  const [bx, by] = corner(cx, cy, (p >> 1) + 2, s);
  const t = p & 1 ? 2 / 3 : 1 / 3;
  return [ax + (bx - ax) * t, ay + (by - ay) * t];
}

function svgEl(tag, attrs = {}) {
  const n = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  return n;
}

const hexPoints = (cx, cy, s = S) =>
  Array.from({ length: 6 }, (_, k) => corner(cx, cy, k, s).map((v) => v.toFixed(2)).join(","))
    .join(" ");

/** Bézier between two tile points, bowed toward the tile centre. */
function curveD(cx, cy, a, b, s = S) {
  const [ax, ay] = pointAt(cx, cy, a, s);
  const [bx, by] = pointAt(cx, cy, b, s);
  const pull = 0.72;
  const c1 = [ax + (cx - ax) * pull, ay + (cy - ay) * pull];
  const c2 = [bx + (cx - bx) * pull, by + (cy - by) * pull];
  const f = (v) => v.toFixed(2);
  return `M ${f(ax)} ${f(ay)} C ${f(c1[0])} ${f(c1[1])}, ${f(c2[0])} ${f(c2[1])}, ${f(bx)} ${f(by)}`;
}

/** Draw a whole tile's 6 lines into `group` around (cx, cy). */
function drawLinks(group, cx, cy, links, s = S, stroke = LINE, width = 1.1) {
  for (let a = 0; a < 12; a++) {
    if (a < links[a]) {
      group.appendChild(svgEl("path", {
        d: curveD(cx, cy, a, links[a], s),
        fill: "none", stroke, "stroke-width": width, "stroke-linecap": "round",
      }));
    }
  }
}

// --------------------------------------------------------------------------- //
// Game construction (shared by live play and the wordless tutorial)
// --------------------------------------------------------------------------- //
function createGame(stage, activity, ctx, demo) {
  const draws = activity.draws;
  const tiles = new Map();                   // "q,r" -> effective links
  const hand = [draws[0], draws[1]];
  const handRot = [0, 0];
  let nextDraw = 2;
  let [cur, entry] = step([0, 0], activity.start);
  let ended = null;
  let selected = 0;
  let busy = false;
  const moves = [];
  const traversed = new Set();      // segIds walked by the path (never dead)

  clear(stage);
  const wrap = el("div");
  wrap.style.cssText =
    "display:flex;flex-direction:column;align-items:center;gap:10px;width:100%;padding:4px 0;";
  const svg = svgEl("svg", { viewBox: "-64 -58 128 116" });
  svg.style.cssText = "width:100%;max-width:420px;height:auto;display:block;";
  wrap.appendChild(svg);

  const gCells = svgEl("g");
  const gTiles = svgEl("g");
  const gDead = svgEl("g");         // dead branches, dark over the idle lines
  const gPath = svgEl("g");
  const gMarkers = svgEl("g");
  svg.append(gCells, gTiles, gDead, gPath, gMarkers);

  // Board cells; the centre tile is black with its golden start stub.
  for (const c of cells()) {
    const [cx, cy] = cellCenter(c);
    const isCenter = c[0] === 0 && c[1] === 0;
    gCells.appendChild(svgEl("polygon", {
      points: hexPoints(cx, cy),
      fill: isCenter ? "#23253a" : "#ffffff",
      stroke: isCenter ? "#23253a" : "#d7d9ea",
      "stroke-width": 0.6,
    }));
  }
  const [sx, sy] = pointAt(0, 0, activity.start);
  gTiles.appendChild(svgEl("path", {
    d: `M 0 0 L ${sx.toFixed(2)} ${sy.toFixed(2)}`,
    stroke: GOLD, "stroke-width": 2, "stroke-linecap": "round", fill: "none",
  }));
  gTiles.appendChild(svgEl("circle", { cx: 0, cy: 0, r: 1.6, fill: GOLD }));

  // Target cell outline + pulsing head marker + ghost preview of the pick
  // (with the would-be path drawn on top in green). The target hexagon also
  // takes the tap that places the previewed tile.
  const target = svgEl("polygon", {
    fill: GOLD, "fill-opacity": 0.12, stroke: GOLD,
    "stroke-width": 0.9, "stroke-dasharray": "3 2",
  });
  const ghost = svgEl("g", { "pointer-events": "none" });
  const preview = svgEl("g", { "pointer-events": "none" });
  const head = svgEl("circle", { r: 2, fill: GOLD, "pointer-events": "none" });
  const pulse = svgEl("animate", {
    attributeName: "r", values: "1.5;2.6;1.5", dur: "1s", repeatCount: "indefinite",
  });
  head.appendChild(pulse);
  gMarkers.append(target, ghost, preview, head);

  // Hand: two tiles, rotate and confirm.
  const controls = el("div");
  controls.style.cssText =
    "display:flex;align-items:center;justify-content:center;gap:14px;" +
    (demo ? "pointer-events:none;" : "");
  const btnBase =
    "height:72px;border-radius:16px;border:3px solid transparent;background:#fff;" +
    "box-shadow:0 3px 10px rgba(0,0,0,.12);cursor:pointer;padding:0;";
  const slots = [0, 1].map(() => {
    const b = el("button", null, { type: "button" });
    b.style.cssText = btnBase + "width:72px;padding:3px;";
    const ms = svgEl("svg", { viewBox: "-12.5 -12.5 25 25" });
    ms.style.cssText = "width:100%;height:100%;display:block;";
    b.appendChild(ms);
    return b;
  });
  const rotBtn = el("button", null, { type: "button", textContent: "↻" });
  rotBtn.style.cssText = btnBase + "width:56px;font-size:1.7rem;border-radius:50%;";
  const okBtn = el("button", null, { type: "button", textContent: "✓" });
  okBtn.style.cssText = btnBase +
    "width:64px;font-size:1.9rem;border-radius:50%;background:var(--accent);color:#fff;";
  controls.append(slots[0], slots[1], rotBtn, okBtn);
  wrap.appendChild(controls);
  stage.appendChild(wrap);

  const renderHand = () => {
    slots.forEach((btn, i) => {
      const ms = btn.firstChild;
      ms.innerHTML = "";
      btn.style.borderColor = i === selected && hand[i] ? "var(--accent)" : "transparent";
      btn.style.opacity = hand[i] ? "1" : "0.25";
      if (!hand[i]) return;
      const g = svgEl("g");
      g.style.transition = "transform .18s ease";
      g.style.transform = `rotate(${60 * handRot[i]}deg)`;
      g.appendChild(svgEl("polygon", {
        points: hexPoints(0, 0, 11), fill: "#fbfbfe", stroke: "#d7d9ea", "stroke-width": 0.7,
      }));
      drawLinks(g, 0, 0, hand[i], 11, "#5c6191", 1.2);
      ms.appendChild(g);
    });
  };

  const renderTargets = () => {
    const [cx, cy] = cellCenter(cur);
    target.setAttribute("points", hexPoints(cx, cy));
    const [hx, hy] = pointAt(cx, cy, entry);
    head.setAttribute("cx", hx.toFixed(2));
    head.setAttribute("cy", hy.toFixed(2));
    ghost.innerHTML = "";
    preview.innerHTML = "";
    if (busy || ended || !hand[selected]) return;
    const links = rotated(hand[selected], handRot[selected]);
    const would = new Map(tiles);
    would.set(key(cur), links);
    // The would-be path: what the tile as previewed would make the path
    // walk, chains through existing tiles included — solid green.
    const walked = walkFrom(would, cur, entry).segments;
    // Dead branches of the previewed tile itself show dark already in the
    // ghost (the would-be path is never dead: it is what you would walk).
    const wouldTraversed = new Set(traversed);
    for (const [ck, a, b] of walked) wouldTraversed.add(segId(ck, a, b));
    const ghostDead = deadSegments(would, wouldTraversed)
      .filter(([ck]) => ck === key(cur));
    drawLinks(ghost, cx, cy, links, S, GHOST_LINE);
    // Same rendering as the board's dead branches: full DEAD color on top,
    // so a dying line looks identical previewed or placed.
    for (const [, a, b] of ghostDead) {
      ghost.appendChild(svgEl("path", {
        d: curveD(cx, cy, a, b), fill: "none", stroke: DEAD,
        "stroke-width": 1.4, "stroke-linecap": "round",
      }));
    }
    for (const [ck, a, b] of walked) {
      const [wx, wy] = cellCenter(ck.split(",").map(Number));
      preview.appendChild(svgEl("path", {
        d: curveD(wx, wy, a, b), fill: "none", stroke: PREVIEW,
        "stroke-width": 2, "stroke-linecap": "round",
      }));
    }
  };

  /** Repaint the dead branches: chains that end on the border or centre. */
  const renderDead = () => {
    gDead.innerHTML = "";
    for (const [ck, a, b] of deadSegments(tiles, traversed)) {
      const [dx, dy] = cellCenter(ck.split(",").map(Number));
      gDead.appendChild(svgEl("path", {
        d: curveD(dx, dy, a, b), fill: "none", stroke: DEAD,
        "stroke-width": 1.4, "stroke-linecap": "round",
      }));
    }
  };

  const select = (i) => {
    if (busy || ended || !hand[i]) return;
    if (i === selected && !demo) return rotate();   // tap again = rotate
    selected = i;
    sfx.tap();
    renderHand();
    renderTargets();
  };

  const rotate = (diff = 1) => {
    if (busy || ended) return;
    handRot[selected] = (handRot[selected] + diff + 6) % 6;
    sfx.tap();
    renderHand();
    renderTargets();
  };

  /** Animate one traversed line and return the drawn path element. */
  const drawSegment = (cell, a, b) => {
    const [cx, cy] = cellCenter(cell);
    const p = svgEl("path", {
      d: curveD(cx, cy, a, b), fill: "none", stroke: GOLD,
      "stroke-width": 2.2, "stroke-linecap": "round",
    });
    gPath.appendChild(p);
    const len = p.getTotalLength();
    p.style.strokeDasharray = len;
    p.style.strokeDashoffset = len;
    requestAnimationFrame(() => {
      p.style.transition = "stroke-dashoffset .2s linear";
      p.style.strokeDashoffset = 0;
    });
  };

  const place = async () => {
    if (busy || ended || !hand[selected]) return;
    busy = true;
    ghost.innerHTML = "";
    const rot = handRot[selected];
    moves.push({ choice: selected, rotation: rot });
    const links = rotated(hand[selected], rot);
    tiles.set(key(cur), links);
    const [cx, cy] = cellCenter(cur);
    drawLinks(gTiles, cx, cy, links);
    hand[selected] = nextDraw < draws.length ? draws[nextDraw] : null;
    nextDraw += 1;
    handRot[selected] = 0;
    sfx.tap();
    await wait(160);

    // Follow the path through every tile it reaches (chains included).
    let crossings = 0;
    while (!ended && tiles.has(key(cur))) {
      const exit = tiles.get(key(cur))[entry];
      drawSegment(cur, entry, exit);
      traversed.add(segId(key(cur), entry, exit));
      sfx.pad(crossings % 4);
      crossings += 1;
      [cur, entry] = step(cur, exit);
      if (cur[0] === 0 && cur[1] === 0) ended = "center";
      else if (!inBoard(cur[0], cur[1])) ended = "border";
      else renderTargets();
      await wait(230);
    }
    ctx.addPoints(fib(crossings));
    renderDead();

    if (!ended) {
      busy = false;
      renderHand();
      renderTargets();
      return;
    }
    // The path left the board (or came home): the game is over.
    head.setAttribute("visibility", "hidden");
    target.setAttribute("visibility", "hidden");
    sfx.win();
    celebrate(["🧶", "⭐", "✨"], 18);
    await wait(900);
    ctx.solved({ moves });
  };

  if (!demo) {
    slots.forEach((btn, i) => btn.addEventListener("click", () => select(i)));
    rotBtn.addEventListener("click", () => rotate());
    okBtn.addEventListener("click", () => place());
    // Tapping the previewed tile on the board places it too.
    target.style.cursor = "pointer";
    target.addEventListener("click", () => place());
  }
  renderHand();
  renderTargets();

  return { select, rotate, place, nodes: { slots, rotBtn, okBtn } };
}

// --------------------------------------------------------------------------- //
// Public renderer contract
// --------------------------------------------------------------------------- //
export function renderActivity(stage, activity, ctx) {
  const game = createGame(stage, activity, ctx, false);
  const onKey = (e) => {
    if (e.key === "1" || e.key === "2") { e.preventDefault(); game.select(Number(e.key) - 1); }
    else if (e.key === "ArrowRight") { e.preventDefault(); game.rotate(1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); game.rotate(-1); }
    else if (e.key === "Enter" || e.key === " " || e.code === "Space") {
      e.preventDefault();
      game.place();
    }
  };
  window.addEventListener("keydown", onKey);
  ctx.onCleanup(() => window.removeEventListener("keydown", onKey));
}

export async function renderTutorial(stage, activity, onDone) {
  const stub = { addPoints() {}, solved() {}, loseLife() {}, fail() {}, onCleanup() {} };
  const game = createGame(stage, activity, stub, true);
  const hand = el("div", "hand", { textContent: "👆" });
  stage.appendChild(hand);
  const over = (node) => {
    const r = node.getBoundingClientRect();
    const sr = stage.getBoundingClientRect();
    hand.style.left = r.left - sr.left + r.width / 2 - 12 + "px";
    hand.style.top = r.top - sr.top + r.height / 2 + "px";
  };

  await wait(600);
  over(game.nodes.slots[0]);
  game.select(0);
  await wait(700);
  over(game.nodes.rotBtn);
  game.rotate();
  await wait(550);
  game.rotate();
  await wait(650);
  over(game.nodes.okBtn);
  await wait(400);
  await game.place();
  await wait(400);
  hand.remove();
  onDone();
}
