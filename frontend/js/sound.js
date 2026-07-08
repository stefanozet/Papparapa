// Synthesised sound effects (Web Audio API) — no audio files to download.
// Every sound is short, soft and kid-friendly. The floating 🔊/🔇 button
// toggles all sounds; the choice is remembered in localStorage. On devices
// that support it, mistakes also give a small vibration.

const STORE_KEY = "papparapa-sound";
let muted = false;
try { muted = localStorage.getItem(STORE_KEY) === "off"; } catch { /* private mode */ }

// The AudioContext is created lazily inside a user gesture (a tap or key
// press), which is what browser autoplay policies require.
let ac = null;
function ctx() {
  if (!ac) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ac = new AC();
  }
  if (ac.state === "suspended") ac.resume();
  return ac;
}

/** Play one note: frequency in Hz, offset/duration in seconds. */
function tone(freq, { at = 0, dur = 0.15, type = "triangle", vol = 0.18, slideTo = null } = {}) {
  if (muted) return;
  const c = ctx();
  if (!c) return;
  const t0 = c.currentTime + at;
  const osc = c.createOscillator();
  const gain = c.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, t0);
  if (slideTo) osc.frequency.exponentialRampToValueAtTime(slideTo, t0 + dur);
  gain.gain.setValueAtTime(0.0001, t0);
  gain.gain.linearRampToValueAtTime(vol, t0 + 0.012);
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  osc.connect(gain).connect(c.destination);
  osc.start(t0);
  osc.stop(t0 + dur + 0.05);
}

function buzz(ms) {
  if (navigator.vibrate) navigator.vibrate(ms);
}

// Note frequencies (Hz) used by the jingles.
const F4 = 349.23, A4 = 440, C5 = 523.25, D5 = 587.33, E5 = 659.25,
  G5 = 783.99, A5 = 880, C6 = 1046.5, E6 = 1318.5;

export const sfx = {
  /** Soft click for buttons and selections. */
  tap() { tone(880, { dur: 0.06, vol: 0.1 }); },
  /** Rising blip for a card turning over. */
  flip() { tone(520, { dur: 0.09, vol: 0.14, slideTo: 780 }); },
  /** Tiny step blip (maze walking). */
  move() { tone(700, { dur: 0.05, vol: 0.07 }); },
  /** Quiet clock tick while the timer runs low. */
  tick() { tone(1050, { dur: 0.035, type: "square", vol: 0.04 }); },
  /** "Look!" cue: two gentle rising notes (memory peek, simon playback). */
  peek() { tone(G5, { dur: 0.12, vol: 0.1 }); tone(C6, { at: 0.13, dur: 0.16, vol: 0.1 }); },

  /** Happy ascending chime for a correct answer. */
  correct() {
    tone(C5, { dur: 0.12 });
    tone(E5, { at: 0.09, dur: 0.12 });
    tone(G5, { at: 0.18, dur: 0.24 });
  },
  /** Two bright notes for a memo pair found. */
  match() {
    tone(E5, { dur: 0.1, vol: 0.16 });
    tone(A5, { at: 0.08, dur: 0.2, vol: 0.16 });
  },
  /** Gentle "wah-wah" for a wrong answer (a heart is lost). */
  wrong() {
    tone(311, { dur: 0.18, slideTo: 250 });
    tone(233, { at: 0.18, dur: 0.3, slideTo: 180 });
    buzz(80);
  },
  /** Soft low double-blip for a memo mismatch (no heart lost). */
  miss() {
    tone(240, { dur: 0.1, vol: 0.12 });
    tone(200, { at: 0.1, dur: 0.14, vol: 0.12 });
  },
  /** Low thud for the mouse bumping a maze wall. */
  bump() {
    tone(140, { dur: 0.16, type: "square", vol: 0.14, slideTo: 90 });
    buzz(60);
  },
  /** One note per drum pad (pentatonic, so any order sounds musical). */
  pad(i) {
    const notes = [C5, E5, G5, C6, D5, A5];
    tone(notes[i % notes.length], { dur: 0.3, vol: 0.2 });
  },
  /** Rising arpeggio for the 🚀 level-up banner. */
  levelUp() {
    [C5, E5, G5, C6].forEach((n, k) => tone(n, { at: k * 0.09, dur: 0.14 }));
    tone(E6, { at: 0.36, dur: 0.35, vol: 0.15 });
  },
  /** Short fanfare for the result screens. */
  win() {
    [C5, E5, G5].forEach((n, k) => tone(n, { at: k * 0.12, dur: 0.16, vol: 0.2 }));
    tone(C6, { at: 0.36, dur: 0.5, vol: 0.2 });
    tone(E6, { at: 0.48, dur: 0.4, vol: 0.12 });
  },
  /** Gentle descending phrase when the partita ends on the third error. */
  gameOver() {
    [E5, C5, A4, F4].forEach((n, k) => tone(n, { at: k * 0.16, dur: 0.22, vol: 0.14 }));
  },
};

// --------------------------------------------------------------------------- //
// Mute toggle + generic UI clicks (module-level: runs once at import)
// --------------------------------------------------------------------------- //
const muteBtn = document.getElementById("mute");
function paintMute() {
  if (!muteBtn) return;
  muteBtn.textContent = muted ? "🔇" : "🔊";
  muteBtn.setAttribute("aria-label", muted ? "Attiva i suoni" : "Disattiva i suoni");
}
if (muteBtn) {
  paintMute();
  muteBtn.addEventListener("click", () => {
    muted = !muted;
    try { localStorage.setItem(STORE_KEY, muted ? "off" : "on"); } catch { /* ignore */ }
    paintMute();
    if (!muted) sfx.tap();
  });
}

// Soft click on navigation controls. Game boards (options, cards, d-pad) play
// their own sounds, so they are deliberately not in this list.
document.addEventListener("click", (e) => {
  if (e.target.closest("#mute")) return;
  if (e.target.closest(".btn, .btn-huge, .back, .profile-card, .game-card, .avatar-pick")) {
    sfx.tap();
  }
});