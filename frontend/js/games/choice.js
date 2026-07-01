// Renderer for "choice" activities (sequence + odd-one-out).
// Handles both live play and the wordless animated tutorial.
import { clear, el, popFeedback, wait } from "../ui.js";

function buildBoard(stage, activity) {
  clear(stage);
  const wrap = el("div", "activity choice");

  if (activity.stimulus && activity.stimulus.length) {
    const s = el("div", "stimulus");
    activity.stimulus.forEach((t) => s.appendChild(el("span", "token", { textContent: t })));
    wrap.appendChild(s);
  }

  const opts = el("div", "options");
  activity.options.forEach((t) =>
    opts.appendChild(el("button", "option", { textContent: t, type: "button" }))
  );
  wrap.appendChild(opts);
  stage.appendChild(wrap);
  return opts;
}

export function renderActivity(stage, activity, ctx) {
  const opts = buildBoard(stage, activity);
  let locked = false;

  Array.from(opts.children).forEach((btn, i) => {
    btn.addEventListener("click", async () => {
      if (locked) return;
      locked = true;
      if (i === activity.answer) {
        btn.classList.add("correct");
        popFeedback(stage, "⭐");
        await wait(450);
        ctx.solved(i);
      } else {
        btn.classList.add("wrong");
        opts.children[activity.answer].classList.add("correct");
        await wait(700);
        ctx.fail(i);
      }
    });
  });
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
