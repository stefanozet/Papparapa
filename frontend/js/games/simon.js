// Renderer for "simon" activities: the pads light up one after another (👀),
// then the child replays the sequence by tapping the same pads in the same
// order (👆). A wrong tap costs a heart. The taps are sent to the server,
// which checks them against the sequence.
//
// Input: tap a pad, or press its number key (1..4) — no confirm needed, each
// press plays immediately, like a real drum.
import { sfx } from "../sound.js";
import { burstFrom, clear, el, popFeedback, wait } from "../ui.js";

function buildBoard(stage, activity) {
  clear(stage);
  const wrap = el("div", "activity choice");
  const cue = el("div", "peek-eyes", { textContent: "👀" });
  const opts = el("div", "options");
  const pads = activity.pads.map((glyph, i) => {
    const btn = el("button", "option", { type: "button" });
    btn.append(
      el("span", "num", { textContent: String(i + 1) }),
      el("span", "glyph", { textContent: glyph })
    );
    opts.appendChild(btn);
    return btn;
  });
  wrap.append(cue, opts);
  stage.appendChild(wrap);
  return { cue, pads };
}

/** Flash the sequence on the pads, then flip the cue from "watch" to "play". */
async function playback(cue, pads, sequence) {
  cue.textContent = "👀";
  sfx.peek();
  await wait(600);
  for (const i of sequence) {
    pads[i].classList.add("lit");
    sfx.pad(i);
    await wait(520);
    pads[i].classList.remove("lit");
    await wait(220);
  }
  cue.textContent = "👆";
}

export function renderActivity(stage, activity, ctx) {
  const { cue, pads } = buildBoard(stage, activity);
  const taps = [];
  let accepting = false;
  let alive = true;

  const press = async (i) => {
    if (!accepting) return;
    taps.push(i);
    const step = taps.length - 1;
    if (i !== activity.sequence[step]) {
      accepting = false;
      pads[i].classList.add("wrong");
      pads[activity.sequence[step]].classList.add("hint");   // show what was next
      sfx.wrong();
      await wait(700);
      ctx.fail(taps);
      return;
    }
    pads[i].classList.add("lit");
    sfx.pad(i);
    setTimeout(() => pads[i].classList.remove("lit"), 260);
    if (taps.length === activity.sequence.length) {
      accepting = false;
      sfx.correct();
      burstFrom(pads[i]);
      popFeedback(stage, "⭐");
      await wait(450);
      ctx.solved(taps);
    }
  };

  pads.forEach((pad, i) => pad.addEventListener("click", () => press(i)));

  const onKey = (e) => {
    if (e.key >= "1" && e.key <= "9") {
      const i = Number(e.key) - 1;
      if (i < pads.length) { e.preventDefault(); press(i); }
    }
  };
  window.addEventListener("keydown", onKey);
  // A single cleanup covers both: the timer may fire mid-playback (alive) or
  // while waiting for taps (keyboard listener).
  ctx.onCleanup(() => { alive = false; window.removeEventListener("keydown", onKey); });

  playback(cue, pads, activity.sequence).then(() => { if (alive) accepting = true; });
}

export async function renderTutorial(stage, activity, onDone) {
  const { cue, pads } = buildBoard(stage, activity);
  await playback(cue, pads, activity.sequence);

  // The hand replays the sequence, pad by pad.
  const hand = el("div", "hand", { textContent: "👆" });
  stage.appendChild(hand);
  await wait(400);
  for (const i of activity.sequence) {
    const pr = pads[i].getBoundingClientRect();
    const sr = stage.getBoundingClientRect();
    hand.style.left = pr.left - sr.left + pr.width / 2 - 12 + "px";
    hand.style.top = pr.top - sr.top + pr.height / 2 + "px";
    pads[i].classList.add("lit");
    sfx.pad(i);
    await wait(600);
    pads[i].classList.remove("lit");
    await wait(250);
  }
  hand.remove();
  sfx.correct();
  popFeedback(stage, "⭐");
  await wait(600);
  onDone();
}
