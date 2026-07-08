// Generic game engine: drives micro-activities either under a time limit or
// up to a fixed quota of quizzes (meta.quiz_count > 0, set server-side in
// config.py), tracks lives (hearts), levels and score, and reports the final
// result. It is game-agnostic — each game supplies a renderer module, loaded
// dynamically by loadRenderer() below.
//
// Levels: activities come in one batch per level (1..10). Points earned at a
// level accumulate; reaching the threshold (see levels.js) jumps to the next
// level's batch, shows a wordless "level up" banner and grants bonus seconds.
// Consecutive correct answers earn Fibonacci streak bonuses on top. The
// server replays the same rules over the submitted results, so the score
// shown here and the authoritative one agree.
import {
  LEVEL_MAX, LEVEL_UP_SECONDS, pointsFor, streakBonus, thresholdFor,
} from "./levels.js";
import { sfx } from "./sound.js";
import { celebrate, clear, el, wait } from "./ui.js";

// A renderer is resolved from the game's meta, no hardcoded list: games that
// bundle their own dynamics are imported from renderer_url (served by the
// backend from the game's catalog folder), the others from the base kind
// module games/<kind>.js. Loaded modules are cached per source.
const RENDERERS = new Map();
export function loadRenderer(meta) {
  const src = meta.renderer_url || `./games/${meta.kind}.js`;
  if (!RENDERERS.has(src)) RENDERERS.set(src, import(src));
  return RENDERERS.get(src);
}

export class GameEngine {
  constructor({ meta, module, activities, stage, hud, baseScore = 0, startLevel = 1 }) {
    this.meta = meta;
    this.stage = stage;
    this.hud = hud;
    this.module = module;
    this.maxErrors = meta.max_errors;
    this.baseScore = baseScore;  // points already earned earlier in the partita
    this.score = 0;
    this.correct = 0;
    this.errors = 0;       // errors against the current budget (see below)
    this.totalErrors = 0;  // all errors of the game, reported to the server
    this.results = [];
    this.stopped = false;
    this.reason = null;
    this.remaining = meta.duration_seconds;
    this.quizLimit = meta.quiz_count || 0;  // 0 → the timer, not a quota, ends the game
    this.played = 0;
    this._force = null;
    this._paused = false;

    // One queue of activities per level; play resumes from the best level.
    this.level = Math.max(1, Math.min(LEVEL_MAX, startLevel));
    this.levelPoints = 0;
    this.streak = 0;
    this._leveledUp = false;
    this.byLevel = new Map();
    for (const a of activities) {
      const lvl = a.level || 1;
      if (!this.byLevel.has(lvl)) this.byLevel.set(lvl, []);
      this.byLevel.get(lvl).push(a);
    }
  }

  /** Play the whole game; resolves with the result summary. */
  async run() {
    this._renderHud();
    if (this.meta.timed) this._startTimer();
    let queue = this.byLevel.get(this.level) || [];
    let i = 0;
    while (!this.stopped && i < queue.length) {
      const over = await this._playActivity(queue[i]);
      if (over) break;
      this.played += 1;
      if (this.quizLimit && this.played >= this.quizLimit) break;
      if (this._leveledUp) {
        this._leveledUp = false;
        await this._showLevelUp();
        queue = this.byLevel.get(this.level) || [];
        i = 0;
      } else {
        i += 1;
      }
      await wait(220);
    }
    clearInterval(this._timer);
    return {
      score: this.score,
      correct: this.correct,
      errors: this.totalErrors,
      results: this.results,
      reason: this.reason || "completed",
      level: this.level,
    };
  }

