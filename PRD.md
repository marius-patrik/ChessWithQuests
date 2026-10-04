# ChessWithQuests — Product Requirements Document

**Status:** the specification the product is measured against. Implementation state
is tracked in `SCRATCHPAD.md` section 4, one entry per planned pull request.
**Version:** 1.1

Planning material — current state, work streams, risks, acceptance criteria and
the decision log — lives in `SCRATCHPAD.md`. This document states only what the
product is and requires.

---

## 1. What the product is

A desktop board game engine and application in Python, built as an MVC
application, in which **the configuration is the product**. A stock 8×8 game
with the standard pieces is one configuration among many: before a game starts,
a player chooses the board, the starting position, every piece's movement, which
rules are in force, the quests in play, and the time controls.

Two games ship with the engine:

1. **Chess** — orthodox chess, which is the default configuration.
2. **Checkers** — English draughts, which shares the engine and changes no
   engine code.

The second exists to demonstrate the abstraction. If checkers needs an engine
change that chess did not, the abstraction is wrong — so building it is also a
test of the engine's generality.

## 2. Users and what they need

| User | Need |
|---|---|
| **The player** | Configure a variant quickly, then play it without friction: see the board, the turn, both clocks, what has been captured, and what is still to do |
| **The grader** | See an object model that conforms to the supplied Czech architecture diagram, with every deviation declared and justified |
| **The maintainer** | Behaviour covered by tests that exercise real code paths, not tests that restate the rulebook |

## 3. Constraints

Three things are fixed and are not up for debate.

**Already covered by `AGENTS.md`, which is what governs — this document does not
restate them:** object-model conformance (Rule 3), language (Rule 4), delivery
(Rule 7) and the pull-request review trail (Rule 11).

**Not covered by `AGENTS.md`, stated here:** the three below.

### 3.1 Libraries

**Standard library plus `tkinter` only. No third-party runtime dependency. No
chess library.**

- Notation, position encoding and all coordinate conversion are hand-rolled and
  stay hand-rolled. `python-chess` is not used.
- `tkinter` is the GUI toolkit and the only one. No PyQt, PySide, wxPython,
  Kivy, pygame or webview shell.
- `tkinter` is standard library and adds no dependency, but it is absent from
  some Linux Python distributions unless `python3-tk` is installed separately.
- Development tooling (`pytest`, `black`, `properdocs`, `mkdocstrings`) is exempt
  and never ships.

### 3.2 Tests

Tests exercise **code invariants** and **feature flow**. Tests do not assert on
rules, rule text, workflow YAML, notes content, README content or any other
repository metadata, and a test that would still pass if the product were
deleted does not belong in the suite.

Two whole categories of test are therefore wrong and must not be replaced like
for like:

- **Import smoke tests.** `importlib.import_module(name) is not None` proves a
  module parses. It proves nothing about behaviour and is deleted outright
  rather than kept in a reduced form.
- **Metadata assertions.** Tests that open `AGENTS.md`, workflow YAML, `notes/`
  or `README.md` and assert substrings police the rulebook, not the product.

The tests that survive drive real behaviour: a move is played and its effect
asserted, a rule is exercised and its outcome asserted, an invariant such as "no
third-party import anywhere under the project source" is asserted against the
code itself.

### 3.3 Execution of authored code

The application loads and runs Python the player writes in the rule and quest
editors. This is a deliberate property of the product, not an accident, and it
is bounded on purpose: code loads **only** from within the variant directory
being edited, never from an arbitrary path, an environment variable or user
input elsewhere. The editor validates before the code is allowed to join the
configuration, so a syntax error is caught in the editor rather than at game
start.

## 4. The configuration pattern

One pattern applies to the whole engine, and the settings screen reuses it
everywhere.

**Every configurable type declares its fields. The view renders them.**

```python
Field(name, kind, label, default, ...)
```

A configurable type declares its fields by a method named `value_fields()`, except
a `Quest`, which declares `parameters()`, and a clock, which `model/game/clock_fields.py`
describes by asking what the clock object holds. `Field` is the declaration type.

| Configurable | Declares |
|---|---|
| `Board` | rows, columns, placement |
| `Piece` | name, symbols, movement vectors, attack vectors, jump flag, kind, optional FEN character |
| A clock | initial time, increment |
| `Rule` subclass | its own value fields; `enabled` is added by the framework |
| `Quest` subclass | its `parameters()`; `name`, `description` and `reward` are added by the framework |

**Data-driven things are forms assembled from the declaration. Code-driven logic
is edited as code.** There is one form renderer, so adding a field kind is one
widget and every surface inherits it.

