// Application controller: authentication, profile selection, game menu and
// the run orchestration (playing several games one after another).
import { api } from "./api.js";
import { buildHud, GameEngine, loadRenderer } from "./engine.js";
import { sfx } from "./sound.js";
import { celebrate, clear, confirmKey, el, setTheme, showScreen, wait } from "./ui.js";

const AVATARS = ["🐻", "🦊", "🐰", "🐼", "🐶", "🐱", "🦁", "🐸", "🐵", "🦄",
  "🐯", "🐨", "🐷", "🐔", "🐙", "🦖", "🐝", "🐳", "🦉", "🐢"];

let catalogue = null;   // { games: [...] } — menu order, easiest first
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

    // A full partita follows the server's plan: easy games first, and the
    // easiest ones come back at the end in a harder mode (level_delta > 0).
    const play = el("button", "btn-huge", { textContent: "▶️", title: "Gioca tutto" });
    play.onclick = async () => {
      try { runGames((await api.planRun(currentChild.id)).plan); }
      catch (ex) { showError(ex, showHome); }
    };
    const playWrap = el("div", "center");
    playWrap.style.gap = "8px";
    playWrap.append(play, el("p", "subtitle", { textContent: "Gioca!" }));
    screen.appendChild(playWrap);

    const grid = el("div", "grid");
    grid.style.gridTemplateColumns = "repeat(3, 1fr)";
    grid.style.marginTop = "18px";
    catalogue.games.filter((g) => !g.advanced).forEach((g) => {
      grid.appendChild(gameCard(g));
    });
    screen.appendChild(grid);

    const links = el("div", "bottom-links");
    const trophy = el("div", "btn ghost", { textContent: "🏆 I miei punti" });
    trophy.onclick = showStats;
    const ranking = el("div", "btn ghost", { textContent: "🏅 Classifica" });
    ranking.onclick = showLeaderboard;
    links.append(trophy, ranking);
    if (catalogue.games.some((g) => g.advanced)) {
      const adv = el("div", "btn ghost", { textContent: "🧪 Giochi avanzati" });
      adv.onclick = showAdvanced;
      links.appendChild(adv);
    }
    screen.appendChild(links);
  });
}

function gameCard(g) {
  const card = el("div", "game-card");
  card.style.setProperty("--accent", g.color);
  card.append(el("div", "face", { textContent: g.icon }));
  if (g.stars) card.append(el("div", "diff", { textContent: "🔥".repeat(g.stars) }));
  card.onclick = () => runGames([{ key: g.key }]);
  return card;
}

/** Advanced games: played on demand, scored outside the ⭐ economy. */
function showAdvanced() {
  setTheme("#5B8DEF");
  showScreen((screen) => {
    screen.appendChild(topbar({ onBack: showHome }));
    screen.appendChild(el("p", "subtitle", { textContent: "🧪 Giochi avanzati" }));
    const grid = el("div", "grid");
    grid.style.gridTemplateColumns = "repeat(3, 1fr)";
    grid.style.marginTop = "18px";
    catalogue.games.filter((g) => g.advanced).forEach((g) => {
      grid.appendChild(gameCard(g));
    });
    screen.appendChild(grid);
  });
}

/** Full-screen error state: a failed fetch must never leave a dead button. */
function showError(ex, onBack) {
  showScreen((screen) => {
    screen.appendChild(topbar({ onBack }));
    const body = el("div", "scroll-area");
    body.append(
      el("div", "big-emoji", { textContent: "😵" }),
      el("p", "subtitle", { textContent: ex.message || "Errore" })
    );
    screen.appendChild(body);
  });
}

async function showStats() {
  let stats;
  try { stats = await api.stats(currentChild.id); }
  catch (ex) { return showError(ex, showHome); }
  showScreen((screen) => {
    screen.appendChild(topbar({ onBack: showHome }));
    // The list can outgrow the viewport: the topbar stays put and the body
    // scrolls on its own, so the back button is always reachable.
    const body = el("div", "scroll-area");
    body.append(
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
      body.appendChild(el("p", "subtitle", { textContent: "Gioca per guadagnare stelle!" }));
    }
    body.appendChild(list);
    screen.appendChild(body);
  });
}

