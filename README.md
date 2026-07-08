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
- **Trofei e classifica generale**: dalla home si aprono la pagina 🏆 con il
  totale e le stelle per gioco del bambino, e la pagina 🏅 con la **classifica
  generale** di tutti i giocatori (`GET /api/leaderboard`): medaglie 🥇🥈🥉 per
  i primi tre e la propria riga evidenziata. Entrambe le pagine scorrono se la
  lista esce dallo schermo, con il pulsante per tornare indietro sempre in alto.
- **Timer di 15 secondi per ogni gioco**: ogni gioco dura **15 secondi** (barra
  che scorre). In quel tempo si accumulano punti; allo scadere si passa al gioco
  successivo. Si può comunque finire prima al terzo errore.
- **Comandi da tastiera**: i tasti **1–9** selezionano un'opzione e **barra
  o invio** confermano e vanno avanti (anche su tutorial e schermate di
  risultato); nel memo girano la carta e nel ritmo suonano il tamburo
  direttamente; nel labirinto si usano le frecce. Su touch basta toccare.
- **Tutorial visuale animato** prima di ogni gioco (una manina 👆 indica la
  risposta giusta; nel labirinto il topo cammina da solo fino al formaggio).
- **Suoni ed effetti**: effetti sonori sintetizzati con la Web Audio API
  (nessun file audio): jingle per risposta esatta, "wah-wah" gentile per
  l'errore, note pentatoniche sui tamburi, fanfara sui risultati, razzo di
  level-up, ticchettio quando il tempo scarseggia. In più stelline ✨ che
  esplodono sul punto toccato e una piccola vibrazione sugli errori (dove
  supportata). Il pulsante 🔊/🔇 in basso a destra li spegne (scelta
  ricordata sul dispositivo).
- **Regola dei 3 errori**: tre cuori ❤️❤️❤️; al terzo errore la partita finisce.
  Nel labirinto **sbattere contro un muro costa un cuore**, nel ritmo lo costa
  **un tamburo sbagliato**. Il memo fa eccezione: sbagliare coppia fa parte del
  gioco, quindi ogni tabellone ha un **budget di errori pari alle sue coppie**
  (tessere ÷ 2), che **si azzera a ogni nuovo tabellone**; solo esaurirlo fa
  finire la partita.
- **10 livelli per gioco**: si parte dal proprio livello migliore (salvato per
  bambino e per gioco) e si sale accumulando punti; al passaggio di livello un
  banner 🚀 senza parole e **+5 secondi** sul timer.
- **Punteggio**: i punti di una risposta dipendono dal livello
  (`⌊10 × 1,5^(livello−1)⌋`), più i **bonus Fibonacci** per le serie di
  risposte esatte consecutive. Il punteggio mostrato è il **totale della
  partita** e lampeggia a ogni risposta esatta; punteggio e livello sono
  **ricalcolati lato server** (anti-imbroglio).

## 🎮 I giochi

Ogni gioco è composto da **micro-attività dello stesso tipo**, ripetute finché
il tempo scorre o si raggiungono i 3 errori.

