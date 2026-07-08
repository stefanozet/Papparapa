// Level rules, mirrored from the backend (backend/app/games/levels.py).
// The engine applies them live to drive the HUD, the level-up banner and the
// bonus seconds; the server replays the same rules over the submitted results
// to recompute score and level authoritatively.

export const LEVEL_MAX = 10;
export const LEVEL_UP_ANSWERS = 3;   // correct answers' worth of points per level
export const LEVEL_UP_SECONDS = 5;   // extra time granted on every level-up

const BASE_POINTS = 10;
const STREAK_START = 3;              // streak length that earns the first bonus

/** Points for one correct answer at `level`: 10, 15, 22, 33, 50, … */
export function pointsFor(level) {
  return Math.floor(BASE_POINTS * 1.5 ** (level - 1));
}

/** Points to accumulate while at `level` to move up to the next one. */
export function thresholdFor(level) {
  return LEVEL_UP_ANSWERS * pointsFor(level);
}

/**
 * Fibonacci streak bonus for the `streak`-th consecutive correct answer.
 * The 3rd in a row earns +1; then every streak equal to 3 + fib (fib = 1, 2,
 * 3, 5, 8, 13, …) earns index + 1: streaks 3, 4, 5, 6, 8, 11, 16 → +1, +1,
 * +2, +3, +4, +5, +6. A wrong answer resets the streak.
 */
export function streakBonus(streak) {
  if (streak < STREAK_START) return 0;
  if (streak === STREAK_START) return 1;
  let fib = 1, nxt = 2, index = 0;
  while (STREAK_START + fib <= streak) {
    if (STREAK_START + fib === streak) return index + 1;
    [fib, nxt] = [nxt, fib + nxt];
    index += 1;
  }
  return 0;
}
