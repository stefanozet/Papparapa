// Application controller: authentication, profile selection, game menu and
// the run orchestration (playing several games one after another).
import { api } from "./api.js";
import { buildHud, GameEngine, moduleFor } from "./engine.js";
import { celebrate, clear, el, setTheme, showScreen, wait } from "./ui.js";

const AVATARS = ["🐻", "🦊", "🐰", "🐼", "🐶", "🐱", "🦁", "🐸", "🐵", "🦄",
  "🐯", "🐨", "🐷", "🐔", "🐙", "🦖", "🐝", "🐳", "🦉", "🐢"];

let catalogue = null;   // { games: [...], default_run: [...] }
let currentChild = null;

// --------------------------------------------------------------------------- //
// Boot
// --------------------------------------------------------------------------- //
async function boot() {
  catalogue = await api.games();
  if (api.token()) {
    try { await api.me(); return showProfiles(); }
    catch { api.logout(); }
  }
  showAuth();
}

// --------------------------------------------------------------------------- //
// Auth (parent-facing – text is fine here)
// --------------------------------------------------------------------------- //
function showAuth(mode = "login") {
  setTheme("#5B8DEF");
  showScreen((screen) => {
    screen.classList.add("center");
    screen.append(
      el("h1", "logo", { innerHTML: 'Papparapa <span class="emoji">🎈</span>' }),
      el("p", "subtitle", { textContent: "Giochi di logica per bambini" })
    );

    const form = el("form");
    const email = el("input", null, { type: "email", placeholder: "Email genitore", required: true, autocomplete: "email" });
    const pass = el("input", null, { type: "password", placeholder: "Password", required: true, minLength: 6 });
    const err = el("div", "error-msg");
    const submit = el("button", "btn", { type: "submit", textContent: mode === "login" ? "Entra" : "Crea account" });
    form.append(email, pass, err, submit);

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      err.textContent = "";
      submit.disabled = true;
      try {
        const fn = mode === "login" ? api.login : api.register;
        const { access_token } = await fn.call(api, email.value.trim(), pass.value);
        api.setToken(access_token);
        await showProfiles();
      } catch (ex) {
        err.textContent = ex.message || "Errore";
        submit.disabled = false;
      }
    });
    screen.appendChild(form);

    const toggle = el("div", "btn ghost", {
      textContent: mode === "login" ? "Non hai un account? Registrati" : "Hai già un account? Entra",
    });
    toggle.onclick = () => showAuth(mode === "login" ? "register" : "login");
    screen.appendChild(toggle);
  });
}

// --------------------------------------------------------------------------- //
// Profile selection
// --------------------------------------------------------------------------- //
async function showProfiles() {
  setTheme("#5B8DEF");
  const children = await api.children();
  showScreen((screen) => {
    const bar = topbar({ withBack: false });
    const logout = el("div", "btn ghost", { textContent: "Esci" });
    logout.onclick = () => { api.logout(); showAuth(); };
    bar.append(el("div", "spacer"), logout);
    screen.appendChild(bar);

    screen.appendChild(el("p", "subtitle", { textContent: "Chi vuole giocare?" }));

    const grid = el("div", "grid profiles");
    children.forEach((c) => {
      const card = el("div", "profile-card");
      card.append(el("div", "face", { textContent: c.avatar }), el("div", "name", { textContent: c.name }));
      card.onclick = () => { currentChild = c; showHome(); };
      grid.appendChild(card);
    });

    const add = el("div", "profile-card");
    add.append(el("div", "face", { textContent: "➕" }), el("div", "name", { textContent: "Nuovo" }));
    add.onclick = showAddChild;
    grid.appendChild(add);

    screen.appendChild(grid);
  });
}

function showAddChild() {
  showScreen((screen) => {
    const bar = topbar({ onBack: showProfiles });
    screen.appendChild(bar);
    screen.appendChild(el("p", "subtitle", { textContent: "Crea un giocatore" }));

    let chosen = AVATARS[0];
    const name = el("input", null, { placeholder: "Nome", maxLength: 30 });
    name.style.maxWidth = "340px";
    screen.appendChild(name);

    const grid = el("div", "avatar-grid");
    const tiles = AVATARS.map((a) => {
      const t = el("div", "avatar-pick", { textContent: a });
      t.onclick = () => { chosen = a; tiles.forEach((x) => x.classList.remove("selected")); t.classList.add("selected"); };
      grid.appendChild(t);
      return t;
    });
    tiles[0].classList.add("selected");
    screen.appendChild(grid);

    const err = el("div", "error-msg");
    const save = el("button", "btn", { textContent: "Crea" });
    save.onclick = async () => {
      if (!name.value.trim()) { err.textContent = "Scrivi un nome"; return; }
      save.disabled = true;
      try {
        await api.createChild(name.value.trim(), chosen);
        await showProfiles();
      } catch (ex) { err.textContent = ex.message; save.disabled = false; }
    };
    screen.append(err, save);
  });
}

// --------------------------------------------------------------------------- //
// Home menu
// --------------------------------------------------------------------------- //
function showHome() {
  setTheme("#5B8DEF");
  showScreen((screen) => {
    const bar = topbar({ onBack: showProfiles });
    bar.append(el("div", "spacer"), el("div", "who", { textContent: currentChild.avatar }));
    screen.appendChild(bar);

    const play = el("button", "btn-huge", { textContent: "▶️", title: "Gioca tutto" });
    play.onclick = () => runGames(catalogue.default_run);
    const playWrap = el("div", "center");
    playWrap.style.gap = "8px";
    playWrap.append(play, el("p", "subtitle", { textContent: "Gioca!" }));
    screen.appendChild(playWrap);

    const grid = el("div", "grid");
    grid.style.gridTemplateColumns = "repeat(3, 1fr)";
    grid.style.marginTop = "18px";
    catalogue.games.forEach((g) => {
      const card = el("div", "game-card");
      card.style.setProperty("--accent", g.color);
      card.append(el("div", "face", { textContent: g.icon }));
      card.onclick = () => runGames([g.key]);
      grid.appendChild(card);
    });
    screen.appendChild(grid);

    const trophy = el("div", "btn ghost", { textContent: "🏆 I miei punti" });
    trophy.style.marginTop = "auto";
    trophy.onclick = showStats;
    screen.appendChild(trophy);
  });
}

