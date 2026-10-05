# SCRATCHPAD

**This file is the execution manual for the whole track.** An agent with no other
context should be able to read this and drive the project from its current state
to a finished, playable product. Where this file and the product requirements
disagree, the product requirements win; where this file and the architecture
notes disagree, the notes win.

- What the product is: `PRD.md`
- Object model and deviations: `notes/object_model.md`
- Chess rules baseline: `notes/chess_rules.md`
- Visual reference: `GUI_mockup.svg`
- Governing process: `AGENTS.md`

---

## 1. Non-negotiable constraints

Breaking any of these is a rejected change regardless of quality.

1. **Standard library plus `tkinter` only.** No third-party runtime dependency.
   No chess library — `python-chess` is banned. FEN, PGN, SAN and coordinate
   conversion are hand-rolled. Dev tooling (`pytest`, `black`, `properdocs`,
   `mkdocstrings`) is exempt and never ships.
2. **The reference diagram is the assignment specification.** Anything it defines
   is implemented. Anything it does not define is out of scope unless a user
   request adds it.
3. **Every deviation from the diagram is recorded** in
   `notes/object_model.md` with rationale and approval, before implementation.
4. **The engine holds no chess.** No piece-type special cases, no hard-coded
   8×8, no `getType() == "king"`. Chess is a *configuration*, not the engine.
5. **Rules and quests are the only code-driven layers**, and both use the same
   pattern: a parent class with subclasses, composed explicitly, never a
   registry. Everything else is data. Composition is explicit as well: a
   configuration's `pieces/`, `rules/`, `quests/`, `clocks/` and `export/`
   sections each compose the files their own directory holds, so the tree is the
   list and a rule, a piece, a clock or a notation is in force for having been
   written.
6. **Every change arrives as a pull request.** Nothing lands unreviewed. Do not
   merge — that is the maintainer's decision alone.
7. **Commit messages are Conventional Commits**, scoped by area: `area:model`,
   `area:view`, `area:controller`, `area:ci`, `area:docs`.
8. **A change that touches code ships with tests.** `pytest`, `black --check` and
   `properdocs build --strict` are green before any PR is opened.
9. **Czech aliases are required alongside English canonical names.** `AGENTS.md`
   Rule 4 states that all identifiers are English, which contradicts the fifteen
   Czech aliases `PRD.md` section 5 requires. The aliases are the approved
   decision, recorded in `notes/object_model.md` section 1 and re-approved on
   2026-10-02, and all fifteen now ship — six in `games/chess/pieces/` and nine
   in the engine and view modules `PRD.md` section 5 names. Planned PR 5 amends
   Rule 4 to permit them and is written on `feature/governance-rules`; the main
   stack's `AGENTS.md` has not taken it, so on the main stack alone the rule text
   and the code disagree. Merging PR 5 resolves it. No other contradiction
   between `AGENTS.md` and this plan survives.

## Where each planned pull request is tracked

| Planned PR | Issue |
|---|---|
| 1 | #127 |
| 2, 3, 6, 7 | #131 |
| 4 | #126 |
| 5 | #124 |
| 8, 9, 10, 11, 12, 13, 14, 18, 19, 20, 21 | #129 |
| 15, 16 | #125 |
| backlog | #130 |

---

## 2. Repository layout

This is the layout as it is on the main stack, not a target.

```
controller/           the MVC controller
  controller.py         GameController — square click to move
  window_controller.py  WindowController — window and clock events
model/                the parent classes and the machinery every configuration shares
  pieces/piece.py       Piece, the parent of the six chess pieces
  game/                 Board, Move, MoveValidator, GameManager, Player, Timer,
                        GameLogger, Quest, Rule, Configuration, Field, events
  game/quests.py        the twenty built-in quest classes
  users/                User, UserManager
  misc/                 export writers, metadata, algebraic re-export, QuestManager
view/                 the tkinter layer
  game_view.py          BoardView — draws the board
  player_game_view.py   PlayerGameView — the window a game is played in
  player_view.py        PlayerView — one player's panel
  quest_view.py         QuestCard, QuestList
  start_modal.py        StartModal — configuration selector, Settings, Start
  settings_dialog.py    SettingsDialog — one form over declared fields
  app.py                window assembly
games/                the shipped configurations, one directory each
  chess/                the default configuration
    board.py              rows, columns, starting placement
    pieces/               one file per piece: pawn, rook, knight, bishop, queen, king
    rules/                one file per rule
    clocks/               Fischer
    export/               algebraic coordinate conversion
    quests/               a package that declares no quest files; `build_quests()` is
                          in games/chess/__init__.py
  checkers/             the second configuration
    board.py, moves.py, pieces/, rules/, clocks/, export/, quests/
                        export/ holds the letter notation and this game's own metadata
                        header; the numbering both write in is `square_number` in
                        board.py, counted from the squares the game is played on
chesswithquests/      the entry point, `python -m chesswithquests`
logs/                 game logs, configurable, git-ignored
tests/  notes/  theme/  .github/
```

`model/` keeps the parent classes — `Piece`, `Rule`, `Quest`, `Clock`, `Board` —
and the machinery every configuration shares: the move, the validator, the game
manager, the timer, the logger, the player, the user and the notation base.
`Clock` is the configurable parent `notes/object_model.md` §13 registered as the
intention; it is built, because `clocks/` cannot be composed against a parent
class that is not there, and `model/game/clock_fields.py` still describes a clock
by asking what it holds so that a clock written in a variant is configurable
whether or not it derives from `Clock`.

**Everything in a configuration directory is a Python file.** It could not all be
data: rules and quests carry logic, so one language avoids a format split and
keeps the tree readable.

**A section is composed out of the files it holds.** `CONFIGURATION_SECTIONS` in
`model/game/configuration.py` declares which directories a configuration has and
the parent class each one composes, and `compose_section` builds one entry per
`Piece`, `Rule`, `Quest`, `Clock` or `ExportWriter` subclass the modules in that
directory declare. `build_pieces()`, `build_rules()`, `build_quests()`,
`build_clocks()` and `build_exporters()` stay declared functions in each
configuration — they hand their own section's package to the composer — and there
is no registry, no plugin loader and no scan of anything outside the section. So a
file written into `rules/` is in force, a piece written into `pieces/` is in the
catalogue, a clock in `clocks/` is offered and a notation in `export/` is
written with, each because it is a file in that directory. Order is the section's
own module first and the remaining files by name, because rule order is the
tie-break when two rules propose an outcome at once. A file that cannot be
imported refuses the load and names itself; one that declares nothing is left out
and named in `Configuration.uncomposed`, because `rules/attacks.py` is a helper
three rule files share and refusing the load over it would stop the game
starting.

**A section may declare which of its entries lead, and that orders rather than
selects.** `export/` declares `PREFERRED`, because which notation a game is saved
in is a preference rather than a fact about a directory: `default_format` takes
the first format the first writer declares and `save_log` names its file from it.
Every writer the directory holds is composed whatever the preference says, and a
writer the preference does not name is offered last; what is refused is a name in
`PREFERRED` that the directory does not declare, because a preference and a
directory that disagree is how a notation quietly stops existing.

**One section composes classes rather than instances.** `Configuration.pieces` is
a catalogue of what a board may hold, and a piece is placed with a colour and a
square, so the composed entry is the class and `CLASS_ENTRY_SECTIONS` says so.

**A configuration is a folder that can be copied.** `cp -r games/chess
games/house`, change what differs, and a variant exists. `cp -r games/checkers
games/house` works the same way. Duplication is the extension mechanism. One game
runs one board. `model/game/configuration.py` loads a loaded directory as a
package rooted at itself, and composes a section as the package it is handed
rather than as a name looked up somewhere, so a copy composes its own board,
pieces, rules, clocks and quests rather than the original's.

**One declared deviation from "one file per entry": quests.** `PRD.md` §6 promises
`quests/  one file per quest: logic and parameters`. Neither configuration keeps
quest files there. `games/chess/quests/` holds an `__init__.py` and nothing else,
and `games/chess/__init__.py` instantiates the engine's twenty quest classes as
`build_quests()`. `games/checkers/quests/__init__.py` composes its own directory —
empty — and instantiates four of them itself. The quest classes live in
`model/game/quests.py`, which a configuration instantiates, because a
configuration ships a handful of quests rather than the whole library. The
*directory* is composed, so a quest written there joins the configuration; what the
two configurations ship in it is still nothing. This is recorded as a deviation in
`notes/object_model.md` §22 and annotated in `PRD.md` §6.

---

## 3. How to read the pull-request numbers

This manual numbers **planned** pull requests 1 to 21. Those numbers are **not**
GitHub pull-request numbers, and typing one into the GitHub interface will open or
close the wrong thing. Merged pull requests in this repository run 1 to 105; the
open ones run to 155.

| Planned PR | Real pull request | Title |
|---|---|---|
| 1 | 128 | product requirements document for ChessWithQuests |
| 2 | 132 | flatten `src/` into the repository root and generate the docs tree |
| 3 | 133 | delete the tests that assert on repository metadata |
| 4 | 139 | run CI natively and drop the DarkFactory dependency |
| 5 | 140 | make the governance rules state what is now true |
| 6 | 135 | packaging, a documented entry point, and the git-ignored log directory |
| 7 | 134 | state only what the product does today |
| 8 | 136 | board generalisation — every bound comes from the board |
| 9 | 137 | Quest parent with twenty built-in quests |
| 10 | 138 | the `Rule` parent, `Result` with precedence, and configuration loading |
| 11 | 141 | the thirteen orthodox chess rules |
| 13 | 149 | the chess configuration owns its pieces and its board |
| 14 | 150 | wire the subsystems into the game loop |
| 15 | 151 | the game window, and a game you can play |

Planned PRs 12, 16, 17, 18, 19, 20 and 21 have no pull request of their own. The
work behind 12 and 17 rode in with the checkers configuration, and the review
fixes are in 155. Each planned pull request belongs to the plan issue named in the
table at the head of this file, in that issue's `Placement` section.

---

## 4. Current state

`pytest` is green. `black --check` clean. `properdocs build --strict` clean,
zero warnings.

**This section quotes no test count.** The stack is several pull requests deep and
grows as it merges, so a number written here is wrong the day after it is written.
Run `pytest -q` for the current count, and treat §4.3's dead-code sweep the same
way.

**No test is a metadata assertion.** The last one,
`tests/test_docs_and_docstrings.py::test_generated_docs_directory_is_not_tracked`,
shelled out to `git check-ignore` and asserted that a path is ignored. That is a
property of `.gitignore`, not of the product, and by `PRD.md` §3.2's own
definition it would still pass with the product deleted. It is gone, and so is
`test_docs_config_and_strict_build` beside it; §5 records both deletions and §8
item 1 says the same. What they stood in for is a workflow rather than a test:
`.github/workflows/verify-docs.yml:31` runs `properdocs build --strict`, and so
does the `docs` job of the pinned pipeline `ci.yml` calls.

What exists is a playable chess product and a working draughts engine beside it.
The whole view layer, the game-loop wiring, both configurations and the rule and
quest hierarchies are built; §4.5 records which planned pull request delivered
each of them.

### 4.1 Gaps

