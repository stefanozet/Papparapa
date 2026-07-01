// Small DOM helpers, screen management and celebration effects.

export function el(tag, cls, props = {}) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  Object.assign(node, props);
  return node;
}

export function clear(node) { node.innerHTML = ""; return node; }

const appRoot = () => document.getElementById("app");

/** Replace the whole app view with a freshly built screen element. */
export function showScreen(build) {
  const root = clear(appRoot());
  const screen = el("div", "screen");
  build(screen);
  root.appendChild(screen);
  return screen;
}

export function setTheme(color) {
  document.documentElement.style.setProperty("--accent", color || "#5B8DEF");
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = color || "#5B8DEF";
}

export function wait(ms) { return new Promise((r) => setTimeout(r, ms)); }

/** Rain a burst of celebratory emoji from the top of the screen. */
export function celebrate(emojis = ["⭐", "🎉", "🌟", "🎈", "✨"], count = 28) {
  const fx = document.getElementById("fx");
  for (let i = 0; i < count; i++) {
    const piece = el("span", "fx-piece", {
      textContent: emojis[Math.floor(Math.random() * emojis.length)],
    });
    piece.style.left = Math.random() * 100 + "vw";
    const dur = 1.8 + Math.random() * 1.6;
    piece.style.animation = `fall ${dur}s linear ${Math.random() * 0.6}s forwards`;
    fx.appendChild(piece);
    setTimeout(() => piece.remove(), (dur + 1) * 1000);
  }
}

/** Briefly pop an emoji in the centre of the stage as instant feedback. */
export function popFeedback(stage, emoji) {
  const p = el("div", "big-emoji", { textContent: emoji });
  p.style.position = "absolute";
  p.style.zIndex = 30;
  p.style.pointerEvents = "none";
  stage.appendChild(p);
  setTimeout(() => p.remove(), 600);
}