async function showStats() {
  const stats = await api.stats(currentChild.id);
  showScreen((screen) => {
    screen.appendChild(topbar({ onBack: showHome }));
    screen.classList.add("center");
    screen.append(
      el("div", "big-emoji", { textContent: "🏆" }),
      el("div", "big-score", { textContent: "⭐ " + stats.total_score })
    );
    const byKey = Object.fromEntries(catalogue.games.map((g) => [g.key, g]));
    const list = el("div", "grid");
    list.style.width = "100%";
    Object.entries(stats.games).forEach(([key, s]) => {
      const g = byKey[key] || { icon: "🎮" };
      const row = el("div", "profile-card");
      row.style.flexDirection = "row";
      row.style.justifyContent = "space-between";
      row.style.padding = "14px 20px";
      row.append(
        el("span", null, { textContent: g.icon, style: "font-size:2rem" }),
        el("span", null, { textContent: "⭐ " + s.best, style: "font-weight:800" })
      );
      list.appendChild(row);
    });
    if (!Object.keys(stats.games).length) {
      screen.appendChild(el("p", "subtitle", { textContent: "Gioca per guadagnare stelle!" }));
    }
    screen.appendChild(list);
  });
}

// --------------------------------------------------------------------------- //
// Playing a run of one or more games
// --------------------------------------------------------------------------- //
async function runGames(keys) {
  let total = 0;
  for (let i = 0; i < keys.length; i++) {
    const key = keys[i];
    const start = await api.start(key, currentChild.id);
    setTheme(start.game.color);

    await playTutorial(start.game, start.tutorial);
    const result = await playGame(start.game, start.activities);

    const finish = await api.finish(start.session_id, {
      results: result.results,
      errors: result.errors,
      ended_reason: result.reason,
    });
    total += finish.score;
    await showGameResult(start.game, finish, i < keys.length - 1);
  }
  await showFinalResult(total, keys.length);
}

/** Wordless animated demo, then a big "ready" button. */
function playTutorial(game, tutorial) {
  return new Promise((resolve) => {
    showScreen((screen) => {
      screen.classList.add("game-screen");
      setTheme(game.color);
      const header = el("div", "center");
      header.style.padding = "16px 0 0";
      header.append(el("div", "ready-emoji", { textContent: game.icon }));
      screen.appendChild(header);

      const stage = el("div", null);
      stage.id = "stage";
      screen.appendChild(stage);

      const module = moduleFor(game.key);
      module.renderTutorial(stage, tutorial, () => {
        const go = el("button", "btn-huge", { textContent: "👍" });
        go.style.margin = "0 auto 30px";
        go.onclick = resolve;
        screen.appendChild(go);
      });
    });
  });
}

async function playGame(game, activities) {
  let hud;
  const screen = showScreen((s) => {
    s.classList.add("game-screen");
    hud = buildHud(s);
    const stage = el("div", null);
    stage.id = "stage";
    s.appendChild(stage);
  });
  const stage = screen.querySelector("#stage");
  const engine = new GameEngine({ meta: game, activities, stage, hud });
  return engine.run();
}

function starsFor(correct) {
  if (correct >= 12) return "⭐⭐⭐";
  if (correct >= 6) return "⭐⭐";
  if (correct >= 1) return "⭐";
  return "🙂";
}

function showGameResult(game, finish, more) {
  return new Promise((resolve) => {
    if (finish.correct_count > 0) celebrate();
    showScreen((screen) => {
      screen.classList.add("center");
      setTheme(game.color);
      screen.append(
        el("div", "big-emoji", { textContent: game.icon }),
        el("div", "stars-row", { textContent: starsFor(finish.correct_count) }),
        el("div", "big-score", { textContent: "⭐ " + finish.score })
      );
      const next = el("button", "btn-huge", { textContent: more ? "➡️" : "🏁" });
      next.onclick = resolve;
      screen.appendChild(next);
    });
  });
}

async function showFinalResult(total, gameCount) {
  celebrate(["🏆", "⭐", "🎉", "🌟", "🎈", "✨"], 40);
  await wait(150);
  showScreen((screen) => {
    screen.classList.add("center");
    setTheme("#5B8DEF");
    screen.append(
      el("div", "big-emoji", { textContent: "🏆" }),
      el("div", "big-score", { textContent: "⭐ " + total }),
      el("p", "subtitle", { textContent: currentChild.avatar })
    );
    const again = el("button", "btn-huge", { textContent: "🔁" });
    again.onclick = showHome;
    screen.appendChild(again);
    const home = el("div", "btn ghost", { textContent: "🏠" });
    home.onclick = showHome;
    screen.appendChild(home);
  });
}

// --------------------------------------------------------------------------- //
// Shared bits
// --------------------------------------------------------------------------- //
function topbar({ onBack, withBack = true } = {}) {
  const bar = el("div", "topbar");
  if (withBack && onBack) {
    const back = el("button", "back", { textContent: "‹", type: "button" });
    back.onclick = onBack;
    bar.appendChild(back);
  }
  return bar;
}

boot().catch((e) => {
  document.getElementById("app").innerHTML =
    `<div class="screen center"><div class="big-emoji">😵</div><p>${e.message}</p></div>`;
});