| Gap | Evidence |
|---|---|
| ~~**Export is the largest remaining hole — and it is now the *records*, not the mechanism.**~~ **Closed 2026-10-05.** All five of the diagram's formats are one writer class each, in `games/chess/export/`, and the engine holds only the `ExportWriter` protocol. All three of the wrong records — the three rows below — were corrected in the same change | `games/chess/export/{pgn,fen,stenographic}.py` |
| ~~**FEN writes four placeholder fields.**~~ **Closed 2026-10-05.** `return f"{board_fen} {turn} - - 0 1"` wrote the same four values whatever the game was doing. Castling rights now come from the two pieces and their flags (the same question `rules/castling.py` asks, with the kind names read out of that rule rather than written here), the en passant target from the last move, the halfmove clock from the plies since a capture or an advance — which is `FiftyMoveRule`'s own number, asserted equal so no second counter exists — and the fullmove number from the move count. `GameManager.transcript` also hands the writer the side to move, which nothing passed and which made every position with Black to move read `w` | `games/chess/export/fen.py`, `model/game/manager.py` |
| ~~**PGN movetext is not SAN.**~~ **Closed 2026-10-05.** The movetext is Standard Algebraic Notation: piece letters, `x`, the file or rank that says which identical piece moved, the file a pawn took from, `O-O`/`O-O-O` read off the rook's square, `=Q`, and `+`/`#`. SAN is a question about a position and a `Move` carries none, so the writer **replays** the game — a fresh board from its own configuration, its own copy of the rules, notified of each move as `GameManager.make_move` notifies them. Asserted against the Opera Game's published movetext, written in as a literal, and case by case | `games/chess/export/pgn.py`, `tests/test_transcript_notation.py` |
| ~~**Stenographic is a coordinate pair, not a stenographic record.**~~ **Closed 2026-10-05.** The record is compressed with a standard library codec — `STANDARD_CODECS` is `zlib`, `gzip`, `bz2` and `lzma` and nothing else — with `zlib` as the standard choice and the codec configurable per writer and per call. The bytes are written as base85 because a writer returns a `str`, and the record names the codec that produced it so `from_stenographic` can read it back. What the three sentences of the specification settle, and what was decided, is in the module docstring | `games/chess/export/stenographic.py`, `tests/test_coordinate_record.py` |
| ~~**`PRD.md` FR-52 claims a FEN import that does not exist.**~~ **Closed 2026-10-05, by amendment.** FR-52 said a reader was "directed by the user on 2026-10-02" and `notes/object_model.md` §12 recorded it. No reader exists, and the owner's rule is that the diagram is the whole specification — and the diagram draws writers. FR-47 and FR-52 are amended and §12's approval line is withdrawn. **The reader is not built** | `PRD.md` FR-47/FR-52, `notes/object_model.md` §12, §27 |
| **The draughts letter record does not write the route of a capture chain.** `ExportLetter` writes the departure square and the arrival square, which is the rulebook's own convention (FMJD Annex 1 article 8.2), but a chain of three jumps that arrives on 30 by one route and a different chain that arrives on 30 by another read alike. The disambiguating long form — every square landed on, `18x25x30` — is what `PDN` prescribes for exactly this and is **not written**. Recorded rather than fixed: a chain is one move in this engine, so the record is correct about what was played and silent about how | `games/checkers/export/letter.py`, `move_text` |
| ~~**A rule or quest file written into a configuration joined nothing.**~~ **Closed 2026-10-05.** `view/settings_dialog.py` wrote `rules/<stem>.py`, the editor validated it and reported no problems, and `games/chess/rules/__init__.py` held a literal tuple of the thirteen rules chess ships — so the file was written, checked, and never composed. No error, no warning, no rule. `rules/` and `quests/` are composed out of their own files now, in file-name order, and a file that cannot be imported refuses the load by name | `model/game/configuration.py` `compose_section`, `games/chess/rules/__init__.py`, `tests/test_section_composition.py` |
| ~~**A piece, clock or notation file written into a configuration joined nothing either.**~~ **Closed 2026-10-05.** The same defect one section over: `pieces/`, `clocks/` and `export/` were declared `None` — "composed by hand" — while `games/chess/pieces/__init__.py` held a literal `PIECES` tuple and both configurations' `build_exporters()` listed their writers out. All five sections are composed out of their own directories now, each against a parent class (`Clock` was built for it), and a section's declared preference orders its entries without removing any | `model/game/configuration.py` `CONFIGURATION_SECTIONS`, `model/game/clock.py`, `tests/test_section_composition.py` |
| ~~**`ChessNotationWriter` is still an engine class.**~~ **Closed 2026-10-05.** The class is deleted and the writers are `games/chess/export/`'s, each a file in that directory and composed from it | `notes/object_model.md` §7 |
| ~~**`ChessNotationWriter.export` is unexercised.**~~ **Closed 2026-10-05.** There is no format switch left to exercise; each writer's `export` is called in `tests/test_notation_and_writers.py`, in any spelling, and refuses a notation it does not write | `tests/test_notation_and_writers.py` |
| ~~**Two of the diagram's five formats have no writer at all.**~~ **Closed 2026-10-05.** *Letter* is `ExportAlgebraic` in `games/chess/export/algebraic.py`, declaring `Algebraic`, and *Field - Field - Extra* is `ExportMetadata` in `games/chess/export/metadata.py`. All five of the diagram's formats are one writer each | `PRD.md` FR-44, FR-48; `notes/reference_diagram.md` |
| ~~**`MetadataWriter` is still an engine class, and still PGN-shaped.**~~ **Closed 2026-10-05.** It is `games/chess/export/metadata.py`'s `ExportMetadata`, a writer like the other four; `Configuration.metadata` is how a configuration supplies one, `GameManager` builds none and writes no tag into one, and `model/misc/metadata.py` is deleted | `games/chess/export/metadata.py`, `model/game/configuration.py`, `model/game/manager.py` |
| **`games/checkers` now plays WCDF English draughts**, having not done so until 2026-10-04: the king steps (1.17, 1.21), the forty-move count is 80 plies (1.32.2), a repetition rule exists (1.32.1), and the invented insufficient-material draw is gone. One divergence is deliberate — 1.32.1 is a claim to a referee and the engine proposes the draw itself. The perft gate cannot see the king's reach: no man crowns inside the eight plies it walks | `games/checkers/pieces/king.py`, `games/checkers/rules/draws.py`, `games/checkers/rules/__init__.py` |

`pyproject.toml` **does** ship both configurations. Commit `319ed0d` added
`games.checkers` and its six subpackages to the explicit package list, so a clean
install finds chess *and* draughts. The false claim that it omitted
`games.checkers` stood in three places in this file — this table, §6's PR 6 state
line and §8's item 24a — and once in `README.md`. All four now say the opposite.

`model/game/configuration.py` also carries `copy_configuration`,
`rename_configuration` and `delete_configuration`, which refuse the default
configuration — so FR-27 and FR-28 are enforced at the data layer whether or not a
widget calls them.

### 4.2 What the game loop does

`model/game/manager.py` drives one game from `new_game()` to a `Result`. It takes
its board, pieces, rules, quests, clocks and export writers from the
`Configuration` it is given and names none of them: there is no `chess` in it and
no `checkers` in it. The six subsystems this file once described as orphaned are
constructed and driven: `UserManager` and `QuestManager` at `manager.py:84,89`,
`WindowController` by `view/app.py:42`, and `Configuration.exporters` supplies
the writers. `link_default_users` at `manager.py:113` registers a user per side
and links it to the player it controls, which is what makes a player a person
rather than a colour.

**Which layer calls which manager member, because it is not the view.**
`view/player_game_view.py` calls four manager methods — `get_state`
(`player_game_view.py:148,163,220,313`), `finish_game` (`:164`), `new_game`
(`:204`) and `charge_turn` (`:314`) — and reads the attributes `board`,
`active_player`, `players`, `result`, `game_logger`, `quest_manager` and
`move_validator`. It calls **none** of `start_turn`, `make_move`,
`get_valid_moves`, `cancel_move`, `credit_increment`, `status`, `get_result`,
`transcript` or `save_log`; an earlier revision of this file said it called ten of
them, which was wrong.

`make_move` is called from `controller/controller.py:83`, which asks
`move_validator.find_move` for the move the rules offered rather than rebuilding
one from two squares (`controller.py:70`). `start_turn` and `cancel_move` have no
caller anywhere in the source or the suite at all — §4.3 lists them, and
`controller.py:96` clears the controller's own selection instead. `get_result`,
`status`, `transcript` and `save_log` are reached from inside `manager.py` and
from tests.

### 4.3 Dead code

The inventory this section used to carry is mostly resolved. Verified gone:
`Timer.countdown`, `Player.get_color`, `Player.get_user`,
`Player.get_elo_rating`, `UserManager.find_user`, `Quest.complete`,
`Board.setup_default_board`, and the names `Tower`, `Horse` and `Controller`. The
board's starting position moved out of the engine entirely: `games/chess/board.py`
and `games/checkers/board.py` declare it.

**`GameManager.possible_moves` is not gone and must not be treated as dead.**
It is a class-body alias for `get_valid_moves` at `model/game/manager.py:190`, and
`tests/test_game_manager.py:16` calls it. An earlier revision of this file listed
it under "verified gone", which was false. The decision is to **keep the alias and
correct the record**, because deleting it means editing a test to remove a passing
assertion — and the alias costs one line and breaks no caller — while correcting
the record costs the reader nothing at all. It is kept out of the unreferenced
table below for the same reason: it *is* referenced, by
`tests/test_game_manager.py:16`. §8 item 32 and planned PR 20 carry the re-check;
this paragraph is the decision, so that re-check does not have to invent one.

Several members this section once called dead are alive and must not be touched:
`Board.dimensions` (`board.py:103,111`), `Board.captured_white`
(`board.py:57,176`, read by `move.py:165,220`), `Move.promotion_piece`
(`move.py:93,185`), `ExportWriter.field`, `GameManager.players` and
`WindowController.title`, `width` and `height`.

**`Move.captured_piece` is declared, documented and used.** It is a constructor
parameter and instance attribute of `Move` (`model/game/move.py:67` and `:47`),
written by `apply_to_board` at `:174` and read by `Board` bookkeeping, the quests
and the draughts perft walk. An earlier revision of this file said it was "no
longer declared on `Move`" and that only `HopMove` carried it. `HopMove` does
carry `captured_pieces` for a chain; it does not replace `Move.captured_piece`.
See §4.7 for what `Move` actually carries.

**How the sweep is run, so the number is reproducible.** It parses every
`.py` file under `model/`, `controller/`, `view/`, `games/` and
`chesswithquests/` with `ast`, collects every module-level `def`/`class` and
every method whose name does not begin with `_`, and then counts how often each
name occurs in the source and in `tests/`. At this commit that is **470 public
definitions (86 classes, 316 methods, 68 functions) carrying 306 distinct public
names, in 86 files**. A name shared with a member elsewhere counts as referenced,
so the result is a screen and not a verdict. **Re-run it rather than trusting
this paragraph** — an earlier revision of this file claimed "222 public
callables and methods", which no reading of the tree reproduces.

What is unreferenced by that sweep:

| Unreferenced | Note |
|---|---|
| `GameManager.start_turn` | the loop's turn entry point; nothing calls it, source or suite |
| `GameManager.cancel_move` | no caller; `controller/controller.py:96` clears the controller's own selection instead |
| `GameLogger.file_path` | a getter with no reader |
| `MoveValidator.set_board` | a setter the validator is constructed with instead |
| `field_values` (`model/game/field.py:105`) | a module-level function, not a `Field` member; no reader |
| `ResultEvent.moves_by` (`model/game/events.py:158`) | no reader |
| `QuestManager.register_quest` | no reader; the manager is populated at construction |
| `longest_chain` (`games/checkers/rules/chains.py:176`) | no reader |
| `FiftyMoveRule.reset_count` (`games/checkers/rules/draws.py:75`) | no reader |
| `_SourceLoader.create_module` (`model/game/source_validation.py:79`) | **not dead**: the import machinery calls it. Do not remove, and exclude it when re-running the sweep |

**`PlayerGameView.start_auto_refresh` is referenced** — `view/app.py:62` calls it
so the clocks advance on real time. An earlier revision of this file listed it as
unreferenced on the reasoning that "the clock ticks are driven explicitly", which
is false: `player_game_view.py:314`'s explicit `charge_turn` is a second caller,
not the only one.

**PR 20 re-checks this list and removes only what is still unreferenced.** A
member written in anticipation of a consumer that has now arrived must not be
deleted.

### 4.4 Docstring coverage

The two `Returns:` gaps this section used to record — `ExportWriter.export` and
`GameLogger.file_path` — are closed, and the `piece.py` `__main__` demo block is
gone. `tests/test_docs_and_docstrings.py` holds the invariant: every module,
class and public method under `model/`, `controller/`, `view/` and `games/` has a
docstring, and `properdocs build --strict` completes with zero warnings.

### 4.5 Delivery state of the twenty-one planned pull requests

**Thirteen** of the twenty-one are delivered in the main stack, **two** are
delivered on branches outside it, **four** are partial and **two** are not
started. **"Delivered" means the acceptance criteria are met, not that a branch
was opened.** An earlier revision of this section opened with "nine delivered in
the main stack, three outside", which its own table below contradicted; the table
said thirteen, two, three and three.

