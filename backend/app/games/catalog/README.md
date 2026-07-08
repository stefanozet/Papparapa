# Catalogo dei giochi

Ogni gioco è un **plug-in**: un modulo (`mio_gioco.py`) o una cartella
(`mio_gioco/`) dentro questa directory. All'avvio il registry
(`../registry.py`) importa tutto ciò che trova qui, raccoglie le sottoclassi
concrete di `Game` e le valida — niente liste da aggiornare, niente import da
aggiungere a mano. I nomi che iniziano con `_` vengono ignorati (utile per
moduli di supporto condivisi).

## La firma di un gioco

```python
from ..base import ChoiceGame   # o Game, per dinamiche non "a scelta"

class MioGioco(ChoiceGame):
    # --- attributi obbligatori -------------------------------------------
    key = "mio"            # identificatore unico (usato da API e salvataggi)
    name = "Il mio gioco"  # nome leggibile (i bambini vedono solo l'icona)
    icon = "🎲"            # emoji nel menù
    color = "#9B59B6"      # colore tema (hex)
    # kind: ereditato da ChoiceGame ("choice"); va dichiarato se diverso

    # --- attributi opzionali (default in base.py) ------------------------
    # timed = True                duration_seconds = 15
    # activities_per_level = 8    max_errors = 3
    # calibrated = False          (True se ogni risposta è un segnale pulito)

    # --- metodi obbligatori ----------------------------------------------
    def difficulty_buckets(self):
        """Firma dei parametri di generazione -> difficoltà in [0, 1]."""
        return {"facile": 0.2, "medio": 0.5, "difficile": 0.85}

    def _one(self, bucket):
        """Una micro-attività per quel bucket (solo il contenuto: kind + campi)."""
        return {"kind": "choice", "stimulus": ["🍎"], "options": ["🍎", "🐟"], "answer": 0}

    def tutorial(self):
        """Un'attività semplice per la demo animata senza parole."""
        return {"id": "t", "kind": "choice", "stimulus": ["🍎"], "options": ["🍎", "🐟"], "answer": 0}

    # validate(activity, answer) -> bool: ereditato da ChoiceGame;
    # da implementare se si eredita direttamente da Game.
```

`generate()` è ereditato: produce da solo i batch per i 10 livelli mappando
ogni livello sul bucket con difficoltà più vicina. Non serve toccarlo.

## Il rendering: kind base o renderer proprio

Il `kind` dice al frontend **come si gioca** l'attività. Due strade:

1. **Kind base** — il gioco riusa una dinamica esistente e non serve alcun
   JavaScript. I kind base sono i file di `frontend/js/games/`:

   | kind     | dinamica                                             |
   |----------|------------------------------------------------------|
   | `choice` | tocca l'opzione giusta tra N                         |
   | `memory` | come choice, ma lo stimolo si nasconde dopo `peek_ms`|
   | `memo`   | carte coperte, trova le coppie                       |
   | `simon`  | guarda la sequenza 👀, poi ripetila 👆               |
   | `maze`   | porta il topo al formaggio                           |

2. **Renderer proprio** — il gioco è una cartella e porta con sé la sua
   dinamica (esempio reale: `entangled/`):

   ```
   catalog/mio_gioco/
   ├── __init__.py      # importa (o definisce) la classe del gioco
   ├── game.py          # la sottoclasse di Game, kind a piacere (es. "mio")
   ├── renderer.js      # il renderer, servito su /api/games/mio/renderer.js
   └── logic.js         # (opzionale) altri moduli JS importati dal renderer
   ```

   Il registry rileva `renderer.js` automaticamente e il frontend lo importa
   da `renderer_url` senza che si tocchi nient'altro. Ogni altro file `.js`
   nella cartella è servito accanto al renderer, quindi `renderer.js` può
   importarlo relativamente (`import ... from "./logic.js"`).

All'avvio il registry verifica che il `kind` esista tra i base o che il gioco
abbia il suo `renderer.js`: un gioco non renderizzabile fa fallire subito
l'avvio con un errore chiaro.

## Il contratto del renderer JS

Un renderer (base o bundled) è un modulo ES che esporta due funzioni:

```js
export function renderActivity(stage, activity, ctx) { ... }
export function renderTutorial(stage, activity, onDone) { ... }
```

- `stage` — il `<div>` in cui disegnare l'attività (svuotarlo e riempirlo);
- `activity` — il dict prodotto da `_one()` lato Python (più `id`, `level`,
  `bucket`, `difficulty` aggiunti da `generate()`);
- `ctx` — il dialogo con il motore:
  - `ctx.solved(answer)` — attività risolta; `answer` viene inviata al server
    per la validazione autorevole (ometterla per i giochi client-reported);
  - `ctx.fail(answer)` — risposta sbagliata e attività chiusa (costa un cuore);
  - `ctx.loseLife()` — errore *dentro* l'attività senza chiuderla (es. urtare
    un muro nel labirinto); ritorna `true` se i cuori sono finiti;
  - `ctx.addPoints(n)` — solo per i giochi `self_scored`: aggiunge punti in
    diretta all'HUD (il server li ricalcola comunque con `score_session`);
  - `ctx.onCleanup(fn)` — registra il teardown (listener da rimuovere, timer da
    fermare): gira comunque, anche se il tempo scade a metà attività.
- `renderTutorial` mostra la demo muta e chiama `onDone()` quando ha finito.

## Giochi avanzati e punteggio proprio

Due attributi opzionali cambiano dove e come si gioca:

- `advanced = True` — il gioco appare nella pagina "🧪 Giochi avanzati" invece
  che nel menù principale, resta fuori dal piano della partita completa e il
  suo punteggio non entra nel totale ⭐ né in classifica (rimane il record
  personale nelle statistiche).
- `self_scored = True` — il gioco assegna i punti da solo (`ctx.addPoints`),
  senza cuori, livelli o bonus streak; deve fare override di
  `score_session()` per ricalcolare il punteggio in modo autorevole lato
  server (vedi `entangled/game.py` per l'esempio completo).

Un `renderer.js` bundled è servito da un URL diverso dal frontend, quindi gli
import relativi non risolvono: le utility condivise vanno importate con
percorso assoluto —

```js
import { el, clear, wait } from "/js/ui.js";
import { sfx } from "/js/sound.js";
```

(Il browser dedupica: è lo stesso modulo che usa il resto dell'app.)

## Checklist finale

1. Il file/cartella è in `catalog/` e la classe ha `key` unico.
2. `pytest` passa (i test generici coprono ogni gioco scoperto).
3. Il gioco appare nel menù e si gioca — la partita completa lo includerà da
   sola: l'ordine lo decide il planner in base alla difficoltà calibrata.
