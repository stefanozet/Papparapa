// Generic game engine: drives micro-activities under a time limit, tracks
// lives (hearts) and score, and reports the final result. It is game-agnostic
// — each game supplies a renderer module (see games/*.js).
import * as choice from "./games/choice.js";
import * as maze from "./games/maze.js";
import { el, wait } from "./ui.js";

const MODULES = { sequence: choice, odd: choice, maze };
export function moduleFor(key) { return MODULES[key]; }

const POINTS = 10;

export class GameEngine {
  constructor({ meta, activities, stage, hud }) {
    this.meta = meta;
    this.activities = activities;
    this.stage = stage;
    this.hud = hud;
    this.module = moduleFor(meta.key);
    this.maxErrors = meta.max_errors;
    this.score = 0;
    this.correct = 0;
    this.errors = 0;
    this.results = [];
    this.stopped = false;
    this.reason = null;
    this.remaining = meta.duration_seconds;
    this._force = null;
  }

  /** Play the whole game; resolves with the result summary. */
  async run() {
    this._renderHud();
    this._startTimer();
    for (const activity of this.activities) {
      if (this.stopped) break;
      const over = await this._playActivity(activity);
      if (over) break;
      await wait(220);
    }
    clearInterval(this._timer);
    return {
      score: this.score,
      correct: this.correct,
      errors: this.errors,
      results: this.results,
      reason: this.reason || "completed",
    };
  }

  _playActivity(activity) {
    return new Promise((resolve) => {
      let settled = false;
      const done = (over) => {
        if (settled) return;
        settled = true;
        this._force = null;
        resolve(over);
      };
      this._force = () => done(true);

      const ctx = {
        points: POINTS,
        solved: (answer) => {
          this.score += POINTS;
          this.correct += 1;
          if (answer !== undefined) this.results.push({ id: activity.id, answer });
          this._renderHud();
          done(false);
        },
        fail: (answer) => {
          if (answer !== undefined) this.results.push({ id: activity.id, answer });
          done(this._loseLife());
        },
        loseLife: () => {
          const over = this._loseLife();
          if (over) done(true);
          return over;
        },
      };
      this.module.renderActivity(this.stage, activity, ctx);
    });
  }

  _loseLife() {
    this.errors += 1;
    if (this.errors >= this.maxErrors) this.reason = this.reason || "errors";
    this._renderHud();
    return this.errors >= this.maxErrors;
  }

  _startTimer() {
    this._timer = setInterval(() => {
      this.remaining = Math.max(0, this.remaining - 0.1);
      this.hud.timer(this.remaining / this.meta.duration_seconds);
      if (this.remaining <= 0 && !this.stopped) {
        this.stopped = true;
        this.reason = this.reason || "timeout";
        if (this._force) this._force();
      }
    }, 100);
  }

  _renderHud() {
    this.hud.render({ hearts: this.maxErrors - this.errors, max: this.maxErrors, score: this.score });
  }
}

/** Build the HUD DOM (hearts + score + timer bar) and return a controller. */
export function buildHud(container) {
  const hud = el("div", "hud");
  const hearts = el("div", "hearts");
  const score = el("div", "score");
  hud.append(hearts, score);
  const track = el("div", "timer-track");
  const bar = el("div", "timer-bar");
  track.appendChild(bar);
  container.append(hud, track);

  return {
    render({ hearts: h, max, score: s }) {
      hearts.innerHTML = "";
      for (let i = 0; i < max; i++) {
        const heart = el("span", i < h ? "" : "lost", { textContent: "❤️" });
        hearts.appendChild(heart);
      }
      score.textContent = "⭐ " + s;
    },
    timer(fraction) {
      bar.style.width = Math.max(0, fraction * 100) + "%";
      bar.style.background = fraction < 0.25 ? "var(--orange)" : "var(--accent)";
    },
  };
}