| Planned PR | Content | State | Where |
|---|---|---|---|
| 1 | PRD + SCRATCHPAD | **delivered** | main stack |
| 2 | Flatten `src/` to root, generated docs pipeline | **delivered** | main stack |
| 3 | Delete metadata-only tests, close docstring gaps, drop unused aliases | **delivered** — 51 collected tests removed, not 62; §5 | main stack |
| 4 | CI: native self-contained workflows, remove the agent workflows only | **delivered, outside the main stack** — on a branch 24 commits behind the tip; re-scoped on the main stack by #167 | `feature/native-ci-workflows` |
| 5 | Governance rules: `AGENTS.md` 1, 2, 4, 7, 9, 10, 11, 12, **13** | **delivered, outside the main stack** — on top of PR 4. Rule 13 is withdrawn on the main stack instead, tombstoned, by #167 | `feature/governance-rules` |
| 6 | Packaging, entry point, git-ignored log directory | **delivered** — including both configurations in the package list (§4.1) | main stack |
| 7 | README honesty | **delivered** in the main stack by commit `77d978c`. The stale branch rewrite is superseded and is not to be merged | main stack |
| 8 | Board generalisation | **delivered** | main stack |
| 9 | `Quest` parent with built-in subclasses | **delivered** — twenty classes, split twelve `after_move` and eight `at_game_end` | main stack |
| 10 | `Rule` parent, five hooks, configuration loading | **delivered** | main stack |
| 11 | Orthodox chess rules, removal of type coupling | **partial** — thirteen `Rule` subclasses ship, and the *hard-coded* type coupling is gone. Thirteen `getType()` call sites remain in `games/chess/rules/` across five files, and the engine still holds three in `model/game/`, plus four `hasattr` probes in `model/game/clock_fields.py`. See §7 PR 11 | main stack |
| 12 | Multi-hop moves | **delivered, as a different design from the one planned** — `Move` grew no hop sequence; `games/checkers/moves.py` declares `HopMove(Move)`, which carries the hops. See §4.7 | main stack |
| 13 | Migrate chess into `games/chess/` | **delivered** | main stack |
| 14 | Wire the orphan subsystems | **delivered** | main stack |
| 15 | View layer with the game-start modal | **delivered** — `BoardView`, `PlayerGameView`, `PlayerView`, `QuestCard`, `QuestList`, `StartModal` | main stack |
| 16 | Settings surface | **delivered** — the five sections, the corner configuration selector with create/rename/delete/duplicate, and a code editor that validates before the code joins a configuration | main stack |
| 17 | `games/checkers/` | **partial** — the board, two piece kinds, eight rules, the clock and four quests, held to the published perft counts, and **two writers**: `ExportLetter` and its own `ExportMetadata`, declared `Letter` and `Field-Field-Extra` by `build_exporters()`. There is no position record and none was invented. The game it plays is flying-kings, not WCDF English draughts; `notes/object_model.md` §21 | main stack |
| 18 | Export generalised | **delivered** — one writer class per format in `games/chess/export/`, the format switch and the `ChessNotationWriter` class deleted, the engine holding only the `ExportWriter` protocol and `tests/test_engine_holds_no_chess.py` walking `model/` to keep it that way. The item's other half closed 2026-10-05: *letter* is `ExportAlgebraic`, and the header is `ExportMetadata` supplied through `Configuration.metadata` | this branch |
| 19 | Export formats: PGN, FEN, field-field-extra, stenographic | **delivered 2026-10-05** — all five formats have a writer, the header is derived from the game with no placeholder strings, the movetext is real SAN read off a replay, FEN computes all six fields, and the coordinate record is compressed with a standard library codec and reads back. See §4.1 and `notes/object_model.md` §27 | this branch |
| 20 | Czech aliases and remaining dead code | **partial** — all fifteen aliases ship, `Knight` is canonical, `Tower`, `Horse` and `Controller` are gone. Absent: the `controller/controller.py` → `game_manager_controller.py` rename, and the dead-code re-check | main stack |
| 21 | Behavioural test coverage | **partial** — no test asserts on repository metadata any more, §4.3's list is unreferenced rather than untriaged, and §8 items 2, 6, 8 and 12 are not fully asserted | main stack |

### 4.6 The stack has grown past twenty-one

The twenty-one are the plan; the branches are the truth. Four items were added to
the main stack after the plan was written, and each is a real pull request:

| Added item | What it is | Where |
|---|---|---|
| The perft gate | Draughts move generation held to the published perft counts, and chess perft(4) corrected | `tests/test_draughts_perft.py`, `tests/test_perft.py` |
| The engine-leakage cleanup | `tests/test_engine_holds_no_chess.py`, which asserts the invariant the plan stated and the code had broken | main stack |
| The knight rename | `Horse` → `Knight`, with `Kun` as the alias and `games/chess/pieces/knight.py` as the file | main stack |
| The checkers configuration | `games/checkers/` as its own directory | main stack |

**`feature/native-ci-workflows` is not on the main stack**, and neither is
`feature/governance-rules`, which is built on it. Planned PR 4 and PR 5 therefore
exist only there, and any statement in this file about PR 4 or PR 5 describes work
a reader of the main stack cannot see. Both branches forked from `f4e1487` and are
22 to 25 commits behind this stack, so neither can be merged without a rebase —
`feature/native-ci-workflows` still carries a `src/` tree.

**`feature/readme-honesty` is superseded and is not to be merged.** Planned PR 7
was delivered in the main stack by commit `77d978c`; that rewrite states what the
product does today, and the branch forked from `f4e1487`, twenty-two commits
before this stack, predates the view layer, `games/`, the packaging and the
settings surface. Every capability claim in it is false. An earlier revision of
this file said PR 7 was "not started" and that the branch "must be superseded, not
merged" as outstanding work; the supersession has happened.

**The plan issues' labels lag their contents.** #127 (PR 1) and #129 are labelled
`In Progress`; #126 (PR 4) and #124 (PR 5) carry no status label at all, though
both are delivered on branches; #131 covers PRs 2, 3, 6 and 7, **all four of which
are delivered**. Move them to `Done` when the pull requests merge.

### 4.7 Multi-hop moves were not built as planned

Planned PR 12 says `Move` grows a sequence of hops alongside `start_pos` and
`end_pos`. **It does not.** What `Move` actually carries is declared in
`model/game/move.py:35-72` and is nine constructor parameters: `start_pos`,
`end_pos`, `piece`, `move_type`, `captured_piece`, `promotion_piece`,
`capture_from`, `companion_start` and `companion_end`.

- **`captured_piece`** — the piece this move took, recorded while the board still
  held it (`move.py:47,67`, written at `:174`). It is what a single capture
  carries; `HopMove` adds `captured_pieces` for a chain.
- **`capture_from`** — the square a taken piece stands on when it is not the
  destination, which is what makes a distant capture's victim recoverable
  (`move.py:55,69`).
- **`companion_start` / `companion_end`** — the second square pair, for a move that
  carries a piece along: a castling rook (`move.py:57,59,70,72`, applied at `:190`).

An earlier revision of this section said `Move` carries "a start, an end, a piece,
a move type and an optional promotion piece, **and nothing else**", which omitted
four members that are declared, documented and used, and said of
`Move.captured_piece` that it was "no longer declared on `Move`". Both were false;
§4.3 records the second correction and this paragraph the first.

`Applied` is **not** a member of `Move` — it is a module-level `NamedTuple` at
`model/game/move.py:21`, imported by `HopMove` — and, since 2026-10-05, by
nothing in the engine: the engine's writer was the only other reader and it is
deleted. `HopMove` adds `hops`, `captures`,
`captured_pieces` and `route`, and overrides `apply_to_board`; the engine's
`unapply_from_board` is reused verbatim, because `HopMove` returns the engine's own
`Applied` record.

This is the better outcome — nothing under `model/`, `controller/` or `view/`
grows a draughts-shaped member, and `notes/object_model.md` section 11 records
it — and the plan is what is wrong. **§11 was amended on 2026-10-02 and does say a
`Move` subclass carries the hops.** `games/checkers/moves.py`'s module docstring
still says section 11 "should be amended… it is not", which was true when it was
written and is now stale; the correction lives in the code, not in this file.

---

## 5. Test strategy

Current: every test in the suite is behavioural **except one**, named below.
Target: behaviour-only, and the suite is one test short of it.

**The metadata assertions are gone, and PR 3 removed fifty-one of them.** At
commit `4e7f270` collection went from **137 to 86**, so 51 collected tests were
removed. Eight files were **deleted outright** — `tests/test_workflow_rules.py`
(15 `def test_`), `test_auto_format_workflow.py` (2), `test_claude_symlink.py` (3),
`test_chess_rules_notes.py` (1), `test_object_model_notes.py` (1),
`test_readme.py` (1), `test_reference_diagram_notes.py` (1) and `test_structure.py`
(1) — which is **25 `def test_` definitions**; the 51 figure is larger because six
of them were parametrised. One further file, `tests/test_user_manager.py`, had a
single assertion rewritten from `manager.find_user(42)` to `manager.get_user(42)`
because PR 3 removed `find_user`. An earlier revision of this file said "the
sixty-two tests", which no measurement reproduces.

Two consequences for anyone reading this section:

- **The tests that police the rulebook are deleted, not rewritten.** Nothing in
  the suite now keeps `AGENTS.md`, `README.md` or a workflow honest. That is the
  decision `PRD.md` section 3.2 records, and it means the documents in this
  repository are maintained by reading them, not by running a test.
- **The notes-asserting tests were deleted, not rewritten.** Three of the eight
  deleted files asserted on `notes/*.md` content —
  `test_object_model_notes.py`, `test_chess_rules_notes.py` and
  `test_reference_diagram_notes.py`. A fourth test, in
  `tests/test_docs_and_docstrings.py`, read the real `notes/*.md` from disk and
  asserted the generated pages equalled them byte for byte; **that one** was
  rewritten rather than deleted. It is now driven from `tmp_path`, so it asserts
  what `.github/scripts/docs_hooks.py` *does* — that every Markdown file in a
  notes directory is published verbatim and linked from a hub page — against a
  fixture it owns, and it reads nothing from the repository. An earlier revision
  of this file said the notes test "has been rewritten, not deleted" as though it
  were the only one; three others went with the files.

**The survivor, now gone.** `tests/test_docs_and_docstrings.py::test_generated_docs_directory_is_not_tracked`
ran `git check-ignore --quiet .docs/index.md` and asserted the exit code is zero.
It asserted that `.gitignore` ignores the generated docs directory — a property of
the repository, not of the product — so by `PRD.md` §3.2's own definition it
belonged with the fifty-one. It was the last one standing. It is deleted, which
takes metadata assertions to **zero**, together with
`test_docs_config_and_strict_build` from the same file: that test asserted
`properdocs.yml` exists at the repository root and then shelled out to run the
build — the same build `.github/workflows/verify-docs.yml:31` runs, as the `docs`
job of the pinned pipeline behind `ci.yml` also does. That is two more deletions
on top of §5's fifty-one, so the tally of tests deleted for asserting on metadata
rather than on the product is fifty-three; the fifty-one was measured at `4e7f270`
and is not re-measured by this revision, and no current collection count is quoted
here for the reason §4.3 gives.

**What the suite covers that it did not.** The perft gate for chess and draughts,
the engine-holds-no-chess invariant, the rules of draughts position by position,
the copied-configuration boundary, the game loop end to end, the alias table,
the manager reading its writers and quests, and the configuration directory
operations.

**What PR 21 still owes.** §4.3 lists what is unreferenced; unreferenced is not
the same as uncovered, and PR 21 is the pass that distinguishes them. One coverage
gap this file recorded earlier is closed — a `Board` of non-8×8 dimensions is
built and played on in `tests/test_board_generalisation.py`, at 8×8, 10×10 and 5×7.
The other was **not** closed at the time of writing and is closed now: the format switch
had no test at all, because `tests/test_manager_exporters.py` stood its own `OnlyOneNotation`
in front of the manager and never constructed the shipped writer, which is precisely why a
writer that returned `""` for an unknown notation could sit in the tree unnoticed. Since
2026-10-05 every writer's `export` is called in `tests/test_notation_and_writers.py`, in the
manager's case-insensitive spelling and in a spelling it does not declare, and the unknown
notation raises. The writers' *outputs* remain largely unverified in substance because the
outputs are largely wrong (§4.1) — that is item 19's work, not this one's. **The draughts
writers are held against a played game rather than a pasted one**
(`tests/test_checkers_export.py`): a game is played to a result through the manager, and the
record is walked move by move rather than compared against a string written out by hand, so a
record pasted in wrongly cannot pass. The same file refuses `FEN` by name, proves the engine
names no draughts writer and no draughts notation (the chess leak gate's shape pointed at this
game), and proves a copied configuration writes with its own writers, its own naming and its
own board.

---

## 6. Phase 1 — quick wins

No product behaviour changes. Reviewed and merged one at a time before Phase 2
begins. **The maintainer merges; do not merge.**

| PR | Content | Needs | State |
|---|---|---|---|
| 1 | PRD + SCRATCHPAD | — | delivered |
| 2 | Flatten `src/` to root, and reconfigure the docs pipeline with it | 1 | delivered |
| 3 | Delete metadata-only tests, close docstring gaps, drop the unused aliases | 2 | delivered |
| 4 | CI: native self-contained workflows, then remove the agent workflows only | 3 | delivered on `feature/native-ci-workflows`; re-scoped here, §6 PR 4 |
| 5 | Governance rules: `AGENTS.md` 1, 2, 4, 7, 9, 10, 11, 12, 13 | 4 | delivered on `feature/governance-rules` |
| 6 | Packaging, entry point, and the git-ignored log directory | 2 | delivered |
| 7 | README: stop claiming what the product does not yet do | 1 | delivered in the main stack by `77d978c` |