## 5. Naming requirements

Czech aliases required, English canonical, no diacritics:

| Diagram | Canonical | Czech alias |
|---|---|---|
| `Figurka` | `Piece` | `Figurka` |
| `Pěšák` | `Pawn` | `Pesak` |
| `Věž` | `Rook` | `Vez` |
| `Kůň` | `Knight` | `Kun` |
| `Střelec` | `Bishop` | `Strelec` |
| `Dáma` | `Queen` | `Dama` |
| `Král` | `King` | `Kral` |
| `HerníPlocha` | `Board` | `HerniPlocha` |
| `Tah` | `Move` | `Tah` |
| `Hrac` | `Player` | `Hrac` |
| `RevizorTahu` | `MoveValidator` | `RevizorTahu` |
| `Uzivatel` | `User` | `Uzivatel` |
| `Kwest` | `Quest` | `Kwest` |
| `HracView` | `PlayerView` | `HracView` |
| `HracGameView` | `PlayerGameView` | `HracGameView` |

`Knight` is the canonical name for the L-shaped jumping piece, not `Horse`;
`Kun` is its Czech alias. `Tower` is not a name this project uses and has no
counterpart in the diagram.

## 6. Repository layout

The package sits at the repository root. There is no `src/` directory.

```
controller/  model/  view/        the engine
model/        the parent classes a configuration is written against,
              plus the machinery every configuration shares
games/
  chess/      the default configuration, shipped
  checkers/   the second configuration, shipped
logs/         game logs, configurable, git-ignored
```

**Inside a configuration directory:**

```
games/chess/
  board.py      rows, columns, starting placement — one board per game
  pieces/       one file per piece: identity, symbols, vectors
  rules/        one file per rule: logic and configuration
  quests/       one file per quest: logic and parameters   ← see below
  clocks/       clock configuration
```

**`quests/` holds no quest files in either shipped configuration.** The twenty
quest classes live in `model/game/quests.py` and a configuration instantiates them:
`build_quests()` is declared in `games/chess/__init__.py`, and
`games/chess/quests/__init__.py` is a single docstring line and nothing else.
`games/checkers/quests/__init__.py` declares its own `build_quests()` and its
directory holds no quest file either. This is a recorded departure from the line
above, in `notes/object_model.md` §22, and it is the reason the line above is
stated here rather than quietly dropped.

Everything in a configuration is a Python file. It could not all be data,
because rules and quests carry logic, and one language avoids a format split
and the `tomllib` availability problem on Python 3.10.

**A configuration is a folder that can be copied.** `cp -r games/chess
games/house`, change what differs, and a new variant exists. Duplication is
the extension mechanism: to change the board, duplicate the configuration and change
the board. One game runs one board.

`model/` keeps the parent classes — `Piece`, `Rule`, `Quest`, `Board` — and the
machinery every configuration needs, such as the move, the validator and the game
manager. Only configuration-specific implementations live in `games/`. **There is
no `Clock` class.** `notes/object_model.md` §13 registers one as the intention and
§20 records that it is unbuilt; both shipped clocks derive from nothing, and
`model/game/clock_fields.py` describes one by asking what it holds.

## 7. Functional requirements

### 7.1 Configurable data

| ID | Requirement |
|---|---|
| FR-1 | Board dimensions are configurable in rows and columns. |
| FR-2 | The starting position is either the shipped one or edited square by square. |
| FR-3 | A piece declares a name, a white symbol, a black symbol, movement vectors, attack vectors, a jump flag and a `kind` label. A piece may be added to the palette and placed on the board. |
| FR-4 | Symbols are **unicode chess glyphs declared as data**. The board renderer and the notation writer hold no knowledge of piece types; both read what the piece declares. |
| FR-5 | A piece may additionally declare an optional FEN character. Without one it has no FEN representation. |
| FR-6 | Clocks declare an initial time and an increment. |
| FR-7 | A game runs under exactly one configuration and exactly one board. |

### 7.2 Rules — the code-driven layer

