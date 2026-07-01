# Papparapa 🎈

App web (mobile-first) di giochi di logica per l'intrattenimento di bambini e
ragazzi. Il giocatore affronta una serie di giochi uno dietro l'altro — come in
una partita a tappe — guadagnando stelle ⭐ ad ogni gioco.

I giochi **non richiedono di saper leggere o scrivere**: ogni gioco è preceduto
da una **spiegazione visuale animata senza testo**, tutti i contenuti sono
icone/emoji, ed è pensato per durare un tempo limitato. **Al terzo errore la
partita finisce.**

## ✨ Caratteristiche

- **Architettura pulita ed estensibile**: aggiungere un gioco = una classe
  Python + un renderer JavaScript (vedi *Aggiungere un gioco*).
- **Back end in Python** (FastAPI) con database SQLite.
- **Registrazione utenti**: il genitore crea un account (email/password) e sotto
  di sé uno o più **profili bambino**, scelti visivamente tramite avatar. Solo le
  schermate del genitore usano testo; tutto ciò che tocca il bambino è wordless.
- **Giochi a tempo**: ogni gioco ha un limite di secondi; una barra mostra il
  tempo che scorre.
- **Tutorial visuale animato** prima di ogni gioco (una manina 👆 indica la
  risposta giusta; nel labirinto il topo cammina da solo fino al formaggio).
- **Regola dei 3 errori**: tre cuori ❤️❤️❤️; al terzo errore il gioco finisce.
- **Punteggio**: 10 punti per ogni micro-attività risolta. I punteggi delle
  risposte a scelta sono **validati lato server** (anti-imbroglio).

## 🎮 I tre giochi (v1)

Ogni gioco è composto da **micro-attività dello stesso tipo**, ripetute finché
il tempo scorre o si raggiungono i 3 errori.

| Gioco | Icona | Micro-attività |
|-------|-------|----------------|
| **Completa la sequenza** | 🔁 | Vengono mostrati alcuni oggetti che formano un motivo (es. 🔴🟡🔴🟡❓); si sceglie tra tre l'oggetto che continua la sequenza. |
| **Trova l'intruso** | 🔍 | Quattro oggetti: tre della stessa categoria e uno diverso; si tocca l'intruso. |
| **Il topo e il formaggio** | 🧀 | Un labirinto: si guida il topo 🐭 fino al formaggio con il d-pad, le frecce o lo swipe. Sbattere contro un muro costa una vita. |

## 🚀 Avvio rapido

```bash
./run.sh
```

Poi apri **http://localhost:8000** (da smartphone: apri l'IP del computer sulla
stessa rete, es. `http://192.168.1.10:8000`).

Avvio manuale:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 🧪 Test

```bash
cd backend && source .venv/bin/activate
pytest
```

I test coprono registrazione/login, protezione delle route, il ciclo completo
start→finish con scoring autorevole, e la verifica che **ogni labirinto generato
sia risolvibile** (BFS).

## 🏗️ Architettura

```
Papparapa/
├── backend/                     # FastAPI + SQLite
│   ├── app/
│   │   ├── main.py              # entry point: monta API (/api) e frontend (/)
│   │   ├── config.py           # configurazione (env-overridable)
│   │   ├── database.py         # engine + sessione SQLAlchemy
│   │   ├── models.py           # Parent, ChildProfile, GameSession
│   │   ├── schemas.py          # schemi Pydantic
│   │   ├── security.py         # hashing password (PBKDF2) + token firmati
│   │   ├── routers/            # auth, profiles, games
│   │   └── games/              # ← motore giochi estensibile
│   │       ├── base.py         # Game / ChoiceGame (classi astratte)
│   │       ├── registry.py     # elenco giochi + ordine della partita
│   │       ├── sequence.py
│   │       ├── odd_one_out.py
│   │       └── maze.py
│   └── tests/test_api.py
├── frontend/                    # HTML/CSS/JS vanilla, zero build step
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── api.js              # client REST + token
│       ├── ui.js               # helper DOM, transizioni, confetti
│       ├── engine.js           # motore: timer, cuori, punteggio
│       ├── app.js              # schermate e orchestrazione della partita
│       └── games/
│           ├── choice.js       # renderer per sequenza + intruso
│           └── maze.js         # renderer labirinto
└── run.sh
```

**Il backend genera i giochi in Python** e li serve al frontend; il frontend li
disegna e li fa giocare. Alla fine invia le risposte: il server ricalcola in
modo autorevole il punteggio dei giochi a scelta (per il labirinto il risultato
è riportato dal client, essendo un gioco per bambini senza incentivo a barare).

## ➕ Aggiungere un gioco

1. **Backend** — crea `backend/app/games/mio_gioco.py`:

   ```python
   from .base import ChoiceGame

   class MioGioco(ChoiceGame):
       key = "mio"; name = "Il mio gioco"; icon = "🎲"; color = "#9B59B6"
       duration_seconds = 70

       def _one(self):
           # ...costruisci una micro-attività...
           return {"kind": "choice", "stimulus": [...], "options": [...], "answer": 0}

       def generate(self):
           return [{"id": i, **self._one()} for i in range(self.activity_count)]

       def tutorial(self):
           return {"id": "t", "kind": "choice", "stimulus": [...], "options": [...], "answer": 0}
   ```

   Registralo in `registry.py` (aggiungi la classe a `_GAME_CLASSES` e, se vuoi,
   a `DEFAULT_RUN`).

2. **Frontend** — se usi una micro-attività di tipo `choice`, non serve altro:
   il renderer esiste già. Per un tipo nuovo, aggiungi un modulo in
   `frontend/js/games/` con `renderActivity(stage, activity, ctx)` e
   `renderTutorial(stage, activity, onDone)`, poi mappalo in `engine.js`
   (`MODULES`). Il motore (timer/cuori/punteggio) è condiviso.

## ⚙️ Scelte e assunzioni (facili da cambiare)

- **"Al terzo errore la partita finisce"** è interpretato come *fine del gioco
  corrente*, dopo il quale si passa al gioco successivo della partita. Per far
  terminare l'intera partita al terzo errore basta interrompere il ciclo in
  `runGames()` (`frontend/js/app.js`) quando `result.reason === "errors"`.
- **Autenticazione**: account genitore con email/password (hash PBKDF2, token
  firmati HMAC, stateless). Nessun dato del bambino oltre nome e avatar.
- **Punti per attività**: `PAPPARAPA_POINTS` (default 10).
- **Configurazione** via variabili d'ambiente: `PAPPARAPA_DATABASE_URL`,
  `PAPPARAPA_SECRET_KEY` (cambiala in produzione!), `PAPPARAPA_TOKEN_TTL`.