**The order is load-bearing.** PR 3 deletes `tests/test_workflow_rules.py` and
`tests/test_auto_format_workflow.py`, the only tests that asserted on
`.github/workflows/*.yml` and on `AGENTS.md` Rules 7 and 11. PR 4 and PR 5 both
change files those tests read, so both must land after it, not before.

**Phase 1 is numbered 3 = cleanup, 4 = CI, 5 = governance everywhere in this
file.** The summary table above, the issue list in the header, the dependency
graph in §7 and the three detail headings below all say so.

### PR 1 — PRD and SCRATCHPAD

**State**: delivered.

The requirements and this manual. *(already open for review)*

**Acceptance criteria**: every FR reference resolves across all tracked sources;
every PR number in this file falls within 1–21; the definition of done, the risk
table, the dependency graph and the decision log are present and internally
consistent; `pytest`, `black --check` and `properdocs build --strict` are green.

**Verification**: `pytest -q`, `black --check .`, `python -m properdocs build
--strict`, and a cross-reference sweep of every FR and PR reference.

### PR 2 — Flatten `src/` to root, and reconfigure the docs pipeline

**State**: delivered.

**Goal**: the package sits at the repository root.

| What | Change |
|---|---|
| `src/model` → `model`, `src/controller` → `controller`, `src/view` → `view` | delete `src/` |
| `pyproject.toml` | `pythonpath = ["src", "."]` → `["."]` |
| ~15 modules | collapse the 3-level `try/except ImportError` fallbacks to plain imports; they existed only because of `src` |
| `AGENTS.md` Rules 1 and 2 | both say "all code in `src/`" |
| `properdocs.yml` | `docs_dir: src` → a generated child directory; the hand-written module `nav:` is deleted entirely |
| `docs_hooks.py` | build the whole nav programmatically and emit every page as a virtual file |
| `.gitignore` | ignore the generated docs source directory |
| `tests/test_docs_and_docstrings.py` | walk the package dirs |
| `tests/test_structure.py` | **no change** — its module list is already top-level, never `src.*` |

**Acceptance criteria**: `pytest` green; `black --check` clean; `properdocs build --strict`
clean; `grep -rn "src\." --include='*.py' .` finds no stale `src.` import;
every previously-passing test still passes.

**The docs pipeline is the hard part of this PR, and `docs_dir: .` does not
work.** `properdocs` validates that `docs_dir` is not the parent directory of the
config file, so pointing it at the repository root aborts before any file is
walked:

```
ERROR - Config value 'docs_dir': The 'docs_dir' should not be the parent
directory of the config file. Use a child directory instead so that the
'docs_dir' is a sibling of the config file.
```

`exclude_docs` cannot help — the failure is at config validation — and a
committed `docs/` directory is forbidden by `AGENTS.md` Rule 2.

**The design that works is closer to what Rule 2 wants anyway.** `docs_dir` points
at a **generated, git-ignored child directory**, and `docs_hooks.py` builds the
whole navigation and emits every page as a virtual `File.generated`. Nothing
static is stored anywhere. The hook already builds the Notes section of the nav;
this PR extends it to build the entire nav, one entry per module.

**This also removes a recurring breakage.** `properdocs.yml` hard-codes nav
entries for `model/pieces/horse.md`, `model/pieces/tower.md` and
`controller/controller.md`. A nav entry pointing at a missing file is a warning,
and `--strict` makes it a build failure — so PR 13 (moving the pieces) and PR 20
(renaming `horse.py`, deleting `tower.py`) would each break the docs build.
Generating the nav makes that class of breakage structurally impossible, and **no
later PR needs to touch `properdocs.yml`**.

**Additional acceptance criteria**: the generated docs source directory does not
appear in `git status`; adding or renaming a module requires no `properdocs.yml`
edit.

**Blocks**: 5, 6, 8, 9.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.

### PR 3 — Cleanup

**State**: delivered.

**Goal**: remove what asserts nothing about the product.

Delete the tests that assert on repository metadata. §5 records what was deleted
and what replaced it. Close the two docstring gaps and remove the `piece.py`
demo block. Remove the dead aliases that do not collide with the rename:
`Timer.countdown`, `Player.get_color`, `Player.get_user`, `Player.get_elo_rating`,
`UserManager.find_user`. `Tower`, `Horse` and `Controller` are gone as names.

Also correct the two notes that were stale against the diagram, while the note
tests are being removed anyway:

- `notes/reference_diagram.md` describes the diagram as drawing `Tower`, `Kůň` as
  "`Horse` / `Knight`", `GameController` (the diagram's box is
  `GameManagerController`), `WindowController` (no such box exists), `Quest` as
  having "conditional predicates" (it has none), `Figurka` as carrying
  `can_jump` (declared on the six subclasses, not the parent), `MetadataWriter`
  as a "PGN header tags roster" (the box says "no parameters") and `Timer` as
  handling "time increment management" (no increment is drawn). Every one is
  corrected against the diagram.
- `notes/chess_rules.md` names the jumping piece `Knight`.

**Acceptance criteria**: `pytest` green at the reduced count; no test opens
`AGENTS.md`, a workflow, `notes/` or `README.md`; both `Returns:` gaps closed; no
note file describes a class or member the diagram does not draw.

**One acceptance criterion was wrong and is withdrawn.** It read "the only
remaining `pass` is `ExportWriter.export`'s abstract raise". That is wrong twice
over: `ExportWriter.export` (`model/misc/export_writers.py`) **raises**
`NotImplementedError` and contains no `pass` at all, and three real `pass`
statements remain, all of them the same deliberate shape — a tkinter `TclError`
swallowed when a grab or an `after` job has already gone:
`view/player_game_view.py:332`, `view/start_modal.py:123` and
`view/settings_dialog.py:714`. Each is marked `# pragma: no cover`. There is one
other `raise NotImplementedError`, at `model/game/quests.py:693`, where the
private `_AtGameEndQuest._judge` is the hook every subclass must override.

**Risk**: deleting tests could mask regressions. Every deletion is import-only or
metadata-only, and PR 21 adds behavioural coverage to offset.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.

### PR 4 — CI: native workflows, then remove the agent workflows

**State**: delivered on `feature/native-ci-workflows`, which is not on the main
stack. The scope below was **narrowed on the main stack** after the maintainer's
order of 2026-10-02, "remove the agent scaffolding from the project", was narrowed
again to the agent workflows and nothing else. Plan issue #167.

**Goal**: the autonomous agent goes. The delegates that branch protection depends
on stay, and so does the pin they resolve through.

**There are 13 workflows on the main stack, and 11 of them are thin delegates**
to `marius-patrik/DarkFactory` at the pinned ref in `.github/darkfactory.json`:
`agent.yml`, `auto-format.yml`, `ci.yml`, `deploy-docs.yml`, `open-pr.yml`,
`pr-approval-automerge.yml`, `preview-docs.yml`, `project-automation.yml`,
`release.yml`, `report-failure.yml` and `verify-pr-issue.yml`. Only
`verify-docs.yml` and `verify-view.yml` are already self-contained. An earlier
revision of this section said "11 of 12", which counted neither of those two.
**`agent.yml` is gone from the main stack now**, leaving twelve workflows and ten
delegates.

**Delete**: `.github/workflows/agent.yml` and **nothing else in `.github/`**. An
earlier revision of this section listed `.github/darkfactory.json`, `open-pr.yml`,
`pr-approval-automerge.yml`, `project-automation.yml`, `report-failure.yml`, the
`pipeline` git remote and the empty gitignored `.pipeline/`. That list is
withdrawn. `agent.yml` passed fourteen secrets, twelve of them provider
credentials for seven coding-agent harnesses, and it was the only workflow that
named any of the twelve; the two GitHub-side ones it also passed,
`DARKFACTORY_APP_PRIVATE_KEY` and `GH_PROJECT_TOKEN`, are still named by
`open-pr.yml`, `project-automation.yml` and `pr-approval-automerge.yml` and stay.
`.github/ISSUE_TEMPLATE/request.yml:10` loses the sentence claiming requests are
analysed automatically.

**Reimplement natively and self-contained**: nothing. `ci.yml`, `auto-format.yml`,
`deploy-docs.yml`, `preview-docs.yml`, `release.yml` and `verify-pr-issue.yml`
stay thin delegates, as do `open-pr.yml`, `pr-approval-automerge.yml`,
`project-automation.yml` and `report-failure.yml`.

**Unchanged**: `verify-docs.yml` and `verify-view.yml` are already
self-contained. `verify-view.yml` exists only on the main stack and is why §8
item 33 is false there — it is the one workflow that runs the tkinter tests, and
the pinned pipeline does not install a windowing toolkit.

**What is kept in `.github/`, and why:**

- **`.github/darkfactory.json`** — the ten surviving delegates read it wholesale,
  and nothing in this repository can prove the pipeline tolerates a missing key.
  Its `upstream.ref` is the pin every one of them resolves through.
- **`open-pr.yml`** — `AGENTS.md` Rule 7 requires every pull request to be opened
  in Draft by `github-actions[bot]` through it. Deleting it would leave Rule 7
  unsatisfiable and every pull request in this stack, including the one removing
  the agent, would need a personal access token instead.
- **`identity.agent_slug`** (`darkfactory.json:8`) — the only agent-specific key
  in the file, and **vestigial**: with `agent.yml` gone, nothing here reads it. It
  **stays**, for the same reason as the file around it. Deleting one cosmetic
  string is not worth risking `ci.yml` on every pull request to find out.
- **`report-failure.yml:6`** — its trigger named `Autonomous Agent`, a workflow
  that no longer exists, so the entry goes and the rest of the list stands.

**`AGENTS.md` Rule 13 is withdrawn on the main stack, not by PR 5.**
`feature/native-ci-workflows` carries only the six commits that remove the
delegates and the pin, and the rule is still present in its `AGENTS.md`. It is
withdrawn by the pull request bound to #167, which **tombstones** the number
instead of renumbering it, because this file refers to it by number in several
places. An earlier revision of this section attributed the deletion to PR 5, and
listed Rule 13 under PR 4's deletions before that; both attributions were wrong.

**Order inside the PR — non-negotiable**: land the replacement `ci.yml` and
`auto-format.yml` first and get them green, *then* remove the delegates. The
repository must never sit without working required checks. Under the narrowed
scope there is nothing to land first, so the rule reduces to: **`agent.yml` goes
in one commit, and no required check goes with it.**

**Acceptance criteria**: `git remote -v` shows only `origin` and `upstream`; no
workflow calls the autonomous agent, and no workflow names a workflow that does
not exist; none of the twelve provider credentials is named anywhere in the
repository; `AGENTS.md` Rule 13 is withdrawn in place, and Rules 7, 9, 10, 11, 12
and 14 are byte-identical; CI green on all four Python versions.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.

### PR 5 — Governance rules

**State**: delivered on `feature/governance-rules`, on top of PR 4 and not on
the main stack.

**Goal**: `AGENTS.md` states what is now true.

- **Rules 1, 2** — point at the flattened layout and the generated docs
  directory, and name `properdocs` rather than `mkdocs`.
- **Rule 4** — permit Czech aliases alongside English canonical names. It currently
  forbids them outright, contradicting the product requirements.
- **Rule 7** — drop the bot-authored-PR requirement and the auto-merge clause;
  state that the maintainer merges.
- **Rule 9** — keep issue binding and branch auto-deletion; drop the pipeline
  automation wording.
- **Rule 10** — remove the claim that "automated CI checks enforce" the plan and
  the pre-merge review. PR 4 deletes the workflow that enforced them, so after
  this PR nothing does and the rule must not claim it.
- **Rule 11** — delete entirely; it exists only to drive auto-merge.
- **Rule 13** — withdrawn on the **main stack** rather than here, by the pull
  request bound to #167, because the agent workflow it describes is being removed
  and its number is tombstoned rather than renumbered. `feature/governance-rules`
  deletes it outright, which would close the gap the references here read across.
- **Rule 12** — it requires a `Request` issue per prompt with a linked `Plan`
  child and an `approve` comment, enforced by that same deleted workflow. Keep the
  discipline, drop the claim of automated enforcement, and note that this track's
  Request and Plan issues are #123 to #130.

On `feature/governance-rules` the rules that survive run 1 through 10, 12 and 14:
eleven is deleted and thirteen is deleted with it. **On the main stack thirteen is
withdrawn in place instead**, as a tombstone, so the numbering above still means
what it says, and fourteen keeps its number. The branch's whole diff against
`feature/native-ci-workflows` is `AGENTS.md`.

**Acceptance criteria**: no rule references `.github/darkfactory.json`,
`open-pr.yml`, or a bot author; no rule claims automated enforcement by a workflow
PR 4 deletes; Rule 4 permits Czech aliases; Rules 1 and 2 name the flattened
layout and `properdocs`.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.