| ID | Requirement |
|---|---|
| FR-8 | A `Rule` is the parent class for game logic. It carries a configured `value` and per-game `state`, and implements five hooks, each with a permissive default: `permits_move(position, move) -> bool`, `available_moves(position, piece) -> Iterable[Move]`, `outcome(position) -> Optional[Result]`, `on_move_made(position, move) -> None`, and `status(position) -> Optional[str]`. |
| FR-9 | **Four of the five hooks are exhaustive for turn-based game logic**, which can only forbid a move or end the game: `permits_move` and `available_moves` cover forbidding a move, `outcome` covers ending the game, and `on_move_made` carries the bookkeeping the other three depend on. The fifth, `status`, is **display rather than logic** — it reports something worth showing, such as `Check`, while the game continues. |
| FR-10 | **No rule owns behaviour.** The validator asks and rules answer: a rule may permit or forbid, never cause; a rule may propose an outcome, never impose one. |
| FR-11 | An outcome is a `Result` carrying a kind (win, loss, draw), a **precedence**, and an optional winner. Decisive outcomes outrank draws; equal precedence resolves by a declared order. |
| FR-12 | A rule's configured `value` is persisted. Its runtime `state` — counters, history — resets each game and is never persisted. |
| FR-13 | A move may consist of **several hops**. A capture chain in checkers is one move the player makes, not several. |
| FR-14 | No piece type is special to the engine. Whether a position has a king is a rule, not a lookup by type name. |
| FR-15 | Board size is not restricted to 8×8. Rank-relative rules are **generalised, not disabled**: the home rank and the castling and knight-forward files are derived from the configured board. |
| FR-16 | Every orthodox rule in `notes/chess_rules.md` is expressible in those hooks: castling, en passant, promotion, check, checkmate, stalemate, insufficient material, the fifty-move rule, threefold repetition, mutual-agreement draw, loss on time only where the opponent retains mating material, and the confinement of each bishop to the shade of square it started on. |
| FR-17 | Logic beyond any shipped set is expressible without extending the engine: a piece that may move to any square satisfies `available_moves`; a piece that must capture if able satisfies `permits_move`; a game that ends when a named piece is lost satisfies `outcome`. |

### 7.3 Quests — also code-driven

| ID | Requirement |
|---|---|
| FR-18 | A `Quest` is a parent class with subclasses for the built-in quests, following the same pattern as `Rule`. Its `validate() -> bool` takes no arguments, exactly as the reference diagram draws it. |
| FR-19 | There is no separate condition class. A quest carries its own logic; the pattern is identical to `Rule`'s. |
| FR-20 | A quest declares `name`, `description`, a `reward`, and its `parameters()`, which is what the settings form asks the player for. |
| FR-21 | Every quest declares a **`when`**: `after_move` or `at_game_end`. |
| FR-22 | A quest reports **progress** as current and target, not only a boolean, so a card can render `3/5`. |
| FR-23 | **Quest scope is split explicitly.** Quests in play for the current game are held by the quest manager. Quests a user has completed are held by the user. |
| FR-24 | Total experience is **derived** from the quests a user has completed, so the user type gains no new field. |

### 7.4 Configurations

| ID | Requirement |
|---|---|
| FR-25 | A configuration is a directory under `games/` holding board, pieces, rules, quests and clocks. |
| FR-26 | `chess` ships as the default: 8×8, the six standard pieces, every orthodox rule at its orthodox value, and default clocks. Playing orthodox chess requires no configuration. |
| FR-27 | The default configuration cannot be edited or deleted. A variant starts by duplicating it. |
| FR-28 | Configurations can be created, renamed, duplicated, edited and deleted. |
| FR-29 | Configurations persist as directories and survive a restart without an account. |

### 7.5 Settings surface

| ID | Requirement |
|---|---|
| FR-30 | A selector in the corner chooses **which configuration is being edited**. It appears in settings only. |
| FR-31 | Below it are sections, one per configurable surface: **Board, Pieces, Rules, Quests, Clocks**. |
| FR-32 | **All data-based configuration is form-exposed**, assembled from each type's declaration by one renderer. |
| FR-33 | The Rules and Quests sections offer a code editor for authoring logic, which writes into the configuration directory. |
| FR-34 | The editor validates before the code may join the configuration, reporting errors in the editor rather than at game start. |
| FR-35 | Settings can be saved, reset to the shipped defaults, or cancelled. |

### 7.6 Game start and view

| ID | Requirement |
|---|---|
| FR-36 | Starting a game presents a modal offering a **configuration selector**, a **Settings** button and a **Start** button. |
| FR-37 | The board renders with coordinates, symbols, the active player's squares highlighted, and legal-move highlights on selection. |
| FR-38 | Each player panel shows identity, clock, and captured and lost pieces. |
| FR-39 | The turn is indicated. |
| FR-40 | Move history is visible. |
| FR-41 | Status and alerts appear in a footer. |
| FR-42 | Quests appear as cards showing progress and reward. |

### 7.7 Notation and export

