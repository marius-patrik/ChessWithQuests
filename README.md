# ChessWithQuests

A desktop board game engine and application in Python, built as an MVC
application, in which **the configuration is the product**. Chess and English
draughts ship as two directories under `src/games/` and share one engine.

**Status: playable, incomplete.** Chess is playable from the entry point through
a tkinter window, and the settings surface is delivered. The export writers are
prototypes. `PRD.md` states what the product must be and `SCRATCHPAD.md` records
what is built, what is partial, and what is owed — one entry per planned pull
request.

## What works today

Every item below is exercised by a test in `tests/`, except where the row says
what the test actually reaches.

| Capability | Where it lives |
|---|---|
| A board of any dimensions, with bounds checking, moving, capture recording and piece replacement | `src/model/game/board.py` |
| Moves carrying a start square, a target square, a move type and an optional promotion piece, validated and executed atomically | `src/model/game/move.py` |
| Legal move generation per piece and per side, refusing any move that leaves the mover's own piece attacked | `src/model/game/validator.py` |
| Thirteen orthodox chess rules as `Rule` subclasses — castling, en passant, promotion, check, checkmate, stalemate, insufficient material, the fifty-move rule, threefold repetition, mutual agreement, flag fall, bishop colour confinement, and which piece kind is royal | `src/games/chess/rules/` |
| A rule layer of five hooks — `permits_move`, `available_moves`, `outcome`, `on_move_made`, `status` — with an outcome type carrying a kind, a precedence and a winner | `src/model/game/rule.py` |
| A configuration loaded from a directory as a package in its own right, so a copy composes its own board, pieces, rules, quests, clocks and writers | `src/model/game/configuration.py` |
| Each of a configuration's `pieces/`, `rules/`, `quests/`, `clocks/` and `export/` sections composed out of the files it holds: a piece, rule, quest, clock or notation file written into one is in force the next time that configuration is loaded, in that order by file name, and a copy gets its own. A section may declare which of its entries lead, which orders them and removes none. A file that cannot be imported refuses the load and names itself; one that declares nothing is left out and named in the settings form | `src/model/game/configuration.py`, `compose_section` |
| A clock as a parent class with subclasses, so `clocks/` is composed against a declared parent the way `rules/` is against `Rule` | `src/model/game/clock.py` |
| A full game loop from `new_game()` to a result, driving the quest manager, the user manager, the clocks, the transcript and the logger | `src/model/game/manager.py` |
| Twenty built-in quest classes, twelve judged a move at a time and eight judging the finished game | `src/model/game/quests.py` |
| English draughts: twelve pieces a side, a king that steps one square (WCDF 1.17 and 1.21), mandatory capture including chains, crowning without removal, a win by immobilisation or by losing every piece, and the rulebook's three draws (1.32) — the engine's move generator is held to the published perft counts to depth 7 and an independent counter written from the rules agrees to depth 8; those counts cannot see the king's reach, because no man crowns inside the plies they walk | `src/games/checkers/` |
| A capture chain as one move, carried by `HopMove(Move)` rather than by the engine's own `Move` | `src/games/checkers/moves.py` |
| A draughts game written as `1. 9-13 21-17 2. 5-9 17-14` — the square numbers one to thirty-two, a hyphen for a quiet move and a cross for a capture — plus a header derived from the players, the date and the outcome. **No position record**: `FEN` is refused by name, because English draughts has none | `src/games/checkers/export/`, `src/games/checkers/board.py` |
| A tkinter window: a start modal with a configuration selector, Settings and Start; the board drawn from White's side with coordinates, symbols, selection and legal-move highlights; player panels with clocks and captured pieces; the turn; a notated move history; a status footer; quest cards with progress | `src/view/` |
| A settings surface: a corner selector for which configuration is being edited, sections for Board, Pieces, Rules, Quests and Clocks built from declared fields, create/rename/duplicate/delete, and a code editor for rule and quest source that loads the configuration again on save and reports what is in force | `src/view/settings_dialog.py`, `src/view/code_editor.py`, `src/model/game/field.py` |
| Configuration copy, rename and delete, all of which refuse the default configuration | `src/model/game/configuration.py` |
| Fifteen Czech aliases, each the same object as its canonical English class | throughout; `PRD.md` section 5 lists them |
| A `python -m chesswithquests` entry point, and a package list naming both configurations and all twelve of their subpackages. **No test performs a real `pip install` into a clean environment**; `tests/test_packaging.py` resolves `games_root()`, resolves and refuses a configuration name, and runs the entry point's `--check` path and its window construction | `pyproject.toml`, `src/chesswithquests/` |

