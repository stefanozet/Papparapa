# Architettura di Papparapa

Questo documento descrive lo **stack tecnologico** e l'**architettura** del
progetto a livello di codice (moduli, responsabilità, flussi). Per la
descrizione del prodotto (giochi, regole, avvio) vedi il [README](README.md).

## Stack tecnologico

| Livello | Tecnologia |
|---|---|
| Backend | Python 3, [FastAPI](https://fastapi.tiangolo.com/) su [Uvicorn](https://www.uvicorn.org/) (ASGI) |
| ORM / DB | [SQLAlchemy](https://www.sqlalchemy.org/) 2.x, **SQLite** di default (file `backend/papparapa.db`), configurabile via `PAPPARAPA_DATABASE_URL` verso qualsiasi DB supportato (es. Postgres) |
| Validazione / schemi | [Pydantic](https://docs.pydantic.dev/) (via FastAPI) in `schemas.py` |
| Auth | Nessuna libreria esterna: password hashate con **PBKDF2-HMAC-SHA256** (stdlib `hashlib`), token **stateless firmati HMAC** (non JWT, formato custom `body.signature`), tutto in `security.py` |
| Frontend | **JavaScript vanilla**, ES modules nativi del browser — **nessun build step**, nessun framework, nessun bundler/transpiler |
| Stile | CSS puro (`frontend/css/style.css`), mobile-first |
| Audio | Web Audio API sintetizzata a runtime (nessun asset audio) |
| Test | `pytest` + `TestClient` di FastAPI (`backend/tests/test_api.py`) |
| Packaging Python | `requirements.txt` + virtualenv (`.venv`), nessun poetry/pipenv |
| Avvio | `run.sh` (crea venv, installa dipendenze, lancia `uvicorn`) |

Nessun `package.json`: il frontend è servito **staticamente** dallo stesso
processo FastAPI (`StaticFiles`), quindi l'intera app gira con un solo
comando e senza toolchain Node.

## Struttura del progetto

```
Papparapa/
├── backend/
│   ├── app/
│   │   ├── main.py        # crea la FastAPI app, monta i router su /api e i file statici su /
│   │   ├── config.py      # tutta la configurazione, override via env vars
│   │   ├── database.py    # engine SQLAlchemy, sessionmaker, dependency get_db()
│   │   ├── models.py      # ORM: Parent, ChildProfile, GameSession, GameLevel, ActivityStat
│   │   ├── schemas.py     # Pydantic: request/response contract dell'API
│   │   ├── security.py    # hashing password + token firmati + dependency get_current_parent()
│   │   ├── routers/       # auth.py, profiles.py, games.py — endpoint HTTP
│   │   └── games/         # motore dei giochi, indipendente da FastAPI/HTTP
│   └── tests/test_api.py  # test end-to-end via TestClient
└── frontend/
    ├── index.html          # shell SPA (un solo <div id="app">)
    ├── css/style.css
    └── js/                 # ES modules caricati da <script type="module">
        ├── api.js          # client REST (fetch + gestione token)
        ├── engine.js        # motore di gioco lato client: timer, cuori, livelli, punteggio
        ├── app.js           # router di schermate + orchestrazione della partita
        ├── ui.js / sound.js / levels.js
        └── games/           # un renderer per ogni "kind" (choice, memory, memo, simon, maze)
```

## Backend

### Avvio e routing HTTP (`main.py`)

`main.py` è l'unico entry point: crea le tabelle (`Base.metadata.create_all`),
istanzia `FastAPI`, monta i tre router sotto `/api` (`auth`, `profiles`,
`games`) e infine monta l'intera cartella `frontend/` come file statici sulla
root `/` — **dopo** i router API, così `/api/*` ha sempre precedenza. Un solo
processo serve sia API che frontend: non serve un reverse proxy per lo
sviluppo locale.

### Livelli logici

Il backend è organizzato in tre strati con responsabilità nette:

1. **Router (`routers/*.py`)** — solo HTTP: parsing input (Pydantic),
   autenticazione (`Depends(get_current_parent)`), autorizzazione (un
   genitore può leggere/scrivere solo i propri `ChildProfile`), chiamate al
   livello sottostante, mapping in `schemas.*Out`.
2. **Motore giochi (`games/`)** — **puro Python, senza dipendenze da FastAPI
   o dal DB**: genera le attività, valida le risposte, calcola punteggio e
   livello. Riusabile e testabile in isolamento.
3. **Persistenza (`models.py` + `database.py`)** — ORM SQLAlchemy, una
   sessione per richiesta via dependency injection (`get_db`).

### Motore dei giochi come plug-in (`games/`)

Il cuore architetturale del progetto è pensato per l'estendibilità:

- **`base.py`** definisce la classe astratta `Game` (e `ChoiceGame`, la
  sottoclasse per i giochi "scegli tra opzioni"). Ogni gioco implementa
  `difficulty_buckets()`, `_one(bucket)`, `tutorial()`, `validate()`; il
  metodo `generate(start_level)` è ereditato e produce da solo i batch di
  attività per ognuno dei 10 livelli.
- **`registry.py`** fa **auto-discovery**: ad ogni avvio importa ogni modulo
  in `games/catalog/`, raccoglie le sottoclassi concrete di `Game`, le valida
  (attributi richiesti, niente chiavi duplicate, un renderer frontend
  esistente per il proprio `kind`) e le espone come dizionario `GAMES`.
  **Aggiungere un gioco non richiede toccare nessun'altra parte del
  codice** — vedi `games/catalog/README.md` per la ricetta completa.
- **`catalog/`** contiene un file (o una cartella) per gioco. Un gioco
  "a cartella" (es. `entangled/`) può portarsi dietro un `renderer.js`
  proprio, servito dal backend tramite `GET /api/games/{key}/{asset}` (con
  validazione anti path-traversal) e caricato dinamicamente dal frontend.
- **`levels.py`** centralizza le regole di progressione (punti per livello,
  soglie di passaggio, bonus Fibonacci sulle serie) — condivise
  concettualmente con `frontend/js/levels.js` (duplicazione intenzionale:
  il frontend le applica in tempo reale per la UX, il server le **rigioca**
  a fine partita come fonte di verità).
- **`difficulty.py`** implementa lo shrinkage bayesiano che fonde il prior
  parametrico di un bucket con il tasso di fallimento osservato
  (`models.ActivityStat`), così la difficoltà mostrata (🔥) si affina
  giocata dopo giocata.
- **`planner.py`** decide l'ordine di un'intera partita (`GET /api/runs/plan`)
  a partire dalle difficoltà calibrate: giochi facili prima, un po' di
  casualità, e ripropone i più facili in coda in versione più difficile.

### Modello dati (`models.py`)

```
Parent 1───* ChildProfile 1───* GameSession
                            └──* GameLevel   (livello massimo per gioco, resume)
ActivityStat            (aggregati per game_key + bucket, indipendenti dal child)
```

- `GameSession.spec` salva l'**intera partita generata** (JSON, incluse le
  soluzioni): permette al server di ricalcolare punteggio e livello in modo
  autorevole a fine sessione senza fidarsi del client (anti-cheat per i
  giochi a scelta e il ritmo; labirinto e memo sono self-reported, senza
  incentivo a barare essendo un gioco per bambini).
- `GameLevel` è la persistenza del progresso: una riga per `(child, game)`,
  non scende mai — solo `finish_game` la alza se il nuovo massimo è più alto.

### Autenticazione

Nessuna sessione server-side: `create_token`/`verify_token` producono un
token `base64(payload).base64(hmac_sha256(payload))` con scadenza embeddata
(`exp`), verificato ad ogni richiesta protetta tramite la dependency
`get_current_parent` (FastAPI `HTTPBearer`). Le password sono hashate con
PBKDF2-HMAC-SHA256 (200k round, salt casuale per utente), nessuna dipendenza
esterna di crypto.

### Contratto API (sintesi)

| Endpoint | Scopo |
|---|---|
| `POST /api/auth/register`, `/login`, `GET /auth/me` | account genitore |
| `GET/POST /api/profiles`, `GET /api/profiles/{id}/stats` | profili bambino |
| `GET /api/leaderboard` | classifica generale |
| `GET /api/games` | catalogo giochi + difficoltà calibrata |
| `GET /api/games/difficulty` | analytics difficoltà per gioco/bucket |
| `GET /api/runs/plan` | ordine pianificato di una partita completa |
| `POST /api/games/{key}/start` | genera e apre una sessione di gioco |
| `POST /api/sessions/{id}/finish` | invia le risposte, riceve punteggio autorevole |
| `GET /api/games/{key}/{asset}` | asset JS bundlati dai giochi "a cartella" |

## Frontend

Il frontend è una **SPA senza framework**: `index.html` monta un unico
`<div id="app">` e `app.js` (caricato come `<script type="module">`) fa da
router disegnando schermate diverse dentro quel nodo, senza virtual DOM né
templating — manipolazione diretta del DOM.

- **`api.js`** — client REST minimale (`fetch` + gestione/salvataggio del
  token in `localStorage`).
- **`engine.js`** — motore di gioco condiviso tra tutte le dinamiche: timer
  (o conteggio quiz), cuori/errori, calcolo punteggio e livello lato client
  (rispecchia `levels.py`, poi validato dal server a fine partita).
- **`app.js`** — orchestrazione: schermate (login, profili, menu, tutorial,
  partita, risultati, trofei, classifica) e la sequenza `runGames()` che
  incatena i giochi pianificati dal backend.
- **`games/*.js`** — un renderer per ogni `kind` di attività (`choice`,
  `memory`, `memo`, `simon`, `maze`); caricati **dinamicamente** in base al
  `kind`/`renderer_url` restituito dal backend, così un nuovo gioco che
  riusa un kind esistente non richiede alcuna modifica al frontend.
- **`sound.js`** — effetti sonori sintetizzati via Web Audio API (nessun
  file audio da servire).

## Flusso di una partita

1. Il client chiama `GET /api/runs/plan` → ordine dei giochi calibrato sulla
   difficoltà osservata.
2. Per ogni gioco, `POST /api/games/{key}/start`: il backend genera **tutte**
   le attività (batch per livello, incluse le soluzioni) e le manda al
   client in un colpo solo insieme al livello di partenza salvato.
3. Il frontend gioca le attività localmente (timer/quiz-count, cuori,
   punteggio in tempo reale) senza altre chiamate di rete.
4. A fine gioco, `POST /api/sessions/{id}/finish` invia solo le risposte
   date; il server **rigioca** la sequenza con le stesse regole
   (`Game.score_session` / `levels.replay`) per calcolare punteggio e
   livello **autorevoli**, aggiorna `GameLevel` e alimenta `ActivityStat`
   per ricalibrare la difficoltà.

Questo disegno (genera tutto upfront, valida tutto a consuntivo) minimizza
la latenza percepita durante il gioco — nessuna richiesta di rete tra una
micro-attività e l'altra — mantenendo comunque il server come autorità sul
punteggio.

## Testing

`backend/tests/test_api.py` usa `TestClient` di FastAPI per test end-to-end
sull'intera pila HTTP (senza mock): registrazione/login, protezione delle
route (accesso cross-parent negato), il ciclo `start` → `finish` con
verifica del punteggio ricalcolato, e — via BFS — che ogni labirinto
generato sia effettivamente risolvibile.

## Configurazione

Tutta la configurazione passa da variabili d'ambiente lette in
`config.py` (nessun file `.env` committato): `PAPPARAPA_DATABASE_URL`,
`PAPPARAPA_SECRET_KEY`, `PAPPARAPA_TOKEN_TTL`, `PAPPARAPA_POINTS`,
`PAPPARAPA_QUIZZES_PER_GAME`. In sviluppo tutto ha un default sensato
(SQLite locale, secret key di comodo), pensato per essere sovrascritto in
produzione.