The reference diagram is the specification for this area. The operation
compartment of the **`ChessNotationWriter`** box enumerates the formats — *letter*,
*PGN*, *FEN*, *Field - Field - Extra*, *Stenographic* (standard or custom
compression) — plus **the game transcript**, described as a single parameter.

**All of them are implemented.** Nothing in this section is optional.

The diagram's `export writers` box is a separate, near-empty box holding one
field. It does **not** enumerate the formats, and **no edge in the diagram
connects any writer to any other writer or to that box**. `Extends` in the
diagram is a legend label on a free-standing line beside the piece row, not a
relationship. Deriving one class per format from a base class is therefore a
deviation in its own right — see `notes/object_model.md` section 7.

| ID | Requirement |
|---|---|
| FR-43 | Export is one class per format, extending a base exporter named `ExportWriter`, living in the configuration that uses it. There is no format switch and no format-name string anywhere in the engine. |
| FR-44 | *Letter* — the move is rendered in algebraic notation with piece letters, capture markers, promotion and castling notation. |
| FR-45 | *PGN* — real PGN: a seven-tag roster **derived from the game** (event, site, date, round, both players, result), and movetext in Standard Algebraic Notation, including piece disambiguation, castling notation, promotion, and check and mate suffixes. |
| FR-46 | *FEN* — all six fields are **computed from the game state**: placement, side to move, castling rights, en passant square, halfmove clock and fullmove number. No field is hard-coded. |
| FR-47 | *FEN* round-trips: import a position, build it, export it, obtain the identical string. Asserted for the start position, a mid-game position carrying both castling rights, and one carrying an en passant square. |
| FR-48 | *Field - Field - Extra* — the game transcript header, derived from real state. Player names come from the users playing, the result from the game, the date from the game. No placeholder strings. |
| FR-49 | *Stenographic* — the transcript in stenographic form, with compression that is either a standard choice or a configured one, drawn from the standard library codecs only. |
| FR-50 | *The game transcript* — every move is recorded and readable, independently of any export format. |
| FR-51 | A format that belongs to one game ships with that game. FEN and PGN are chess formats and therefore live in `games/chess/export/`; a game with no FEN representation has no FEN exporter, because the structure says so rather than a capability check. |
| FR-52 | **FEN import exists as well as export**, because the round-trip requirement needs a reader. The diagram defines only writers, so a reader is a recorded deviation. |

### 7.8 Games shipped

| ID | Requirement |
|---|---|
| FR-53 | `games/chess/` is a complete, correct orthodox chess configuration. |
| FR-54 | `games/checkers/` is a complete, correct English draughts configuration: twelve pieces a side, men moving one square forward diagonally, kings stepping one square diagonally in any direction, **mandatory capture including chains**, promotion to king on reaching the far rank, and a win by immobilisation or by losing all pieces. **What ships is WCDF article 1.17, 1.20, 1.21 and 1.32**, and `notes/object_model.md` §21 records the five places where this did not, all now closed: the king slides where the rulebook steps (one number, `max_steps`), the forty-move count defaulted to 100 plies where the rulebook says 80, there was no threefold repetition (rule 1.32.1), a sufficient-material draw ended two-kings-against-one while it was still winnable, and `LimitedKingsRule` was in force. Two variants remain declared and inert: `LimitedKingsRule` at a side's full complement, and `CaptureRule` with its maximum-capture restriction off, which rule 1.20 requires ("may select any one that they wish, not necessarily that which gains the most pieces"). One divergence remains on purpose: rule 1.32.1 is a *claim* to a referee and the engine proposes the draw itself. Planned PR 17 still owns the exporters, of which there are none. |
| FR-55 | Adding `games/checkers/` requires **no engine change**. If it does, the abstraction is wrong — and that is the point of shipping it. |

### 7.9 Application

| ID | Requirement |
|---|---|
| FR-56 | The game log directory is **configurable**. It defaults to `logs/` at the repository root, is created on demand, and is git-ignored. |
| FR-57 | The package is installable and declares its metadata and runtime dependencies, of which there are none beyond the standard library. |
| FR-58 | The application starts from a documented entry point and a complete game can be played to a result. |
| FR-59 | The entry point is a module the packaging declares, so `python -m <entrypoint>` starts a window. |

### 7.10 Diagram surface

Every class and member the diagram defines is listed here with the requirement
that delivers it. Nothing in the diagram is left without coverage, and anything
this project adds beyond the diagram is registered in `notes/object_model.md`.