## What is partial

- **Export writes every record the formats claim.** All five of the diagram's
  formats have one writer class each — `ExportPGN`, `ExportAlgebraic`,
  `ExportMetadata`, `ExportFEN` and `ExportStenographic`, in `src/games/chess/export/`,
  and the engine keeps only the `ExportWriter` protocol. **PGN movetext is
  Standard Algebraic Notation** — read off a replay of the game, so the file that
  says which knight moved and the suffix that says check or mate are answers about
  the position and not about the move. **The algebraic record tells the two
  castles apart** — `O-O` from `O-O-O`, decided by the square the rook stands on,
  since the engine's move type for a castle is the single word `castling` and says
  no side. **FEN computes all six fields**: the
  castling rights from the two pieces and their flags, the en passant target from
  the last move, the halfmove clock as the plies since a capture or an advance
  (which is `FiftyMoveRule`'s own number — asserted equal, so there is no second
  counter), and the fullmove number from the move count. **The coordinate record
  is compressed** with a standard library codec, `zlib` by default and
  configurable, and names the codec it used. **There is no FEN reader**: the
  diagram draws writers, not readers, and `notes/object_model.md` §12's approval
  line for one has been corrected rather than acted on. `src/games/checkers/` writes
  the two formats it has — the letter notation and its own header — and has **no
  position record**, because English draughts has none to write and inventing one
  would be inventing a notation.
- **`src/games/checkers` is not WCDF English draughts.** The king flies where the
  rulebook steps one square, the fifty-move rule defaults to 100 plies where the
  rulebook says 80, there is no threefold repetition, and insufficient material
  draws two-king-against-one. Each departure is recorded in
  `notes/object_model.md` §21.
- **`src/games/checkers` plays WCDF English draughts**, having not done so until
    step, the forty-move count defaulted to 100 plies where 1.32.2 says 80, there
    two-kings-against-one while it was still winnable. One divergence is kept on
    purpose: 1.32.1 is a claim to a referee and the engine proposes the draw
    itself. `notes/object_model.md` §21 records each, and what the perft gate
    could not see.
- **`src/controller/controller.py` is not renamed** to `game_manager_controller.py` to
  match the diagram's `GameManagerController`.

## Not built yet

- No FEN import, so nothing round-trips a position.
- No keyboard-navigation guarantee for the view layer.
- No network play, and no persistence of a game in progress. Neither is in the
  reference diagram.

## Documentation and architecture

- **Generated documentation**: [ChessWithQuests Documentation](https://marius-patrik.github.io/ChessWithQuests/)
  — every page is emitted from the source docstrings at build time by
  `properdocs` with `mkdocstrings`; this file is its overview page. Nothing about
  the documentation is stored: `docs_dir` points at a generated, git-ignored
  directory and `.github/scripts/docs_hooks.py` builds the whole navigation from
  the source tree.
- **Reference architecture diagram**:
  [Draw.io diagram](https://app.diagrams.net/#G19OY7iySOQWRAZDFKy1r-7tJKG_L-_Qn8#%7B%22pageId%22%3A%22C5RBs43oDa-KdzZeNtuy%22%7D)
  — the class hierarchy and the Model-View-Controller split the object model
  follows. Every deviation from it is registered in `notes/object_model.md`.
- **Product requirements**: `PRD.md`.
- **Implementation state and remaining work**: `SCRATCHPAD.md`.
- **Notes**: `notes/chess_rules.md`, `notes/object_model.md`,
  `notes/reference_diagram.md`.

## Development

Python 3.10 or newer. The runtime uses the standard library and `tkinter`, and
nothing else; `python-chess` is banned and FEN, PGN, SAN and coordinate
conversion are hand-rolled. The tools below are development dependencies and
never ship:

```
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Everything runs from the repository root — `pyproject.toml` configures `pytest`
with `pythonpath = ["."]`, and the package is also installable with `pip install .`:

```
python -m pytest -q
python -m black --check .
python -m properdocs build --strict
```

`tkinter` needs a display. Tests stay within `tkinter.Tcl()` and `ttk.Style()`,
which work without one, or run under `xvfb-run`.

No test writes outside pytest's `tmp_path`, so the directory a suite is run from
is left as it was found. `tests/test_view.py` used to build its scratch file from
`str(tk_root)` — which is `'.'` — and left a zero-byte `some_rule.py` in whatever
directory it was invoked from, the repository included.