| Gioco | Icona | Micro-attività |
|-------|-------|----------------|
| **Completa la sequenza** | 🔁 | Vengono mostrati alcuni oggetti che formano un motivo (es. 🔴🟡🔴🟡❓); si sceglie tra tre l'oggetto che continua la sequenza. |
| **Trova l'intruso** | 🔍 | Quattro oggetti: tre della stessa categoria e uno diverso; si tocca l'intruso. |
| **Cosa va insieme?** | 🧩 | Viene mostrato un oggetto (es. 🐝); si sceglie tra tre quello che gli va insieme (🍯). Associazioni logiche di tutti i giorni. |
| **Conta e abbina** | 🔢 | Viene mostrato un gruppo di oggetti (es. 🍎🍎🍎); si tocca, tra gruppi di un altro oggetto, quello con la **stessa quantità**. |
| **Stesso colore** | 🎨 | Viene mostrato un pallino colorato (es. 🔴); si tocca, tra le opzioni, l'oggetto dello **stesso colore** (🍓). |
| **Memoria lampo** | 🧠 | Alcuni oggetti appaiono per qualche secondo 👀, poi si coprono con ❓; si tocca, tra le opzioni, l'oggetto che **c'era**. |
| **Memo delle coppie** | 🃏 | Il memo classico: carte coperte, se ne girano due alla volta finché si trovano **tutte le coppie**. Ogni tabellone concede tanti errori quante sono le sue coppie (tessere ÷ 2), azzerati a ogni nuovo tabellone. |
| **Ripeti il ritmo** | 🥁 | I tamburi si illuminano in sequenza 👀; poi si ripete la sequenza toccandoli **nello stesso ordine** 👆. Un tocco sbagliato costa una vita. |
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
│   │   ├── models.py           # Parent, ChildProfile, GameSession, ActivityStat
│   │   ├── schemas.py          # schemi Pydantic
│   │   ├── security.py         # hashing password (PBKDF2) + token firmati
│   │   ├── routers/            # auth, profiles, games (+ /games/difficulty)
│   │   └── games/              # ← motore giochi estensibile
│   │       ├── base.py         # Game / ChoiceGame + generate() a batch di livello
│   │       ├── levels.py       # livelli, moltiplicatori e bonus Fibonacci
│   │       ├── difficulty.py   # modello di difficoltà (prior + calibrazione)
│   │       ├── registry.py     # scoperta automatica del catalogo + validazione
│   │       ├── planner.py      # ordine della partita (facile → difficile + riproposte)
│   │       └── catalog/        # ← un file (o cartella) per gioco: plug-in
│   │           ├── README.md   # la ricetta per aggiungere un gioco
│   │           ├── sequence.py
│   │           ├── odd_one_out.py
│   │           ├── pairs.py
│   │           ├── count.py
│   │           ├── color.py
│   │           ├── memory.py
│   │           ├── memo.py
│   │           ├── simon.py
│   │           ├── maze.py
│   │           └── entangled/  # gioco avanzato "a cartella": game.py + renderer.js + logic.js
│   └── tests/test_api.py
├── frontend/                    # HTML/CSS/JS vanilla, zero build step
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── api.js              # client REST + token
│       ├── ui.js               # helper DOM, transizioni, confetti
│       ├── sound.js            # effetti sonori Web Audio + toggle 🔊/🔇
│       ├── levels.js           # regole di livello (specchio di levels.py)
│       ├── engine.js           # motore: timer, cuori, livelli, punteggio
│       ├── app.js              # schermate e orchestrazione della partita
│       └── games/
│           ├── choice.js       # renderer per sequenza + intruso + coppie + conta + colore
│           ├── memory.js       # renderer memoria (sbircia → maschera → scelta)
│           ├── memo.js         # renderer memo (carte coperte, trova le coppie)
│           ├── simon.js        # renderer ritmo (guarda 👀 → ripeti 👆)
│           └── maze.js         # renderer labirinto
└── run.sh
```

**Il backend genera i giochi in Python** e li serve al frontend; il frontend li
disegna e li fa giocare. Alla fine invia le risposte: il server ricalcola in
modo autorevole il punteggio dei giochi a scelta e del ritmo (per labirinto e
memo il risultato è riportato dal client, essendo un gioco per bambini senza
incentivo a barare).

## ➕ Aggiungere un gioco

I giochi sono **plug-in**: tutto ciò che sta in `backend/app/games/catalog/`
(un file o una cartella per gioco) viene scoperto e validato automaticamente
all'avvio — niente da registrare a mano, nessuna lista da aggiornare. La
ricetta completa è in [`backend/app/games/catalog/README.md`](backend/app/games/catalog/README.md);
in breve:

1. **Backend** — crea `catalog/mio_gioco.py`. Definisci i **bucket di
   difficoltà** (la firma dei parametri di generazione → difficoltà) e come si
   costruisce una micro-attività per un bucket; `generate()` è ereditato e
   produce da solo i batch per i 10 livelli (livello → bucket più vicino).

   ```python
   from ..base import ChoiceGame

   class MioGioco(ChoiceGame):
       key = "mio"; name = "Il mio gioco"; icon = "🎲"; color = "#9B59B6"

       def difficulty_buckets(self):
           # bucket (parametri) -> difficoltà parametrica in [0, 1]
           return {"facile": 0.2, "medio": 0.5, "difficile": 0.85}

       def _one(self, bucket):
           # ...costruisci una micro-attività per quel bucket...
           return {"kind": "choice", "stimulus": [...], "options": [...], "answer": 0}

       def tutorial(self):
           return {"id": "t", "kind": "choice", "stimulus": [...], "options": [...], "answer": 0}
   ```

   I giochi che ereditano da `ChoiceGame` sono `calibrated`: ogni risposta
   aggiorna le prove per bucket (vedi sotto).

2. **Frontend** — se il gioco usa un *kind* base (`choice`, `memory`, `memo`,
   `simon`, `maze`) non serve altro: il renderer esiste già e viene caricato
   dinamicamente. Per una dinamica nuova, due strade: un nuovo kind condiviso
   in `frontend/js/games/<kind>.js`, oppure un gioco-cartella
   (`catalog/mio_gioco/`) con dentro il proprio `renderer.js`, servito dal
   backend e importato dal frontend senza toccare nient'altro. Il motore
   (timer/cuori/punteggio) è condiviso.

L'ordine della partita completa non è più una lista fissa: lo decide il
**planner** (`backend/app/games/planner.py`) a partire dalla difficoltà
calibrata — giochi facili prima, un po' di casualità, e i più facili tornano
in coda alla partita in modalità più difficile.

## 🚀 Livelli, moltiplicatori e bonus

Ogni gioco ha **10 livelli** (1 facile → 10 difficile): un livello è mappato sul
bucket di generazione con difficoltà parametrica più vicina a `(livello−1)/9`,
quindi salire di livello significa giocare micro-attività davvero più difficili.
Le regole (implementate in `backend/app/games/levels.py` e specchiate in
`frontend/js/levels.js`) sono:

- **Punti per risposta esatta**: `⌊10 × 1,5^(livello−1)⌋` → 10, 15, 22, 33, 50,
  75, 113, 170, 256, 384.
- **Passaggio di livello**: i punti guadagnati *mentre si è a un livello* si
  accumulano; alla soglia (il valore di **3 risposte esatte** a quel livello) si
  sale. Il motore mostra un **banner 🚀 con il nuovo livello** e aggiunge
  **+5 secondi** al timer (il banner non consuma tempo di gioco).
- **Ripresa dal livello migliore**: il livello massimo raggiunto è salvato per
  bambino e per gioco (`models.GameLevel`); la partita successiva allo stesso
  gioco riparte da lì. Una partita andata male non abbassa mai il livello
  salvato.
- **Bonus Fibonacci sulle serie**: risposte esatte consecutive danno punti
  bonus. La 3ª di fila vale **+1**; poi il bonus scatta a ogni serie pari a
  `3 + fib` (fib = 1, 2, 3, 5, 8, 13, …) e vale `indice + 1`: serie di
  3, 4, 5, 6, 8, 11, 16 → **+1, +1, +2, +3, +4, +5, +6**. Un errore azzera la
  serie (un'attività lasciata a metà no).

Il frontend applica le regole in tempo reale (HUD con chip 🚀, banner, secondi
bonus); alla fine il server **rigioca i risultati nell'ordine in cui sono stati
dati** con le stesse regole, così punteggio e livello finale restano autorevoli.

## 🎚️ Difficoltà procedurale e calibrata

I quiz sono generati **proceduralmente** a partire da un insieme di **bucket**:
un bucket è la firma dei parametri di creazione, con una difficoltà *parametrica*
in `[0, 1]`. Ogni gioco espone `difficulty_buckets()`; `generate(start_level)`
emette un batch di micro-attività per ogni livello (bucket più vicino alla
difficoltà target del livello), così ogni micro-attività porta con sé il proprio
`level`, `bucket` e `difficulty`.

Quanto la generazione è procedurale dipende dal gioco:

| Gioco | Procedurale? | Parametri che guidano la difficoltà |
|-------|--------------|-------------------------------------|
| **Sequenza** | ✅ pieno | tipo di motivo (`AB`…`ABCD`), n. opzioni |
| **Intruso** | ✅ pieno | vicinanza tra categorie (near/far), n. opzioni (4/6) |
| **Cosa va insieme?** | 🟡 parziale | coppie curate a mano, ma distrattori near/far e n. opzioni generati |
| **Conta e abbina** | ✅ pieno | ampiezza del conteggio (2–3 a colpo d'occhio / 4–6 da contare), quantità sbagliate vicine (±1) o lontane |
| **Stesso colore** | 🟡 parziale | oggetti curati a mano per colore, ma distrattori di colori vicini/lontani e n. opzioni generati |
| **Memoria lampo** | ✅ pieno | n. oggetti da ricordare (2–4, con tempo di visione proporzionale), distrattori near/far |
| **Memo delle coppie** | ✅ pieno | n. di coppie sul tabellone (2–4) |
| **Ripeti il ritmo** | ✅ pieno | lunghezza della sequenza (2–5), n. di tamburi (3/4) |
| **Labirinto** | ✅ pieno | dimensione della griglia (→ lunghezza percorso e vicoli ciechi) |

**Score di difficoltà calibrato sulle prove.** Ogni risposta aggiorna, per
bucket, i contatori `attempts`/`failures` (`models.ActivityStat`). Lo score
finale mescola il **prior parametrico** con il **tasso di errore osservato**
tramite shrinkage bayesiano (`games/difficulty.py::blend`): con poche prove
resta vicino al prior, con molte prove converge al dato reale. Quindi lo score è
**legato ai parametri di generazione** e si affina man mano che i bambini giocano.

Analytics disponibili su `GET /api/games/difficulty` (score per gioco e per
bucket); il menu mostra la difficoltà come 🔥 sulle card. Labirinto e memo non
hanno un segnale pulito di successo/fallimento per attività, quindi restano
*solo* parametrici (`calibrated = False`); i giochi a scelta e il ritmo (dove
la sequenza ribattuta è giusta o sbagliata) sono calibrati.

## ⚙️ Scelte e assunzioni (facili da cambiare)

- **"Al terzo errore la partita finisce"**: il terzo errore in un gioco termina
  l'**intera partita** (non solo il gioco corrente). La schermata finale mostra
  comunque le stelle guadagnate. Vedi il `break` in `runGames()`
  (`frontend/js/app.js`) su `result.reason === "errors"`.
- **Quiz per gioco / timer**: `PAPPARAPA_QUIZZES_PER_GAME` (default 5, in
  `backend/app/config.py`). Con un valore > 0 il conto alla rovescia sparisce e
  ogni gioco termina dopo quel numero di quiz; impostalo a `0` per tornare alla
  modalità a tempo (`timed` e `duration_seconds` in `games/*.py`, default 15s
  con barra del tempo).
- **Online in futuro**: per ora gira in locale con SQLite. Per il deploy online
  basterà puntare `PAPPARAPA_DATABASE_URL` a un DB gestito (es. Postgres),
  impostare un `PAPPARAPA_SECRET_KEY` robusto e servire dietro HTTPS.
- **Autenticazione**: account genitore con email/password (hash PBKDF2, token
  firmati HMAC, stateless). Nessun dato del bambino oltre nome e avatar.
- **Punti per attività**: `PAPPARAPA_POINTS` (default 10).
- **Configurazione** via variabili d'ambiente: `PAPPARAPA_DATABASE_URL`,
  `PAPPARAPA_SECRET_KEY` (cambiala in produzione!), `PAPPARAPA_TOKEN_TTL`,
  `PAPPARAPA_QUIZZES_PER_GAME`.