### PR 6 — Packaging, entry point, and the log directory

**State**: delivered, with no open gap. `pyproject.toml` ships `games.chess` **and**
`games.checkers` with all six of its subpackages — commit `319ed0d` closed the gap
an earlier revision of this section recorded (§4.1).

Add a `[project]` table and a build backend. **`packages` must be set
explicitly** — a flat layout plus setuptools auto-discovery trips over `tests/`
sitting at the root.

**Three things the product needs that have no other home:**

1. **An entry point.** `python -m <entrypoint>` must start a window (FR-59).
2. **`games/` must ship with the package.** It sits outside `model/`,
   `controller/` and `view/`, so an install shipping only packages would not find
   its own default configuration and every later phase would look broken. Either
   declare the configurations as package data or have the loader locate them
   relative to the installed distribution.
3. **`logs/` must be git-ignored.** FR-56 requires it, and `.gitignore` now has
   the entry. An earlier revision of this section cited FR-55 here, which is the
   checkers-requires-no-engine-change requirement and has nothing to do with logs.

**Acceptance criteria**: the package builds and installs; `pip install .` in a
clean venv imports `model`, `controller` and `view` **and finds both
`games/chess/` and `games/checkers/`**; the entry point starts the application;
`git check-ignore logs/` succeeds; no runtime dependency is declared beyond the
standard library.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.

### PR 7 — README honesty

**State**: delivered in the main stack by commit `77d978c`.

**Goal**: `README.md` stops claiming what the product does not yet do. It used to
advertise "custom board configurations", which was false until PR 8. State what is
true, and add the documentation and diagram links it already has.

**Acceptance criteria**: every capability claimed in `README.md` is covered by a
passing test.

**What delivery looks like.** `README.md` now carries a *What works today* table
whose last column names the module each claim lives in, a *What is partial* list
naming the four concrete export defects, and a *Not built yet* list. Every row of
the first table names a module a test exercises. The one claim that is not a
product capability — "an installable package" — rests on
`tests/test_packaging.py`, which resolves `games_root()`, resolves and refuses a
configuration path, and runs the entry point's `--check` path and its window
construction; it does not perform a real `pip install` into a clean environment.

`feature/readme-honesty` is superseded and **is not to be merged**. It forked from
`f4e1487`, twenty-two commits before this stack, so it predates the view layer,
`games/`, the packaging and the settings surface.

---

## 7. Phase 2 — the product

### Shape

```
Phase 1 (linear in this order)
  1 → 2 → 3 → 4 → 5
        └→ 6 → 7          (6 needs only 2, so 6 and 7 can run alongside 3-5)

Phase 2
  8 → 10 ─┬→ 11 ─┬→ 13 ─┬→ 18 → 19
  9 ──────┘      │      │     └→ 17 (also needs 12)
  12 ────────────┘      │
  13 ───────────────────┴→ 14 → 15 → 16
                                          └→ 20 → 21
```

### Dependency graph as edges

"A → B" means A must merge before B.

| From | To |
|---|---|
| 1 | 2 |
| 2 | 3, 6, 8, 9 |
| 3 | 4 |
| 4 | 5 |
| 8 | 10 |
| 9 | 14 |
| 10 | 11, 12 |
| 11 | 13, 14, 18 |
| 12 | 17 |
| 13 | 17, 20 |
| 14 | 15 |
| 15 | 16, 20 |
| 16 | — nothing further; 17 runs in parallel |
| 17 | 21 |
| 18 | 17, 19 |
| 19 | 21 |
| 20 | 21 |

Roots are 1 and 7. The longest chain is
`2 → 8 → 10 → 11 → 14 → 15 → 20 → 21`, eight deep. PRs 12, 13, 17, 18 and 19 run
alongside that chain rather than extending it, so wall-clock time is set by the
chain and not by the total.

**The graph above is the plan as drawn; §4.5 is where each node actually stands.**
Five edges have been satisfied out of order and the plan does not say so: PR 12
needed only PR 10 and landed with the checkers configuration, PR 17 landed
without PR 18 and is therefore partial, PR 11 landed without removing every
`getType()` and `hasattr` site and is therefore partial, PR 20's alias half landed
without PR 15 or the `controller.py` rename, and PR 7 landed in the main stack
while its branch sat unmerged. Nothing else in the graph moved.

### Wave A — PRs 8 and 9 are independent of each other; PR 10 needs PR 8

| PR | Content | Needs |
|---|---|---|
| 8 | Board generalisation | 2 |
| 9 | `Quest` parent with built-in subclasses | 2 |
| 10 | `Rule` parent, five hooks, configuration loading | 8 |

PRs 6 and 7 are Phase 1 and merge independently of this wave.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 8 — Board generalisation

**State**: delivered.

**Goal**: board size is not restricted to 8×8.

**Scope**: every site that took its bounds from a literal. `Move.validate` takes its bounds from the
board rather than a literal. `Board.setup_default_board` no longer silently
yields an empty board for a non-8×8 size. `MoveValidator` ray lengths come from
the board dimensions. FEN rank and file iteration comes from the board.

**Do not** change chess behaviour — the rules that depend on the home rank land
in PR 11.

**Acceptance criteria**: a `Board` of any dimensions can be constructed,
populated and moved on; `Move.validate` accepts an in-bounds move on any size and
rejects an out-of-bounds one; **no site under `model/`, `controller/` or
`view/` assumes 8×8**; and a test builds boards of 8×8, 10×10 and 5×7 and
exercises a move, a capture, a promotion and a FEN export on each.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 9 — Quest parent with built-in subclasses

**State**: delivered.

**Goal**: quests follow the same parent-and-subclass pattern as rules.

`Quest` gains `name`, `description`, `reward`, `when`, `parameters()`,
`progress()`, `observe_move()`, `observe_result()`, and `validate() -> bool`
matching the diagram exactly. **No condition class.** Twenty built-ins, twelve
watching the game a move at a time and eight judging the finished game:

`after_move`, twelve: `FirstBlood`, `CaptureN`, `CaptureOfType`,
`MovePieceNTimes`, `ReachedSquare`, `VisitNSquares`, `SurvivePlies`,
`SurviveWithoutCapture`, `CastleN`, `PromoteN`, `EnPassantN`, `MakeCheckN`.
`at_game_end`, eight: `NeverInCheck`, `KingOnlyGame`, `GameResult`, `WonBy`,
`GameAtLeast`, `MaterialAhead`, `Pacifist`, `CompositeQuest`.

**`NeverInCheck` and `KingOnlyGame` judge the finished game, not each move.**
They are the two this file once filed under `after_move`, and filing them there
is what produced a fourteen/six split that the code does not have: a game in which
the royal piece is never attacked, and a game in which only one kind of piece ever
moves, are both statements about a game that has ended.

`model/game/quests.py` declares all twenty as classes. `build_quests()` returns
**seventeen** instances — the seventeen a configuration can play without first
answering a question about its own pieces — and names the three it omits and why:
`CompositeQuest` is the mechanism for building a quest out of other quests, and
`CaptureOfType` and `KingOnlyGame` both insist on naming a piece type, which only
a configuration can answer. `games/chess/` supplies those two with chess's own
piece names.

`QuestManager` holds the quests **in play for the current game** only. Completed
quests live on the user via `Uzivatel.pridej_quest` and
`Uzivatel.splnene_kwesty`. XP is derived as the sum of completed rewards; `User`
gains no new field.

**Acceptance criteria**: `Quest.validate()` takes no arguments; a quest built from each `when`
completes on the intended event and not before; a quest completes once and stays
completed; progress renders current and target; `condition_fn` is gone.

**Needs**: 2. **Blocks**: 14.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 10 — Rule parent, five hooks, configuration loading

**State**: delivered.

**Goal**: the code-driven layer, and the configuration concept.

`Rule` carries `value` and `state` and implements `permits_move`,
`available_moves`, `outcome`, `on_move_made`, `status`, each defaulting
permissively. `Result(kind, precedence, winner)` with decisive outranking draws
and ties by declared order. A loader reads a configuration directory.

**Three details carry the design; each has a test**:
- **No rule owns behaviour.** The validator asks, rules answer. A rule may
  permit or forbid, never cause; may propose an outcome, never impose one.
- **Precedence**, so two rules firing at once is deterministic.
- **`value` persists, `state` resets each game.** A saved configuration must not
  contain a game's history.

`games/chess/` is created with `board.py`, and empty `pieces/`, `rules/`,
`quests/`, `clocks/`, `export/` directories. Populated in PR 13.

**Acceptance criteria**: a custom rule loaded from a test fixture participates in a game
without any engine edit; two colliding rules resolve by precedence; a rule's
`state` never reaches disk; loading from a path outside `games/` is refused.

**Needs**: 8. **Blocks**: 11, 12, 18.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 12 — Multi-hop moves

**State**: delivered, as `HopMove(Move)` in `games/checkers/moves.py` rather than
as a sequence on `Move` (§4.7).

**Needs**: 10. **Blocks**: 17.

**Goal**: a capture chain is one move the player makes, not several.

A `Move` subclass carries the hops and `Move` gains nothing draughts-shaped.
`HopMove(Move)` adds `hops`, `captures`, `captured_pieces` and `route`, overrides
`apply_to_board`, and reuses the engine's `Applied` record so the engine's
`unapply_from_board` undoes a chain with no second mechanism. **`Move` is not
byte-for-byte untouched** — it carries `captured_piece`, `capture_from`,
`companion_start` and `companion_end`, four members that are castling and
single-capture members rather than hop members, and all four are listed in §4.7.

**Acceptance criteria**: a three-hop chain built from a constructed board is
offered as a single move, executes atomically, and rolls back completely if any
hop is invalid. A single-hop move goes through the same path as the degenerate
case. `tests/test_draughts_perft.py` holds the chain rule against the published
perft counts.

### Wave B — two PRs in parallel

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 11 — Orthodox chess rules, and removal of type coupling

**State**: **partial** — thirteen rules ship and the hard-coded type coupling is
gone; the *declared-kind* coupling PR 11 set out to remove is not.

**Needs**: 10. **Blocks**: 13, 14, 18.

**Goal**: every rule in `notes/chess_rules.md` implemented, and the engine stops
knowing what a king is.

**Thirteen chess rules** as `Rule` subclasses in `games/chess/rules/`. **They are
not one per file**: the thirteen live in eight files — `castling.py`,
`en_passant.py`, `promotion.py`, `royal.py` and `bishop_colour.py` hold one each,
`check.py` holds three (`CheckRule`, `CheckmateRule`, `StalemateRule`) and
`draws.py` holds four (`InsufficientMaterialRule`, `FiftyMoveRule`,
`ThreefoldRepetitionRule`, `MutualAgreementRule`). A ninth file, `attacks.py`,
holds shared helpers rather than a rule. The one-file-per-rule shape was planned
and is not what shipped.

| Class | File | Rule |
|---|---|---|
| `RoyalPieceKind` | `royal.py` | which piece kind may be put in check |
| `CastlingRule` | `castling.py` | castling |
| `EnPassantRule` | `en_passant.py` | en passant |
| `PromotionRule` | `promotion.py` | promotion |
| `BishopColourRule` | `bishop_colour.py` | each bishop confined to the shade of square it started on |
| `CheckRule` | `check.py` | check |
| `CheckmateRule` | `check.py` | checkmate |
| `StalemateRule` | `check.py` | stalemate |
| `InsufficientMaterialRule` | `draws.py` | insufficient material |
| `FiftyMoveRule` | `draws.py` | the fifty-move rule |
| `ThreefoldRepetitionRule` | `draws.py` | threefold repetition |
| `MutualAgreementRule` | `draws.py` | mutual-agreement draw |
| `FlagFallRule` | `flag.py` | loss on time, and only where the opponent retains mating material |

**The count this file used to give was eleven, and two rules were outside it.**
`BishopColourRule` was never named anywhere in this file, though
`notes/chess_rules.md` section 2 mandates the confinement it enforces.
`RoyalPieceKind` was named in the same sentence as the count and not counted; it
is a `Rule` subclass like the other twelve, which is why the count was eleven
where the directory holds thirteen. It declares a kind rather than judging a
position, and FR-14 is what it exists for.

**What the engine no longer holds.** The hard-coded special cases are gone:
`MoveValidator.find_king` is replaced by `find_royal` (`validator.py:181`), which
asks the active rule set which kind is royal rather than comparing a string; and
the `PIECE_CHARS` table with its `"p"` fallback is gone from the position-record
writer, which now asks the piece (`ExportFEN._fen_letter` in
`games/chess/export/fen.py`, since 2026-10-05).