  _playActivity(activity) {
    // An activity can carry its own error budget (memo: one wrong pair per
    // pair on the board). It replaces the game-wide hearts and starts fresh
    // on every new activity — mistaking is part of that game's mechanic.
    if (activity.max_errors) {
      this.maxErrors = activity.max_errors;
      this.errors = 0;
      this._renderHud();
    }
    return new Promise((resolve) => {
      let settled = false;
      const done = (over) => {
        if (settled) return;
        settled = true;
        this._force = null;
        if (this._cleanup) { const fn = this._cleanup; this._cleanup = null; fn(); }
        resolve(over);
      };
      this._force = () => done(true);

      const ctx = {
        // Renderers register teardown here; it runs when the activity ends for
        // any reason (solved, failed or the timer forcing it to stop).
        onCleanup: (fn) => { this._cleanup = fn; },
        solved: (answer) => {
          // Self-scored games trickle their own points through addPoints;
          // everyone else earns level points and streak bonuses per activity.
          if (!this.meta.self_scored) {
            this.streak += 1;
            const gained = pointsFor(this.level) + streakBonus(this.streak);
            this.score += gained;
            this.levelPoints += gained;
            if (this.level < LEVEL_MAX && this.levelPoints >= thresholdFor(this.level)) {
              this.level += 1;
              this.levelPoints = 0;
              this._leveledUp = true;
            }
          }
          this.correct += 1;
          if (answer !== undefined) this.results.push({ id: activity.id, answer });
          this._renderHud();
          done(false);
        },
        addPoints: (points) => {
          // Live score for self-scored games (see Game.self_scored): the
          // server recomputes the total authoritatively on finish.
          this.score += points;
          this._renderHud();
        },
        fail: (answer) => {
          this.streak = 0;
          if (answer !== undefined) this.results.push({ id: activity.id, answer });
          done(this._loseLife());
        },
        loseLife: () => {
          // No streak reset: only answered results count toward the streak,
          // so the server's replay of the results agrees with the live score.
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
    this.totalErrors += 1;
    if (this.errors >= this.maxErrors) this.reason = this.reason || "errors";
    this._renderHud();
    return this.errors >= this.maxErrors;
  }

  /** Wordless "level up" banner: rocket, the new level and the bonus time. */
  async _showLevelUp() {
    this._paused = true;                       // the banner doesn't eat play time
    if (this.meta.timed) {
      this.remaining += LEVEL_UP_SECONDS;
      this.hud.timer(this.remaining / this.meta.duration_seconds);
    }
    sfx.levelUp();
    celebrate(["🚀", "⭐", "✨"], 18);
    const banner = el("div", "level-up");
    banner.append(
      el("div", "rocket", { textContent: "🚀" }),
      el("div", "lvl", { textContent: String(this.level) })
    );
    if (this.meta.timed) {
      banner.append(el("div", "extra", { textContent: "⏱️ +" + LEVEL_UP_SECONDS }));
    }
    clear(this.stage).appendChild(banner);
    this._renderHud();
    await wait(1400);
    this._paused = false;
  }

  _startTimer() {
    this._timer = setInterval(() => {
      if (this._paused) return;
      this.remaining = Math.max(0, this.remaining - 0.1);
      const fraction = this.remaining / this.meta.duration_seconds;
      this.hud.timer(fraction);
      // Quiet tick once per second while the bar is in the "hurry up" zone.
      const sec = Math.ceil(this.remaining);
      if (fraction < 0.25 && this.remaining > 0 && sec !== this._lastTickSec) {
        this._lastTickSec = sec;
        sfx.tick();
      }
      if (this.remaining <= 0 && !this.stopped) {
        this.stopped = true;
        this.reason = this.reason || "timeout";
        if (this._force) this._force();
      }
    }, 100);
  }

  _renderHud() {
    // Show the running total of the whole partita, not just this game.
    this.hud.render({
      hearts: this.maxErrors - this.errors,
      max: this.maxErrors,
      score: this.baseScore + this.score,
      level: this.level,
    });
  }
}

/**
 * Build the HUD DOM (hearts + level + score, and a timer bar only for timed
 * games) and return a controller. Self-scored games hide hearts and level:
 * their score grows on its own and there is no ladder to climb.
 */
export function buildHud(container, { timed = true, hearts: withHearts = true, level: withLevel = true } = {}) {
  const hud = el("div", "hud");
  const hearts = el("div", "hearts");
  const lvl = el("div", "level");
  const score = el("div", "score");
  if (withHearts) hud.append(hearts);
  if (withLevel) hud.append(lvl);
  hud.append(score);
  container.appendChild(hud);

  let bar = null;
  if (timed) {
    const track = el("div", "timer-track");
    bar = el("div", "timer-bar");
    track.appendChild(bar);
    container.appendChild(track);
  }

  let lastScore = null;
  let lastLevel = null;
  return {
    render({ hearts: h, max, score: s, level }) {
      if (withHearts) {
        hearts.innerHTML = "";
        for (let i = 0; i < max; i++) {
          const heart = el("span", i < h ? "" : "lost", { textContent: "❤️" });
          hearts.appendChild(heart);
        }
      }
      if (withLevel) {
        lvl.textContent = "🚀" + level;
        if (lastLevel !== null && level > lastLevel) {
          lvl.classList.remove("bump");
          void lvl.offsetWidth;             // restart the CSS animation
          lvl.classList.add("bump");
        }
      }
      lastLevel = level;
      score.textContent = "⭐ " + s;
      // Flash the total and float a "+points" chip whenever the score grows.
      if (lastScore !== null && s > lastScore) {
        score.classList.remove("bump");
        void score.offsetWidth;             // restart the CSS animation
        score.classList.add("bump");
        const pop = el("div", "score-pop", { textContent: "+" + (s - lastScore) });
        hud.appendChild(pop);
        setTimeout(() => pop.remove(), 800);
      }
      lastScore = s;
    },
    timer(fraction) {
      if (!bar) return;
      // Bonus seconds can push past the full bar: clamp the display.
      bar.style.width = Math.min(100, Math.max(0, fraction * 100)) + "%";
      bar.style.background = fraction < 0.25 ? "var(--orange)" : "var(--accent)";
    },
  };
}