async function showLeaderboard() {
  setTheme("#5B8DEF");
  let entries;
  try { entries = await api.leaderboard(); }
  catch (ex) { return showError(ex, showHome); }
  showScreen((screen) => {
    screen.appendChild(topbar({ onBack: showHome }));
    const body = el("div", "scroll-area");
    body.append(el("div", "big-emoji", { textContent: "🏅" }));

    const medals = ["🥇", "🥈", "🥉"];
    const list = el("div", "grid");
    list.style.width = "100%";
    entries.forEach((entry, i) => {
      const mine = entry.child_id === currentChild.id;
      const row = el("div", "rank-row" + (mine ? " me" : ""));
      row.append(
        el("span", "rank", { textContent: medals[i] || String(i + 1) }),
        el("span", "face", { textContent: entry.avatar }),
        el("span", "name", { textContent: entry.name }),
        el("span", "pts", { textContent: "⭐ " + entry.total_score })
      );
      list.appendChild(row);
    });
    if (!entries.length) {
      body.appendChild(el("p", "subtitle", { textContent: "Ancora nessun giocatore" }));
    }
    body.appendChild(list);
    screen.appendChild(body);
  });
}

// --------------------------------------------------------------------------- //
// Playing a run of one or more games
// --------------------------------------------------------------------------- //
async function runGames(plan) {
  let total = 0;
  let gameOver = false;
  try {
    for (let i = 0; i < plan.length; i++) {
      const entry = plan[i];
      const start = await api.start(entry.key, currentChild.id, entry.level_delta || 0);
      setTheme(start.game.color);
      // The renderer arrives with the game's meta (base kind or bundled
      // renderer_url); a game the frontend can't render must not crash here.
      const module = await loadRenderer(start.game);

      await playTutorial(start.game, module, start.tutorial);
      const result = await playGame(start.game, module, start.activities, total, start.start_level);

      const finish = await api.finish(start.session_id, {
        results: result.results,
        errors: result.errors,
        ended_reason: result.reason,
      });
      total += finish.score;

      // Three errors end the whole partita, not just the current game.
      if (result.reason === "errors") {
        gameOver = true;
        break;
      }
      await showGameResult(start.game, finish, i < plan.length - 1);
    }
  } catch (ex) {
    return showError(ex, showHome);
  }
  await showFinalResult(total, gameOver);
}

/** Wordless animated demo, then a big "ready" button. */
function playTutorial(game, module, tutorial) {
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

      module.renderTutorial(stage, tutorial, () => {
        const go = el("button", "btn-huge", { textContent: "👍" });
        go.style.margin = "0 auto 30px";
        const off = confirmKey(() => { off(); resolve(); });   // Space/Enter starts
        go.onclick = () => { off(); resolve(); };
        screen.appendChild(go);
      });
    });
  });
}

async function playGame(game, module, activities, baseScore = 0, startLevel = 1) {
  let hud;
  const screen = showScreen((s) => {
    s.classList.add("game-screen");
    hud = buildHud(s, {
      timed: game.timed,
      hearts: !game.self_scored,
      level: !game.self_scored,
    });
    const stage = el("div", null);
    stage.id = "stage";
    s.appendChild(stage);
  });
  const stage = screen.querySelector("#stage");
  const engine = new GameEngine({ meta: game, module, activities, stage, hud, baseScore, startLevel });
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
    if (finish.correct_count > 0) { celebrate(); sfx.win(); }
    showScreen((screen) => {
      screen.classList.add("center");
      setTheme(game.color);
      screen.append(
        el("div", "big-emoji", { textContent: game.icon }),
        el("div", "stars-row", { textContent: starsFor(finish.correct_count) }),
        el("div", "big-score", { textContent: "⭐ " + finish.score })
      );
      if (!game.self_scored) {
        screen.append(el("div", "level-line", { textContent: "🚀 " + finish.level }));
      }
      const next = el("button", "btn-huge", { textContent: more ? "➡️" : "🏁" });
      const off = confirmKey(() => { off(); resolve(); });
      next.onclick = () => { off(); resolve(); };
      screen.appendChild(next);
    });
  });
}

async function showFinalResult(total, gameOver) {
  // A partita that ended on the third mistake still celebrates the points won,
  // just a little more gently (no confetti, a friendly face instead of a cup).
  if (gameOver) sfx.gameOver();
  else { celebrate(["🏆", "⭐", "🎉", "🌟", "🎈", "✨"], 40); sfx.win(); }
  await wait(150);
  showScreen((screen) => {
    screen.classList.add("center");
    setTheme("#5B8DEF");
    screen.append(
      el("div", "big-emoji", { textContent: gameOver ? "🙂" : "🏆" }),
      el("div", "big-score", { textContent: "⭐ " + total }),
      el("p", "subtitle", { textContent: currentChild.avatar })
    );
    const off = confirmKey(() => { off(); showHome(); });
    const again = el("button", "btn-huge", { textContent: "🔁" });
    again.onclick = () => { off(); showHome(); };
    screen.appendChild(again);
    const home = el("div", "btn ghost", { textContent: "🏠" });
    home.onclick = () => { off(); showHome(); };
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
