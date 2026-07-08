// Small DOM helpers, screen management and celebration effects.
import { sfx } from "./sound.js";

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

/**
 * Run `action` when the user presses Space or Enter ("confirm and go on").
 * Returns a function that detaches the listener; it also self-detaches once
 * fired, so the primary button on a screen can share the same handler.
 */
export function confirmKey(action) {
  const off = () => window.removeEventListener("keydown", handler);
  const handler = (e) => {
    if (e.key === "Enter" || e.key === " " || e.code === "Space") {
      e.preventDefault();
      off();
      sfx.tap();
      action();
    }
  };
  window.addEventListener("keydown", handler);
  return off;
}

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

/** Small starburst of emoji flying out from a viewport point. */
export function burst(x, y, emojis = ["✨", "⭐"], count = 8) {
  const fx = document.getElementById("fx");
  for (let i = 0; i < count; i++) {
    const piece = el("span", "fx-piece", {
      textContent: emojis[Math.floor(Math.random() * emojis.length)],
    });
    piece.style.left = x + "px";
    piece.style.top = y + "px";
    const angle = (i / count) * 2 * Math.PI + Math.random() * 0.6;
    const dist = 45 + Math.random() * 55;
    piece.animate(
      [
        { transform: "translate(-50%,-50%) scale(1)", opacity: 1 },
        {
          transform: `translate(calc(-50% + ${Math.cos(angle) * dist}px),` +
            ` calc(-50% + ${Math.sin(angle) * dist}px)) scale(.35)`,
          opacity: 0,
        },
      ],
      { duration: 550 + Math.random() * 250, easing: "ease-out", fill: "forwards" }
    );
    fx.appendChild(piece);
    setTimeout(() => piece.remove(), 900);
  }
}

/** Starburst centred on a DOM node (the tapped option, card or cell). */
export function burstFrom(node, emojis) {
  const r = node.getBoundingClientRect();
  burst(r.left + r.width / 2, r.top + r.height / 2, emojis);
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
