// Renderer for "memory" activities: the items to remember flash on screen for
// activity.peek_ms, get covered by ❓, then the child picks the one that was
// there. After the peek the interaction is exactly a choice, so this module
// masks the stimulus and delegates play and tutorial to the choice renderer.
import { sfx } from "../sound.js";
import { clear, el, wait } from "../ui.js";
import * as choice from "./choice.js";

const masked = (activity) => ({
  ...activity,
  stimulus: activity.stimulus.map(() => "❓"),
});

async function peek(stage, activity) {
  clear(stage);
  const wrap = el("div", "activity choice");
  const s = el("div", "stimulus");
  activity.stimulus.forEach((t) => s.appendChild(el("span", "token", { textContent: t })));
  wrap.append(s, el("div", "peek-eyes", { textContent: "👀" }));
  stage.appendChild(wrap);
  sfx.peek();
  await wait(activity.peek_ms || 2000);
}

export function renderActivity(stage, activity, ctx) {
  let alive = true;
  ctx.onCleanup(() => { alive = false; });   // the game timer may fire mid-peek
  peek(stage, activity).then(() => {
    if (alive) choice.renderActivity(stage, masked(activity), ctx);
  });
}

export async function renderTutorial(stage, activity, onDone) {
  await peek(stage, activity);
  await choice.renderTutorial(stage, masked(activity), onDone);
}