**What PR 11 said it also removes, and did not.** The claim was that `find_king`,
`is_check`, `is_checkmate`, every `getType() == "king"` / `== "pawn"` comparison
and every `hasattr` probe are gone. `find_king` is gone. **`is_check`
(`validator.py:244`) and `is_checkmate` are both still there**, and they are
called from `manager.py:211,215,353,354`. Neither is *hard-coded* coupling —
neither names a piece type — but neither was removed either.

**Where `getType()` actually still is.** Twenty-one call sites across ten files,
counted as occurrences of the call rather than lines holding it — `attacks.py:98`,
`draws.py:340` and `geometric.py:89` each hold two:

| Location | Sites |
|---|---|
| `games/chess/rules/` | **13 across 5 files** — `attacks.py:62,98`, `castling.py:84,145,191,215`, `draws.py:128,333,340,395`, `bishop_colour.py:90`, `promotion.py:102` |
| `games/checkers/rules/` | 5 across 3 files — `draws.py:100`, `limited_kings.py:68`, `geometric.py:89,131` |
| `model/game/` | **3 across 2 files** — `validator.py:199`, `manager.py:351,352` |

An earlier revision of this section said "the three remaining `getType()`
comparisons are in `games/chess/rules/` — `attacks.py`, `castling.py` and
`draws.py`". There are **thirteen** in that directory, across **five** files:
`bishop_colour.py` and `promotion.py` were not named.

**Where `hasattr` actually is.** Four probes, all in one file:
`model/game/clock_fields.py:53,64,94,101`. They ask what a clock object holds,
which is how the Clocks section describes a clock that derives from nothing — see
`notes/object_model.md` §20. The claim that `hasattr` coupling is left "anywhere
under `model/`" is therefore false.

Rank-relative rules generalise: the home rank, the knight-forward file and the
castling rook files are derived from the configured board rather than assumed to
be 1, 8 and `a`–`h`. `CastlingRule.home_row` (`castling.py:44`) and
`CastlingRule.start_file` (`:56`) read the board, and the castle loop bounds
`rook_file` and `king_dest` against `position.cols`. **No test exercises castling
or en passant on a non-8×8 board** — §8 item 12.

**Acceptance criteria**: each rule passes a game with it enabled and a game with it disabled,
and the difference is the setting rather than a code path; no `getType()` or
`hasattr` coupling is left anywhere under `model/`, `controller/` or `view/`; a
custom piece whose kind is not `"king"` neither crashes nor silently disables
check.

**Which of those hold.** The first holds for twelve of the thirteen:
`BishopColourRule` is named only as a string in the rule-order list at
`tests/test_chess_rules.py:62` and no test drives it on or off through a game. The
second does **not** hold — see the two tables above. The third holds:
`test_validator.py:20-26` shows a validator with no rules in force has no royal
piece and `test_chess_rules.py:276-281` shows a non-`king` kind disables check
without crashing.

**Needs**: 10. **Blocks**: 13, 14, 18.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 13 — Migrate chess into `games/chess/`

**State**: delivered.

**Needs**: 11. **Blocks**: 17, 20.

**Goal**: the chess configuration is complete and self-contained.

Move the six piece subclasses out of `model/pieces/` into `games/chess/pieces/`,
with declared unicode symbols and optional FEN characters. Move the rules from
PR 11 into `games/chess/rules/`. Create `games/chess/clocks/` and populate
`games/chess/board.py`. `chess` is the default and cannot be edited or deleted; a variant starts by
duplicating the folder.

**Two things that break silently unless this PR owns them.** The docs build
must stay green with the pieces gone from `model/pieces/` — PR 2 generates the
nav so no config edit should be needed, but **verify it**, because a stale nav
entry fails `--strict`. And `tests/test_structure.py` lists `model.pieces.*`, so
those entries become `games.chess.pieces.*` — unless PR 3 already deleted that
file, so check which applies.

**Acceptance criteria**: `model/` retains only the parent classes and machinery;
chess plays from `games/chess/` with no engine change; removing a piece file
removes it from a game without touching engine code; `properdocs build --strict`
is green with no `properdocs.yml` edit.

**Needs**: 11. **Blocks**: 17.

### Wave C — two PRs (14 and 18)

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 14 — Wire the orphan subsystems

**State**: delivered.

**Needs**: 9, 11. **Blocks**: 15.

`QuestManager`, `UserManager`, `User`, `MetadataWriter`, the configuration's
export writers (one class per format since 2026-10-05), `WindowController` are
instantiated and driven by the game loop.
`GameManager.players` is linked to users. `Timer.add_time` actually applies
increment. The `hasattr(user, "add_quest")` probe becomes a real call:
**`manager.py:384`** calls `user.add_quest(quest)`. (An earlier revision of this
file cited `manager.py:375`, which is `self.quest_manager.observe_result(event)`.)

**Acceptance criteria**: a complete game runs end to end headless, from `new_game` through a
finished result, with quests firing, clocks ticking, the transcript recording
and a user credited.

**Needs**: 9, 11. **Blocks**: 15.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 15 — View layer with the game-start modal

**State**: delivered.

**Needs**: 14. **Blocks**: 16, 20.

`BoardView`, `PlayerView` and `PlayerGameView` in `view/`, in tkinter, plus
`QuestCard` and `QuestList` in `view/quest_view.py`. Board with coordinates and
symbols, highlights, player panels with clocks and captured and lost pieces, turn
indicator, move history, status footer, quest cards with progress and reward.
Starting a game shows a modal with a **configuration selector**, a **Settings**
button and **Start**.

**There is no `GameView` class, and adding one would be wrong.**
`notes/object_model.md` section 15 once recorded one as created; it was not, and
the correction is there now. `view/game_view.py` declares `BoardView`, which is
the only part of the program that knows what a square looks like, and
`view/player_game_view.py` declares `PlayerGameView`, which holds a `BoardView`
and is the window a game is played in. `PlayerGameView.refresh` calls
`board_view.refresh`, so the diagram's `aktualizuj_plochu` is served by a
composition rather than by a class of its own.

**Headless testing**: `tkinter` needs a display. Tests stay within
`tkinter.Tcl()` and `ttk.Style()`, which work without one, or run under
`xvfb-run`. CI installs `python3-tk` in this PR, the first to import tkinter.

**Acceptance criteria**: the modal appears and its three controls work; a game is played to a
result through the GUI; every widget is reachable by keyboard. `tests/test_view.py`
holds the first two — the chooser lists the shipped games and starts one, the
board is dealt, a click shows where the piece may go, the move is played and the
turn hands over, an illegal click is refused and says so, and a game played to
checkmate ends in a result. Keyboard reachability is not asserted anywhere and is
owed.

**Needs**: 14. **Blocks**: 16, 20.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 18 — Export generalised

**State**: **mechanism delivered 2026-10-05**; *letter* as a format and the metadata
header are not.

**Needs**: 11. **Blocks**: 17, 19.

One class per format extending `ExportWriter`, living in `games/<variant>/export/`.
The `format_type` switch in `ChessNotationWriter.export` and the format-name
string are deleted — that is the `Extends` relation the diagram draws. Ship the
mechanism plus *letter* (algebraic) and the metadata header, both of which the
game needs immediately.

**Acceptance criteria**: no format switch and no format-name string exists anywhere in the
engine; adding a format is one file and no engine change; the metadata header is
derived from the players and result, with no placeholder strings.

**What landed**: `ExportPGN`, `ExportFEN` and `ExportStenographic` in
`games/chess/export/`, `build_exporters()` declaring them in that order, the
`ChessNotationWriter` class and the `model/misc/notation.py` shim deleted, and
`tests/test_engine_holds_no_chess.py` grown from a per-module list into a walk
over `model/` whose vocabulary is read from the chess configuration at run time.

**The last criterion is met, 2026-10-05.** `MetadataWriter` was the one thing
still in the way, because `manager.py:97` built it with no arguments and
`Configuration` had no slot to supply one. `Configuration.metadata` is that slot;
the header is `games/chess/export/metadata.py`'s `ExportMetadata`, declaring the
diagram's *Field - Field - Extra*; `GameManager` reads the configuration's record
and writes no tag into it, and passes the players, the outcome and the date
instead. The header carries the players and the outcome, so `Player 1`, `Player 2`
and the hard-coded `Site` are gone.

**Needs**: 11. **Blocks**: 19.

### Wave D — three PRs in parallel

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 16 — Settings surface

**State**: delivered — `SECTIONS` in `view/settings_dialog.py:37` is Board, Pieces,
Rules, Quests and Clocks; the corner selector duplicates, renames and deletes a
configuration; and `view/code_editor.py` edits rule and quest source, checked by
`model/game/source_validation.py` before it may join.

**Needs**: 15. **Blocks**: nothing further; 17 and 19 run in parallel.

One spec-driven form renderer: every configurable type declares its fields, and
one renderer turns that declaration into widgets. `Board.value_fields()`,
`Piece.value_fields()`, `Rule.value_fields()`, `Quest.parameters()` and
`model/game/clock_fields.py:clock_fields` are the declarations; `Field` is the
declaration type. **There is no `Configurable` class and no `spec()`** — see
`notes/object_model.md` §9. Sections for Board, Pieces, Rules, Quests, Clocks. A
corner selector meaning *which configuration is being edited* — settings only. An
"edit logic" code editor for rules and quests, writing into the configuration
directory and validating before the code may join.

**Acceptance criteria**: a form is assembled for each section without hand-built widgets; a
new field kind is one widget and every section inherits it; the editor refuses
invalid code and reports the error in the editor; a configuration can be created,
renamed, duplicated, edited, deleted and copied as a folder.

**Needs**: 15. **Blocks**: 20.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 17 — `games/checkers/`

**State**: partial — the game is delivered, held to the published perft counts,
and it declares **two** exporters: the letter notation and its own metadata
header.

**Needs**: 12, 13, 18 — it is meant to ship *letter* and metadata exports, and PR
18 is what makes those possible. **Blocks**: 21.

Full English draughts: twelve pieces a side, men moving one square forward
diagonally, kings sliding any distance diagonally, **mandatory capture including
chains**, promotion to king on reaching the far rank, and a win by immobilisation
or by losing all pieces. Exports: *letter* and the metadata header. **No FEN** —
a draughts position has none, and the structure says so rather than a runtime
check.

**What was built against that paragraph.** The board is 8×8 with twelve pieces a
  side, men step one square forward diagonally, crowning keeps the man in play, and
  `CaptureRule` / `LandingRule` / `CrowningRule` / `ImmobilisationRule` are in
  force. **Five points of that paragraph did not ship** until 2026-10-04, and none
  of them was recorded before this correction; `notes/object_model.md` §21 records
  each and what closing them cost:

  - **The king steps one square** (WCDF 1.17 and 1.21). It used to fly, which is
    international, Brazilian, Czech and Dutch draughts. Both are one number,
    `max_steps`, in `games/checkers/pieces/king.py`.
  - **The forty-move count is 80 plies** (1.32.2), forty moves by each side. It
    used to default to 100, which is fifty moves each.
  - **There is a threefold repetition rule** (1.32.1). There was none.
  - **The sufficient-material draw is gone.** It was in no rulebook, and it ended
    two-kings-against-one while that game was still winnable.
  - **`LimitedKingsRule` and `CaptureRule` remain declared and inert.**
    `LimitedKingsRule` caps how many kings a side may hold — at its shipped value,
    a side's full complement, so it forbids nothing until somebody lowers it.
    `CaptureRule`'s maximum-capture restriction ships switched **off**, which is
    what 1.20 requires: a player "may select any one that they wish, not
    necessarily that which gains the most pieces".

  **The perft gate could not have caught the king's reach**, and says so in its own
  docstring: a man needs more than eight plies to crown from the starting
  position, so no king exists in the tree the gate walks. A sliding and a stepping
  king were both measured at depth eight and both gave 845931.

**`build_configuration()` declares two exporters** (`games/checkers/__init__.py`),
as of 2026-10-05: `ExportLetter` (declared `Letter`) and
`games/checkers/export/metadata.py`'s `ExportMetadata` (declared
`Field-Field-Extra`), assembled by `build_exporters()` with the letter notation
first so `default_format()` and `save_log`'s extension follow from the
declaration. An earlier revision of this section said the configuration's "two
exporters" were absent *and* that it declared `exporters=[]`; both were true of
the code as it stood and neither is any more. Issue #158's "declares two
exporters" was wrong at the time and is right now, by accident rather than by
record.

**What the two writers will not write.** `ExportLetter` refuses `FEN` by name.
There is no FEN for English draughts: the algebraic squares are chess's, the
square numbers are a coordinate system rather than a position grammar, and a
draughts position has no halfmove clock or castling right to record. Writing one
to satisfy a writer would be inventing a notation, so the absence is stated rather
than probed for at runtime. The header writer differs from chess's in kind rather
than in spelling: a PGN header *is* the seven-tag roster and obliged to carry
every tag, so chess's writer puts `?` in a tag nobody supplied, while no
published roster obliges a draughts record to carry a tag it has nothing for, so
this one leaves the field out.

