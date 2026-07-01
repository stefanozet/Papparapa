// Renderer for the maze game ("Il topo e il formaggio").
// Move the mouse 🐭 to the cheese 🧀. Walls cost a life. Works with an
// on-screen d-pad, arrow keys and swipe gestures.
import { clear, el, popFeedback, wait } from "../ui.js";

const MOUSE = "🐭";
const CHEESE = "🧀";

function buildMaze(stage, activity) {
  clear(stage);
  const wrap = el("div", "maze-wrap");
  const grid = activity.grid;
  const rows = grid.length;
  const cols = grid[0].length;

  // Size cells so the whole maze fits comfortably on a phone screen.
  const maxPx = Math.min(320, window.innerWidth - 60);
  const cs = Math.max(18, Math.floor(maxPx / cols));

  const board = el("div", "maze");
  board.style.gridTemplateColumns = `repeat(${cols}, ${cs}px)`;
  board.style.setProperty("--cs", cs + "px");

  const cells = [];
  for (let r = 0; r < rows; r++) {
    cells[r] = [];
    for (let c = 0; c < cols; c++) {
      const isWall = grid[r][c] === "#";
      const isExit = r === activity.exit[0] && c === activity.exit[1];
      const cell = el("div", "cell " + (isWall ? "wall" : isExit ? "exit" : "path"));
      if (isExit) cell.textContent = CHEESE;
      board.appendChild(cell);
      cells[r][c] = cell;
    }
  }
  wrap.appendChild(board);

  const dpad = el("div", "dpad");
  dpad.innerHTML =
    '<button class="up" type="button">⬆️</button>' +
    '<button class="left" type="button">⬅️</button>' +
    '<button class="right" type="button">➡️</button>' +
    '<button class="down" type="button">⬇️</button>';
  wrap.appendChild(dpad);

  stage.appendChild(wrap);
  return { board, cells, dpad, cs };
}

export function renderActivity(stage, activity, ctx) {
  const { board, cells, dpad } = buildMaze(stage, activity);
  let pos = [...activity.start];
  let done = false;

  const draw = () => {
    cells.forEach((row, r) =>
      row.forEach((cell, c) => {
        if (activity.grid[r][c] === "#") return;
        const isExit = r === activity.exit[0] && c === activity.exit[1];
        cell.textContent = r === pos[0] && c === pos[1] ? MOUSE : isExit ? CHEESE : "";
      })
    );
  };
  draw();

  const move = async (dy, dx) => {
    if (done) return;
    const ny = pos[0] + dy;
    const nx = pos[1] + dx;
    const target = activity.grid[ny] && activity.grid[ny][nx];
    if (target === undefined || target === "#") {
      board.classList.add("bump");
      setTimeout(() => board.classList.remove("bump"), 300);
      ctx.loseLife(); // may end the game
      return;
    }
    pos = [ny, nx];
    draw();
    if (ny === activity.exit[0] && nx === activity.exit[1]) {
      done = true;
      popFeedback(stage, "🎉");
      await wait(450);
      ctx.solved({ solved: true });
    }
  };

  // d-pad
  dpad.querySelector(".up").onclick = () => move(-1, 0);
  dpad.querySelector(".down").onclick = () => move(1, 0);
  dpad.querySelector(".left").onclick = () => move(0, -1);
  dpad.querySelector(".right").onclick = () => move(0, 1);

  // keyboard (desktop testing)
  const onKey = (e) => {
    const map = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };
    if (map[e.key]) { e.preventDefault(); move(...map[e.key]); }
  };
  window.addEventListener("keydown", onKey);

  // swipe
  let sx = 0, sy = 0;
  board.addEventListener("touchstart", (e) => {
    sx = e.touches[0].clientX; sy = e.touches[0].clientY;
  }, { passive: true });
  board.addEventListener("touchend", (e) => {
    const dx = e.changedTouches[0].clientX - sx;
    const dy = e.changedTouches[0].clientY - sy;
    if (Math.abs(dx) < 20 && Math.abs(dy) < 20) return;
    if (Math.abs(dx) > Math.abs(dy)) move(0, dx > 0 ? 1 : -1);
    else move(dy > 0 ? 1 : -1, 0);
  }, { passive: true });

  // Clean up the global key listener when the activity ends.
  const origSolved = ctx.solved, origLose = ctx.loseLife;
  const cleanup = () => window.removeEventListener("keydown", onKey);
  ctx.solved = (a) => { cleanup(); return origSolved(a); };
  ctx.loseLife = () => { const over = origLose(); if (over) cleanup(); return over; };
}

// BFS shortest path, used by the tutorial to auto-walk to the cheese.
function solve(grid, start, exit) {
  const rows = grid.length, cols = grid[0].length;
  const key = (r, c) => r * cols + c;
  const prev = new Map();
  const q = [start];
  const seen = new Set([key(...start)]);
  while (q.length) {
    const [r, c] = q.shift();
    if (r === exit[0] && c === exit[1]) break;
    for (const [dr, dc] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nr = r + dr, nc = c + dc;
      if (nr < 0 || nc < 0 || nr >= rows || nc >= cols) continue;
      if (grid[nr][nc] === "#" || seen.has(key(nr, nc))) continue;
      seen.add(key(nr, nc));
      prev.set(key(nr, nc), [r, c]);
      q.push([nr, nc]);
    }
  }
  const path = [];
  let cur = exit;
  while (cur) { path.push(cur); cur = prev.get(key(...cur)); }
  return path.reverse();
}

export async function renderTutorial(stage, activity, onDone) {
  const { cells } = buildMaze(stage, activity);
  const path = solve(activity.grid, activity.start, activity.exit);
  const draw = (pr, pc) =>
    cells.forEach((row, r) =>
      row.forEach((cell, c) => {
        if (activity.grid[r][c] === "#") return;
        const isExit = r === activity.exit[0] && c === activity.exit[1];
        cell.textContent = r === pr && c === pc ? MOUSE : isExit ? CHEESE : "";
      })
    );

  await wait(500);
  for (const [r, c] of path) {
    draw(r, c);
    await wait(420);
  }
  popFeedback(stage, "🎉");
  await wait(700);
  onDone();
}
