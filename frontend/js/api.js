// Thin API client with token storage in localStorage.
const TOKEN_KEY = "papparapa_token";

export const api = {
  token() { return localStorage.getItem(TOKEN_KEY); },
  setToken(t) { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); },
  logout() { this.setToken(null); },

  async req(path, { method = "GET", body, auth = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth && this.token()) headers.Authorization = `Bearer ${this.token()}`;
    const res = await fetch(`/api${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      let detail;
      try { detail = (await res.json()).detail; } catch { /* ignore */ }
      const err = new Error(detail || res.statusText);
      err.status = res.status;
      throw err;
    }
    return res.status === 204 ? null : res.json();
  },

  register(email, password) {
    return this.req("/auth/register", { method: "POST", auth: false, body: { email, password } });
  },
  login(email, password) {
    return this.req("/auth/login", { method: "POST", auth: false, body: { email, password } });
  },
  me() { return this.req("/auth/me"); },
  children() { return this.req("/profiles"); },
  createChild(name, avatar) {
    return this.req("/profiles", { method: "POST", body: { name, avatar } });
  },
  stats(childId) { return this.req(`/profiles/${childId}/stats`); },
  leaderboard() { return this.req("/leaderboard"); },
  games() { return this.req("/games", { auth: false }); },
  planRun(childId) { return this.req(`/runs/plan?child_id=${childId}`); },
  start(key, childId, levelDelta = 0) {
    return this.req(
      `/games/${key}/start?child_id=${childId}&level_delta=${levelDelta}`,
      { method: "POST" }
    );
  },
  finish(sessionId, payload) {
    return this.req(`/sessions/${sessionId}/finish`, { method: "POST", body: payload });
  },
};
