// Renderer for "memo" activities: a board of face-down cards, each picture
// twice. Tap two cards to turn them over; a match stays up, a mismatch flips
// back and spends one heart of the board's own budget (one per pair, refilled
// on every new board — see activity.max_errors); an empty budget ends the
// game. Clearing the board solves the activity; the result is
// client-reported like the maze.
//
// Input: tap a card, or press its number key (1..9) to flip it.
import { sfx } from "../sound.js";
import { burstFrom, clear, el, popFeedback, wait } from "../ui.js";

const BACK = "❓";

function buildBoard(stage, activity) {
  clear(stage);
  const wrap = el("div", "activity");
  const grid = el("div", "memo-grid");
  grid.style.gridTemplateColumns = `repeat(${Math.ceil(activity.cards.length / 2)}, 1fr)`;

  const cards = activity.cards.map((_, i) => {
    const card = el("button", "memo-card down", { type: "button" });
    card.append(
      el("span", "num", { textContent: String(i + 1) }),
      el("span", "face", { textContent: BACK })
    );
    grid.appendChild(card);
    return card;
  });
  wrap.appendChild(grid);
  stage.appendChild(wrap);

  const show = (i) => {
    cards[i].classList.replace("down", "up");
    cards[i].querySelector(".face").textContent = activity.cards[i];
  };
  const hide = (i) => {
    cards[i].classList.replace("up", "down");
    cards[i].querySelector(".face").textContent = BACK;
  };
  return { cards, show, hide };
}

export function renderActivity(stage, activity, ctx) {
  const { cards, show, hide } = buildBoard(stage, activity);
  const matched = new Set();
  let first = -1;      // the single face-up card, -1 if none
  let busy = false;    // a mismatch is being flipped back

  const flip = async (i) => {
    if (busy || matched.has(i) || i === first) return;
    show(i);
    sfx.flip();
    if (first < 0) { first = i; return; }

    const other = first;
    first = -1;
    if (activity.cards[other] === activity.cards[i]) {
      cards[other].classList.add("matched");
      cards[i].classList.add("matched");
      sfx.match();
      burstFrom(cards[i]);
      matched.add(other);
      matched.add(i);
      if (matched.size === activity.cards.length) {
        sfx.correct();
        popFeedback(stage, "⭐");
        await wait(450);
        ctx.solved({ solved: true });
      }
    } else {
      busy = true;
      cards[other].classList.add("wrong");
      cards[i].classList.add("wrong");
      sfx.miss();
      // The engine ends the activity when the budget runs out: leave the
      // board locked and the wrong pair showing.
      if (ctx.loseLife()) return;
      await wait(650);
      cards[other].classList.remove("wrong");
      cards[i].classList.remove("wrong");
      hide(other);
      hide(i);
      busy = false;
    }
  };

  cards.forEach((card, i) => card.addEventListener("click", () => flip(i)));

  const onKey = (e) => {
    if (e.key >= "1" && e.key <= "9") {
      const i = Number(e.key) - 1;
      if (i < cards.length) { e.preventDefault(); flip(i); }
    }
  };
  window.addEventListener("keydown", onKey);
  ctx.onCleanup(() => window.removeEventListener("keydown", onKey));
}

export async function renderTutorial(stage, activity, onDone) {
  const { cards, show } = buildBoard(stage, activity);

  // Auto-play the solve: reveal each pair in turn and let it stick.
  const byFace = new Map();
  activity.cards.forEach((face, i) => {
    if (!byFace.has(face)) byFace.set(face, []);
    byFace.get(face).push(i);
  });

  await wait(600);
  for (const [a, b] of byFace.values()) {
    show(a);
    sfx.flip();
    await wait(650);
    show(b);
    cards[a].classList.add("matched");
    cards[b].classList.add("matched");
    sfx.match();
    await wait(550);
  }
  sfx.correct();
  popFeedback(stage, "⭐");
  await wait(700);
  onDone();
}
