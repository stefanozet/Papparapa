// Renderer for "choice" activities (sequence + odd-one-out + pairs).
// Handles live play, keyboard control and the wordless animated tutorial.
//
// Input: tap an option to answer immediately, or use the number keys (1..4) to
// select one and Space/Enter to confirm. Each option carries its number badge.
import { sfx } from "../sound.js";
import { burstFrom, clear, el, popFeedback, wait } from "../ui.js";

// Options are usually one emoji, but the counting game shows *groups* (🐟🐟🐟);
// those get a "multi" class so the CSS can shrink and wrap the symbols.
const SEGMENTER = typeof Intl !== "undefined" && Intl.Segmenter
  ? new Intl.Segmenter(undefined, { granularity: "grapheme" })
  : null;
const glyphCount = (t) => (SEGMENTER ? [...SEGMENTER.segment(t)] : [...t]).length;

function buildBoard(stage, activity) {
  clear(stage);
  const wrap = el("div", "activity choice");

  if (activity.stimulus && activity.stimulus.length) {
    const s = el("div", "stimulus");
    activity.stimulus.forEach((t) => s.appendChild(el("span", "token", { textContent: t })));
    wrap.appendChild(s);
  }

  const opts = el("div", "options");
  activity.options.forEach((t, i) => {
    const btn = el("button", glyphCount(t) > 1 ? "option multi" : "option", { type: "button" });
    btn.append(
      el("span", "num", { textContent: String(i + 1) }),
      el("span", "glyph", { textContent: t })
    );
    opts.appendChild(btn);
  });
  wrap.appendChild(opts);
  stage.appendChild(wrap);
  return opts;
}

export function renderActivity(stage, activity, ctx) {
  const opts = buildBoard(stage, activity);
  const buttons = Array.from(opts.children);
  let locked = false;
  let selected = -1;

  const answer = async (i) => {
    if (locked) return;
    locked = true;
    if (i === activity.answer) {
      buttons[i].classList.add("correct");
      sfx.correct();
      burstFrom(buttons[i]);
      popFeedback(stage, "⭐");
      await wait(450);
      ctx.solved(i);
    } else {
      buttons[i].classList.add("wrong");
      buttons[activity.answer].classList.add("correct");
      sfx.wrong();
      await wait(700);
      ctx.fail(i);
    }
  };

  const select = (i) => {
    if (locked || i < 0 || i >= buttons.length) return;
    selected = i;
    sfx.tap();
    buttons.forEach((b, k) => b.classList.toggle("selected", k === i));
  };

  buttons.forEach((btn, i) => btn.addEventListener("click", () => answer(i)));

  const onKey = (e) => {
    if (locked) return;
    if (e.key >= "1" && e.key <= "9") {
      const i = Number(e.key) - 1;
      if (i < buttons.length) { e.preventDefault(); select(i); }
    } else if (e.key === "Enter" || e.key === " " || e.code === "Space") {
      e.preventDefault();
      if (selected >= 0) answer(selected);
    }
  };
  window.addEventListener("keydown", onKey);
  ctx.onCleanup(() => window.removeEventListener("keydown", onKey));
}

export async function renderTutorial(stage, activity, onDone) {
  const opts = buildBoard(stage, activity);
  const good = opts.children[activity.answer];
  const hand = el("div", "hand", { textContent: "👆" });
  stage.appendChild(hand);

  const pointOnce = async () => {
    const gr = good.getBoundingClientRect();
    const sr = stage.getBoundingClientRect();
    hand.style.left = gr.left - sr.left + gr.width / 2 - 12 + "px";
    hand.style.top = gr.top - sr.top + gr.height / 2 + "px";
    good.classList.add("hint");
    sfx.tap();
    await wait(750);
    good.classList.remove("hint");
    await wait(450);
  };

  await wait(500);
  await pointOnce();
  await pointOnce();
  await wait(300);
  onDone();
}