| Diagram member | Delivered by |
|---|---|
| `HerníPlocha` · `rozmery`, `herni_deska`, `vyhozene_figurky_b`, `vyhozene_figurky_c` | FR-1, FR-2 |
| `HerníPlocha` · `vrat_obsah`, `posun_figurky`, `nahrad_figurku` | FR-37, FR-15, FR-16 |
| `Figurka` · `název`, `barva(tým)`, `vektory`, `vektory_utoku` | FR-3, FR-4, FR-5 |
| `Pěšák` `Věž` `Kůň` `Král` `Dáma` `Střelec` | FR-3 |
| `Hrac` · `barva`, `uzivatel`, `getEloRating` | FR-60 |
| `Tah` · `vychozi pozice`, `cilova pozice`, `figurka`, `typ tahu` | FR-15, FR-16, FR-52 |
| `Tah` · `over platnost()`, `proved tah()` | FR-15 |
| `RevizorTahu` · `herni_plocha`, `tah` | FR-15 |
| `RevizorTahu` · `simulate_Move()`, `check_Šach()`, `check_Mat`, `check_Pat` | FR-8, FR-16, FR-61 |
| `GameManager` · `plocha`, `aktivni_hrac`, `hraci`, `aktualni_tah`, `casovac`, `game_logger`, `revizor_tahu` | FR-62 |
| `GameManager` · `zacni_tah()`, `mozne_tahy()`, `zrus_tah()`, `uloz_log()`, `get_stav()` | FR-62 |
| `GameManager` · `najdi_uzivatele(id)` | FR-60 |
| `Timer` · `cas_hrac`, `nuluj_cas()`, `pocitej_cas()` | FR-6, FR-63 |
| `GameLogger` · `soubor`, `uloz_tah()`, `vytvor_soubor()` | FR-50, FR-64 |
| `Uzivatel` · `uzivatelske_jmeno`, `jmeno`, `email`, `elo`, `splnene_kwesty`, `pridej_quest()` | FR-60, FR-24 |
| `User Manager` · `Id_uzivatele`, `log_uzivatelu`, `historie_uzivatele`, `proveď_tah()` | FR-60 |
| `Quest` · `nazev`, `popis`, `validate()` | FR-18, FR-20 |
| `QuestManager` · `field`, `method(type): type` | FR-23. **`QuestManager` exists** (`model/misc/quest_manager.py`) but holds **neither** drawn member — see `notes/object_model.md` §23 |
| `ChessNotationWriter` · format list, `item` | FR-43 to FR-52. **`item: attribute` is drawn but no member named `item` exists** in `ChessNotationWriter` (`model/misc/export_writers.py`) — see `notes/object_model.md` §23 |
| `MetadataWriter` · `method(type): type` | FR-48. **Drawn, and no `method` member exists** in `MetadataWriter` (`model/misc/metadata.py`) — see `notes/object_model.md` §23 |
| `export writers` · `field` | FR-43 — `ExportWriter.field` is declared at `model/misc/export_writers.py:46` |
| `GameManagerController` · `vyber_pole()` | FR-65 |
| `GameVeiw` · `controller`, `aktualizuj_plochu()` | FR-37, FR-66. The diagram spells the class `GameVeiw`; no `GameView` class exists — `notes/object_model.md` section 15 |
| `HracGameView` · `controller`, `akutalizuj_hrace()` | FR-38, FR-67 |
| `HracView` | FR-38, FR-67 |

### 7.11 Requirements added to close gaps in diagram coverage

| ID | Requirement |
|---|---|
| FR-60 | A user has a username, display name, email and an ELO rating, is registered and looked up by identifier, is linked to the player it controls, and the player's rating is readable from that link. The user directory records its users, its action log and its history. |
| FR-61 | The validator's four drawn operations are preserved. `simulate_Move()` returns the moves available to the active player; `check` reports whether the royal piece is attacked; checkmate and stalemate are reported as outcomes through `Result`. The royal piece is identified by whatever the configuration declares, never by a type name. |
| FR-62 | The game manager holds the board, the active player, the players, the current move, the clock, the logger and the validator, and exposes starting a turn, listing available moves, cancelling a move, writing the log, and reporting the game state. |
| FR-63 | A clock holds per-player time, resets, and counts down for the given player. |
| FR-64 | A log creates its file on demand, records each move with its move type, and exposes the recorded moves. |
| FR-65 | The controller selects a square and dispatches it to the game manager. |
| FR-66 | The game view refreshes the board when the controller reports a change. |
| FR-67 | The player view refreshes that player when the controller reports a change. |