**The numbering is the board's, and it was already there.** `square_number` in
`games/checkers/board.py` counts the played squares in board order rather than
holding a second table, so `tests/test_draughts_perft.py`'s independent
derivation of the same arrangement is asserted equal to it for all thirty-two
squares. That is one numbering with a cross-check, not two that could drift.

**This PR is the executable proof of the abstraction.** If it needs an engine
change that chess did not, the seam is in the wrong place — treat that as a
failure of the abstraction, not of the PR. **No engine file changed to add
`games/checkers/`, and none changed to add its writers** — the second half is the
stronger claim, because it is the one PR 18 and PR 19 made possible.

**Acceptance criteria**: **zero engine changes**; mandatory capture is one `permits_move`
rule; a three-capture chain is offered as one move; a man reaching the far rank
is crowned; a player with no legal move loses; nothing in the engine mentions a
king, a pawn, a check or a mate. The last holds for piece *types* — no engine
module names one, and `tests/test_engine_holds_no_chess.py` proves it. It does not
hold for the words: `MoveValidator.is_check` and `is_checkmate` are engine methods
(§8 item 14).

**How far the perft gate actually reaches.** `ENGINE_DEPTHS` in
`tests/test_draughts_perft.py` is `(1, 2, 3, 4, 5, 6, 7)` — **the engine is walked
to depth 7**. The independent reference counter in the same file is asserted
against `PUBLISHED` to depth 8. The maximum-capture variant is walked to depth 6.
Chess's own gate, `tests/test_perft.py`, walks to depth 4. **No test anywhere
walks a perft to depth 9.**


**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 19 — Export formats

**State**: delivered 2026-10-05 — the five formats and the header have writers, and the records
all three of the remaining formats wrote are now right. See §4.1 and `notes/object_model.md` §27.

**Needs**: 18. **Blocks**: 21.

Every format the diagram's `ChessNotationWriter` box enumerates: *letter*, *PGN*,
*FEN*, *Field - Field - Extra*, *Stenographic* with standard or configured
compression from the standard library codecs, plus the game transcript.

**PGN is the largest single item.** Real PGN: a seven-tag roster derived from the
game, and SAN movetext with piece disambiguation, castling notation, promotion,
and check and mate suffixes.

**Acceptance criteria**: every format the diagram names is implemented and none is deferred;
FEN computes all six fields from game state with no hard-coding; **FEN
round-trips** — import a position, build it, export it, obtain the identical
string — for the start position, a mid-game position carrying both castling
rights, and one carrying an en passant square; PGN movetext is genuine SAN,
verified against known-good PGN for a position requiring disambiguation, with
each disambiguation case separately tested (two knights, three queens, two rooks
on one rank, a pinned piece that can still legally reach the square, promotion
capture).

### Wave E — the last two PRs, strictly sequential

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 20 — Czech aliases and remaining dead code

**State**: partial — all fifteen aliases ship and the three dropped names are
gone. The `controller.py` rename and the dead-code re-check are not.

**Needs**: 13, 15 — PR 13 for the piece files, PR 15 for the view classes it must alias. **Blocks**: 21.

Add the fifteen aliases from `PRD.md` section 5, `Knight` canonical with `Kun` as
its alias. Rename `horse.py` → `knight.py`; delete `Tower`, `Horse` and
`Controller`; rename `controller/controller.py` → `controller/game_manager_controller.py`
to match the diagram's `GameManagerController`.

**Re-check §4.3 and remove only what is still dead** — PR 14 made several
attributes live.

**Acceptance criteria**: every alias importable and `is` its canonical class;
`Tower`, `Horse` and `Controller` no longer importable; no dangling `hasattr`
probe or type-string comparison; `notes/object_model.md` carries the full
fifteen-row alias table with a location column per class, and that table is
verified against the source rather than trusted — a test asserts every name in it
is importable from its stated location.

**One item here is deliberately not done.** `Knight` declares
`piece_type="horse"`, and it keeps that. `piece_type` is data a configuration
writes into its saved values, so renaming it would silently repoint every stored
configuration that says `horse` at nothing. The display name changed to `Knight`
because a display name is not persisted. `notes/object_model.md` section 19
records this, and it is **not approved** — see that section's table of decisions
awaiting approval.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 21 — Behavioural test coverage

**State**: partial.

**Needs**: 17, 19, 20.

Close everything §4 lists as missing.

**Acceptance criteria**: every public method under `model/`, `controller/`, `view/` and
`games/` is reachable from at least one test; no surviving test asserts only on
repository metadata; the invariant tests hold — no third-party runtime import
anywhere under the project source, no hard-coded board dimension outside
`Board.DEFAULT_DIMENSIONS` and a configuration's own `DIMENSIONS`, all fifteen
aliases importable, the default configuration cannot be edited or deleted,
configurations survive a restart, a rule loaded from outside `games/` is refused,
colliding rules resolve by precedence, and a rule's `state` never reaches disk.

---

## 8. Definition of done

The project is finished when all of these hold.

**Read the annotations.** Several of these items were written as if a gate
existed. Where nothing asserts them, the annotation says so and names what *is*
asserted. An unannotated item here is a target, not a verified state.

**Quality gates**

1. `pytest` green, and no surviving test asserts only on repository metadata.
   **True.** `pytest` is green and no test asserts only on repository metadata.
   Everything `PRD.md` §3.2 names — `AGENTS.md`, workflow YAML, `notes/`,
   `README.md`, the `CLAUDE.md` symlink, import smoke — is gone, and the last
   survivor is gone too:
   `tests/test_docs_and_docstrings.py::test_generated_docs_directory_is_not_tracked`
   ran `git check-ignore --quiet .docs/index.md` and has been deleted, along with
   `test_docs_config_and_strict_build` beside it. §5 records both deletions.
2. Every public method is reachable from at least one test. **Not asserted, and
   not true on a name screen.** No test enforces this, and the sweep in §4.3
   finds 67 of 384 public methods and functions whose name never appears in
   `tests/` — among them `GameManager.start_turn` and `cancel_move`,
   `GameLogger.file_path`, `MoveValidator.set_board`, `ResultEvent.moves_by`,
   `QuestManager.register_quest`, `longest_chain`, `FiftyMoveRule.reset_count`,
   `BoardView.set_selection` and `set_in_check`, and every
   `games/checkers/rules/geometric.py` helper. Some of those are reached
   internally; that is precisely the distinction PR 21 has to make and has not.
3. `black --check .` clean at line length 100. **True** — 127 files unchanged.
4. `properdocs build --strict` clean, zero warnings. **True**, and the build is
   gated by a workflow rather than by a test:
   `.github/workflows/verify-docs.yml:31` runs `python -m properdocs build --strict`,
   and the `docs` job of the pinned pipeline `ci.yml` calls runs the same command.
   The test that used to shell out to it,
   `tests/test_docs_and_docstrings.py::test_docs_config_and_strict_build`, is
   deleted; `preview-docs.yml` triggers on every pull request with no base-branch
   filter, so a stacked pull request is built `--strict` too.
5. No third-party runtime import anywhere under the project source. **True** —
   `tests/test_packaging.py::test_no_third_party_runtime_import_under_the_project_source`.
6. No board dimension is hard-coded outside `Board.DEFAULT_DIMENSIONS` and a configuration's own `DIMENSIONS`. **True in the tree, not asserted as an absence.** The only dimension literal under `model/`, `controller/` or `view/` is `Board.DEFAULT_DIMENSIONS = (8, 8)` at `model/game/board.py:30`; every other `8` in those trees is tkinter padding or prose. But no test asserts the absence. What is asserted is the *consequence*, by exercising the board API at 8×8, 10×10 and 5×7 (`tests/test_board_generalisation.py`): construction, placement, bounds-checked validation, sliding, capture, an engine promotion on the far rank of whatever size the board is, and a FEN record whose rank count matches `rows`. That covers the paths those tests touch and not every path in the tree. An earlier revision of this item said the invariant "is asserted against the board API", which overstated it.

**Rules and configurations**

7. `Rule` has the five hooks, each defaulting permissively, and `Result` carries
   a kind, a precedence and an optional winner.
8. Every rule in `notes/chess_rules.md` implemented, each driven on and off
   through one game. **Implemented: yes, thirteen of thirteen. Driven on and off:
   twelve of thirteen.** `BishopColourRule` is the exception. It appears in
   `tests/test_chess_rules.py:62` only as a string in the rule-order assertion,
   and no test constructs it, so the rule `notes/chess_rules.md` §2 mandates has
   no behavioural test at all.
9. Logic beyond any shipped set is expressible without touching the engine.
10. Two colliding rules resolve by precedence, tested with rules written to
    collide.
11. A rule's configured `value` persists; its runtime `state` resets each game
    and never reaches disk.
12. Those rules hold on non-8×8 boards, rank-relative rules generalised.
    **Half asserted.** `tests/test_board_generalisation.py` builds 8×8, 10×10 and
    5×7 boards and exercises move validation, sliding, capture, an engine-level
    promotion and FEN serialisation on each. `CastlingRule` and `EnPassantRule`
    derive their files from the board in code (`castling.py:44,56`, and the
    `position.cols` bounds at `:105`), but **no test plays either on a board that
    is not 8×8**. "Generalised" is a statement about the code here, not a
    verified behaviour.
13. A move may consist of several hops.
14. Nothing in the engine mentions a king, a pawn, a check or a mate.
    **True for piece *types*, false for the words.** `MoveValidator.is_check` and
    `is_checkmate` are engine methods (`validator.py:244` and the `is_checkmate`
    call at `manager.py:205`), and `is_check` is an `MoveEvent` field. Neither
    names a piece type, which is what the requirement is for — §7 PR 11 spells out
    which half holds.

**Quests**

15. `Quest.validate()` takes no arguments and matches the diagram. **True, and
    asserted** — `tests/test_quest.py:58` inspects `Quest.validate`'s signature
    and every built-in subclass's.
16. Every built-in quest completes on its intended event and not before.
17. Quests in play and quests completed are held separately; XP is derived.

**Configurations**

18. `chess` plays orthodox chess with nothing configured, and cannot be edited or
    deleted.
19. A configuration is a directory that can be copied to create a variant.
20. `checkers` is full English draughts and requires **no engine change**, and it
offers the two formats that mean something for it. **The engine-change half
      holds; the half about the formats does not.** No engine file changed to add
      `games/checkers/`, and none changed when the rulebook gaps were closed on
      2026-10-04 either. The configuration plays WCDF English draughts: the king
      steps (1.17, 1.21), the forty-move count is eighty plies (1.32.2), a
      repetition rule exists (1.32.1), and the sufficient-material draw that ended
      two-kings-against-one is gone. Two variants remain declared and inert, and one
      divergence is deliberate: 1.32.1 is a claim to a referee and the engine
      proposes the draw itself. It still offers **zero** formats, not two.
      `notes/object_model.md` §21 records each; planned PR 17 owns the exporters.

**Interface**

21. Starting a game shows the modal with configuration selector, Settings and
    Start.
22. Every data-based configuration is form-exposed from one renderer.
23. The editor refuses invalid code before it joins a configuration.
24. A game is played end to end from the entry point to a result.
24a. `games/` ships with the installed package, so a clean install finds its own
    default configuration **and the second one**. **This now holds.**
    `pyproject.toml` names `games`, `games.chess` with its six subpackages, and
    `games.checkers` with its six — commit `319ed0d`. `tests/test_packaging.py`
    resolves `games_root()` and asserts the shipped configurations are there; no
    test performs a real `pip install` into a clean environment.

**Export**

25. Every format the diagram names is implemented: *letter*, *PGN*, *FEN*,
    *Field - Field - Extra*, *Stenographic*, and the game transcript. **Five of
    five, and as of 2026-10-05 each writes the record its format is.** One writer
    class each, in `games/chess/export/`: `ExportAlgebraic`, `ExportPGN`,
    `ExportMetadata`, `ExportFEN`, `ExportStenographic`, declared in that order by
    `games/chess/__init__.py:build_exporters` so PGN still leads. Having a writer is
    not the same as writing the right record, and on 2026-10-02 three of them wrote the
    wrong one — items 27 and 28, both closed below. **The second configuration writes
    two of them, 2026-10-05:** `games/checkers/export/` holds `ExportLetter` (declared
    `Letter`) and its own `ExportMetadata` (declared `Field-Field-Extra`), declared by
    `build_exporters()` with the record first. It writes no position record, and
    `ExportLetter` refuses `FEN` by name — the absence is stated in
    `games/checkers/export/__init__.py` rather than probed for at runtime.
    **The algebraic writer mis-read one thing of its own, 2026-10-05, and it is
    closed here:** it chose `O-O` from the spelling of `Move.move_type`, which
    is the single word `castling` for either castle, so a game that castled on both
    sides was written `O-O` twice. The side is read from the rook's square, as
    `pgn.py:_castle_of` already did, and
    `tests/test_notation_and_writers.py::test_a_castle_that_the_engine_itself_offered_tells_which_one_it_is`
    plays both castles and asserts the two tokens.
26. No format switch and no format-name string exists in the engine. **True as of
    2026-10-05**, and asserted structurally: `tests/test_engine_holds_no_chess.py` walks
    every module under `model/` with the writer names and format names read from the chess
    configuration, and separately refuses any `ExportWriter` subclass and any configuration
    import under `model/`.
27. FEN round-trips for the three positions named in the product
    requirements. **Amended, 2026-10-05, and no longer claimed as a round trip.** The
    round trip cannot be asserted without a reader, and no reader exists: FR-52 said one
    was "directed by the user on 2026-10-02" and the transcript does not support that —
    the owner's rule is that the diagram is the whole specification, and **the diagram
    draws writers, not readers**, which `notes/object_model.md` §12's own rationale
    argued. §12's approval line is withdrawn and FR-47 is amended. **The reader is not
    built.** What the three named positions now carry is asserted in
    `tests/test_position_record.py`, against facts rather than against a reader of this
    repository's own making: the starting position is compared with the string every
    chess program agrees on; a mid-game position is asserted to carry `KQkq` and an en
    passant square, and a position after a two-square advance to carry the target; the
    castling rights are checked against the castling rule's own conditions and the
    halfmove clock against `FiftyMoveRule.state["plies"]`, which it is asserted equal to,
    so there is no second counter.
28. PGN movetext is genuine SAN, verified against known-good PGN. **True, and
    asserted against a published game rather than against this writer's own output.**
    `tests/test_transcript_notation.py` replays **the Opera Game** — Morphy against the
    Duke of Brunswick and Count Isouard, Paris 1858 — and asserts the whole movetext
    against a literal transcribed from the English Wikipedia article on 2026-10-05:
    `1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7 8. Nc3
    c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7 14. Rd1 Qe6
    15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0`. That one game carries a queen capture,
    a knight capture, three checks, a long castle, a mate and `Nbd7` — a file
    disambiguation — at once. **Every remaining case is its own test**, because §9 names
    `Nbd7` versus `N1d7` versus `Nd7` as three different answers: two knights by file
    (`Nbd2`/`Nfd2`), two knights taking on one square (`Nbxd4`/`Nfxd4`), two rooks on one
    rank (`Rfe1`/`Rae1`), two rooks on one file (`R1a2`/`R3a2`), three queens (`Qd4d8`,
    needing both), a pawn's file on a capture (`exd5`/`cxd5`), a promotion with check
    (`e8=Q+`) and one that takes (`exd8=Q+`), and **a pinned knight**, which does *not*
    make the mover ambiguous — `Nb3` beside `Ndb3` — because a hint is written only from
    moves that are legal. That last one is the case a geometry-based implementation gets
    wrong, and it is why the disambiguation asks the validator rather than the board.

**Object model and hygiene**

29. All fifteen Czech aliases importable and identical to their canonical
    objects; `Tower`, `Horse` and `Controller` gone. **True, and asserted** by
    `tests/test_aliases.py`, which reads the fifteen-row table from
    `notes/object_model.md` and checks every row against the source.
30. Every deviation recorded in `notes/object_model.md` with approval context.
    **Now true.** The audit behind this correction found eleven unrecorded
    departures; §21, §22, §23 and §24 of that file record them, and §3, §7, §9,
    §11, §13 and §15 have been corrected against the code.
31. `notes/chess_rules.md` amended where board generalisation departs from it.
32. Nothing in §4.3's unreferenced list survives the PR 20 re-check; the §4.4
    docstring gaps are closed. **The docstring half holds; the other half has not
    run.** §4.4's two gaps are closed and `tests/test_docs_and_docstrings.py`
    holds the invariant. But §4.3's unreferenced table has **ten rows — nine
    genuinely unreferenced, plus `_SourceLoader.create_module`, which is excluded
    because the import machinery calls it** — and PR 20's re-check has not
    happened, so this item is outstanding by definition.
33. CI green across `3.10`, `3.11`, `3.12`, `3.13`, depending on no external
    repository's workflow. **False on the main stack.** There are 13 workflows
    there and **11 call the pinned DarkFactory pipeline** — including `ci.yml`
    itself. Native CI lives only on `feature/native-ci-workflows`, a branch 24
    commits behind the tip that cannot be merged without a rebase (§6 PR 4). The
    matrix is 3.10–3.13, and the `3.10`–`3.13` claim about *this* repository's
    own `ci.yml` is untested while it delegates. `verify-view.yml` is the one
    workflow on the main stack that runs the tkinter tests at all.

---

## 9. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| ~~Real PGN requires SAN disambiguation, which is easy to get subtly wrong — `Nbd7` versus `N1d7` versus `Nd7`~~ | **Discharged 2026-10-05.** The mitigation was each case getting its own test plus a known-good PGN, and both exist: seven disambiguation cases in `tests/test_transcript_notation.py`, and the Opera Game's published movetext as a literal the whole transcript is compared against. The pinned case is asserted in both directions — `Nb3` when the rival knight may not move, `Ndb3` when it may — because that is the one a geometry-based implementation gets wrong |
| `getType()` and `hasattr` coupling fails **silently** on rename or on a custom piece | High | PR 11 removes it. PR 20 ships tests that fail when a probe breaks, not only when a name changes. **Partly discharged already**: the *hard-coded* kind comparisons are gone and `tests/test_engine_holds_no_chess.py` reads the chess catalogue from the configuration so the gate cannot drift. What remains is 16 `getType()` sites in `games/chess/rules/` and `model/game/` — the draughts rules hold five more — and four `hasattr` probes; §7 PR 11 lists them file by file |
| Deleting 51 collected tests masks a regression | Medium | Every deletion is import-only or metadata-only, and one `docs_hooks.py` test was rewritten to read a `tmp_path` fixture instead of real `notes/`. PR 21 adds behavioural coverage. §5 gives the exact count |
| The flatten makes the whole repo the docs tree, and `exclude_docs` has to do work `docs_dir: src` did by construction | High | PR 2. Fallback is a dedicated docs directory rather than widening the tree |
| A flat layout breaks setuptools auto-discovery over `tests/` | Medium | PR 6 sets `packages` explicitly |
| Removing DarkFactory leaves the repository without working required checks | High | PR 4 lands the replacement and gets it green before removing anything |
| `checkers` needs an engine change that chess did not | High | That is the point of shipping it. Treat it as a failure of the abstraction and fix the abstraction, not the game |
| A multi-hop move model change destabilises ordinary single-hop moves | Medium | PR 12 tests a one-hop move through the same path as a three-hop chain |
| `tkinter` is absent from some Linux distributions | Medium | PR 15 installs `python3-tk` in CI and keeps tests within `Tcl()` and `ttk.Style()` |
| Customisable pieces, board geometry and rules all rest on one declaration mechanism | Medium | Every form is generated from it, so a defect shows up uniformly and is fixed once |
| The stack is deep; a late rework invalidates the bottom | Medium | Phase 1 absorbs the mechanical work, and the wide waves at the front mean the risky chain starts while the stack is short |

---

## 10. Decisions

Each records what was chosen and why. Where a choice was contested, the winning
reason is what matters.

| # | Decision | Rationale |
|---|---|---|
| 1 | Czech aliases carry no diacritics | The diagram itself uses both spellings; ASCII avoids every encoding failure on Windows consoles, CI logs and doc builds |
| 2 | Only classes the diagram names in Czech get an alias | The rest are already English in the diagram, so the code already matches |
| 3 | English canonical, Czech as aliases | Code calls English; the diagram stays discoverable from code and docs |
| 4 | `Knight` is canonical, `Kun` is its alias, `Horse` is removed | `Kůň` is the diagram's name; `Knight` is the international name and the alias avoids two names for one class |
| 5 | `Tower` is dropped | No counterpart in any diagram box, and dead code |
| 6 | `Controller` is dropped; the module becomes `game_manager_controller.py` | No diagram box; matches the diagram's `GameManagerController` and the sibling `window_controller.py` |
| 7 | No special handling for aliases in the docs | If mkdocstrings renders them they are visible; if it does not, that is acceptable |
| 8 | The settings layer is built | The mockup requires it and the diagram lacks it; recorded as a deviation |
| 9 | Rank-relative rules generalise rather than disable | The home rank and castling files are derived from the board, so en passant and castling work at any size |
| 10 | Rules and quests are the only code-driven layers, using one pattern | Data by default; code only where behaviour is genuinely needed. One pattern rather than an exception |
| 11 | Five rule hooks | Four cover game logic exhaustively — turn-based logic can only forbid a move or end the game — plus `status` for display. Check is not a game end, so folding it into `outcome` would have blurred the semantics |
| 12 | `Result` carries a precedence | Without it, two rules firing at once is ambiguous, and "any conceivable logic" collapses on the first collision |
| 13 | A rule's `value` persists, its `state` resets | Otherwise saving a configuration would save a game's history |
| 14 | No `define_ruleset` and no registry | A configuration is composed explicitly, so the rule type set is closed and greppable. A registry adds surface for nothing. **Amended 2026-10-05:** the closed, greppable set is the files in `rules/`, composed by `compose_section` rather than named in a tuple — see `notes/object_model.md` §25 |
| 15 | No `CustomBoard`, `CustomPiece` or `CustomQuest` types | Board, piece and quest customisation is already complete through data; these classes would wrap data that is already custom and exist only for symmetry |
| 16 | No condition class for quests | Two hierarchies would express the same thing. The pieces pattern settles it: `Pawn(Piece)` carries its own logic, with no strategy object underneath |
| 17 | The whole configuration is one file tree in Python | It cannot all be data — rules and quests carry logic — and one language avoids a format split and the `tomllib` availability problem on Python 3.10 |
| 18 | Configurations live in `games/`, outside the package | Keeps authored and built-in implementations out of the engine, and makes a configuration a copyable unit |
| 19 | One board per game | Duplication is already the mechanism for every other change, so multiple boards would have been the one place it was not |
| 20 | Piece symbols are declared data | The renderer and notation writer then hold no knowledge of piece types, which also removes the silent-pawn fallback |
| 21 | FEN characters are optional per piece | A custom piece has no FEN representation, and reporting that beats emitting something wrong |
| 22 | The king is a rule, not a type | Checkers has no king, and the engine must not know chess. Also removes the silent-failure coupling |
| 23 | FEN and PGN live in `games/chess/export/` | They are chess formats. A game with no FEN representation has no FEN exporter, because the structure says so rather than a runtime check |
| 24 | Every export format the diagram names is implemented | The diagram is the assignment specification; nothing in that box is negotiable |
| 25 | No format switch in the engine | One class per format extending a base is the `Extends` relation the diagram already draws |
| 26 | XP is derived from completed quests | `Uzivatel.splnene_kwesty` already holds them, so `User` gains no field and no deviation |
| 27 | The log directory is configurable, defaulting to `logs/`, git-ignored | A log with no configured destination persists nothing, so the directory is a requirement rather than a convention |
| 28 | The configuration selector exists only in settings | It means *which configuration am I editing*. The start modal is the only place a configuration is chosen to play, so editing cannot silently change what is about to be played |
| 29 | All data-based configuration is form-exposed | The code editor is for logic only. Requiring code to set a board size would make the editor the whole configuration surface |
| 30 | Backlog is one item: a no-code builder for rule logic | The code editor covers the full expressiveness of the hooks meanwhile, so nothing is unavailable while it waits |
| 31 | `src/` is flattened to the root | It removes the import-path and docs-configuration churn from every later PR |
| 32 | The project ships `checkers` | It is the executable proof of the abstraction, and it is self-verifying: if checkers needs an engine change that chess did not, the seam is wrong |
| 33 | Phase 1 changes no product behaviour | Every Phase 2 PR would otherwise carry mechanical churn alongside its real change, which makes review harder |
| 34 | Bot-authored pull requests are dropped | PRs are authored normally and the maintainer merges them |

---

## 11. Out of scope

| Item | Why |
|---|---|
| Network play | Not in the diagram, not requested |
| A no-code builder for rule logic | The single backlog item, tracked in issue #130 |
| Persisting a game in progress | Not in the diagram |
| A settings surface beyond the diagram's mockup | The mockup is a reference for layout and content, not a spec to reproduce exactly. Where the mockup and the diagram disagree, the diagram governs |
| Reinstalling the shared DarkFactory pipeline | Deliberately deferred; its pin is stale and the dependency is removed in PR 4 |
