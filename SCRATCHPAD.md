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
   registry. Everything else is data.
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
    quests/               composed in games/chess/__init__.py, not one file per quest
  checkers/             the second configuration
    board.py, moves.py, pieces/, rules/, clocks/, export/, quests/
chesswithquests/      the entry point, `python -m chesswithquests`
logs/                 game logs, configurable, git-ignored
tests/  notes/  theme/  .github/
```

`model/` keeps the parent classes — `Piece`, `Rule`, `Quest`, `Board`, `Clock` —
and the machinery every configuration shares: the move, the validator, the game
manager, the timer, the logger, the player, the user and the notation base.

**Everything in a configuration directory is a Python file.** It could not all be
data: rules and quests carry logic, so one language avoids a format split and
keeps the tree readable.

**A configuration is a folder that can be copied.** `cp -r games/chess
games/house`, change what differs, and a variant exists. `cp -r games/checkers
games/house` works the same way. Duplication is the extension mechanism. One game
runs one board. `model/game/configuration.py` loads a loaded directory as a
package rooted at itself, so a copy composes its own board, pieces, rules, clocks
and quests rather than the original's.

**One declared deviation from "one file per entry".** `games/chess/quests/` and
`games/checkers/quests/` declare no quest files; both compose their quests in the
configuration's `__init__.py`, because a configuration ships a handful of quests
rather than the whole library. The twenty quest classes live in
`model/game/quests.py`, which a configuration instantiates.

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

`pytest` is green and every test in it is behavioural. `black --check` clean.
`properdocs build --strict` clean, zero warnings.

**This section quotes no test count.** The stack is several pull requests deep and
grows as it merges, so a number written here is wrong the day after it is written.
Run `pytest -q` for the current count, and treat §4.3's dead-code sweep the same
way.

What exists is a playable chess product and a working draughts engine beside it.
The whole view layer, the game-loop wiring, both configurations and the rule and
quest hierarchies are built; §4.5 records which planned pull request delivered
each of them.

### 4.1 Gaps

| Gap | Evidence |
|---|---|
| **Export is the largest remaining hole.** No per-format writer class exists. `ChessNotationWriter` still lives in `model/misc/export_writers.py` and still switches on a format-name string in `export()` | `model/misc/export_writers.py:209`. `games/chess/export/` holds only `algebraic.py`, a coordinate conversion. `games/checkers/export/__init__.py` declares no exporters at all |
| **FEN writes four placeholder fields.** Castling rights, the en passant square, the halfmove clock and the fullmove number are written as `- - 0 1` whatever the game state | `model/misc/export_writers.py:178` |
| **PGN movetext is not SAN.** `to_pgn` writes each move's destination square, and the header falls back to `'[Event "Casual Game"]\n[Result "*"]'` when no `MetadataWriter` is passed | `model/misc/export_writers.py:180-206` |
| **Stenographic is a coordinate pair, not a stenographic record.** `to_stenographic` joins start and end squares per move, with no compression | `model/misc/export_writers.py:121` |
| **`pyproject.toml` does not ship `games/checkers`.** The package list names `games.chess` and its subpackages and omits `games.checkers` entirely, so an install finds chess and not the second configuration | `pyproject.toml:40` |
| **`ChessNotationWriter` is still an engine class.** `notes/object_model.md` section 7 places per-format writers in the configuration that uses them | `games/chess/__init__.py:build_exporters` isolates the import as a single line, so the move is one edit rather than a search |

`model/game/configuration.py` also carries `copy_configuration`,
`rename_configuration` and `delete_configuration`, which refuse the default
configuration — so FR-27 and FR-28 are enforced at the data layer whether or not a
widget calls them.

### 4.2 What the game loop does

`model/game/manager.py` drives one game from `new_game()` to a `Result`. It takes
its board, pieces, rules, quests, clocks and export writers from the
`Configuration` it is given and names none of them: there is no `chess` in it and
no `checkers` in it. `start_turn`, `make_move`, `get_valid_moves`, `cancel_move`,
`charge_turn`, `credit_increment`, `status`, `get_result`, `transcript` and
`save_log` are all reachable from a played game, and `view/player_game_view.py`
calls them. The six subsystems this file once described as orphaned are
constructed and driven: `UserManager` and `QuestManager` at `manager.py:84,89`,
`WindowController` by `view/app.py:42`, and `Configuration.exporters` supplies
the writers. `link_default_users` at `manager.py:113` registers a user per side
and links it to the player it controls, which is what makes a player a person
rather than a colour.

### 4.3 Dead code

The inventory this section used to carry is mostly resolved. Verified gone:
`Timer.countdown`, `Player.get_color`, `Player.get_user`,
`Player.get_elo_rating`, `UserManager.find_user`, `GameManager.possible_moves`,
`Quest.complete`, `Board.setup_default_board`, and the names `Tower`, `Horse` and
`Controller`. The board's starting position moved out of the engine entirely:
`games/chess/board.py` and `games/checkers/board.py` declare it.

Several members this section once called dead are alive and must not be touched:
`Board.dimensions` (`board.py:103,111`), `Board.captured_white`
(`board.py:57,176`, read by `move.py:165,210`), `Move.promotion_piece`
(`move.py:93,185`), `ExportWriter.field`, `GameManager.players` and
`WindowController.title`, `width` and `height`. `Move.captured_piece` is no longer
declared on `Move`; `HopMove` carries it, together with `captured_pieces`, and the
quests read it.

What is unreferenced, by a textual sweep of all 222 public callables and methods
under `model/`, `controller/`, `view/`, `games/` and `chesswithquests/` against
the source and the suite. The sweep counts name occurrences, so it is a screen and
not a verdict — a name shared with a member elsewhere counts as referenced.
**This is a snapshot of one commit; re-run it rather than trusting it.**

| Unreferenced | Note |
|---|---|
| `GameManager.start_turn` | the loop's turn entry point; the view opens a turn through `get_valid_moves` instead |
| `GameManager.cancel_move` | no caller; a UI affordance with no caller yet |
| `GameLogger.file_path` | a getter with no reader |
| `MoveValidator.set_board` | a setter the validator is constructed with instead |
| `Field.field_values` (`model/game/field.py`) | no reader |
| `ResultEvent.moves_by` (`model/game/events.py`) | no reader |
| `QuestManager.register_quest` | no reader; the manager is populated at construction |
| `PlayerGameView.start_auto_refresh` | no reader; the clock ticks are driven explicitly |
| `longest_chain` (`games/checkers/rules/chains.py`) | no reader |
| `FiftyMoveRule.reset_count` (`games/checkers/rules/draws.py`) | no reader |
| `_SourceLoader.create_module` (`model/game/source_validation.py`) | **not dead**: the import machinery calls it. Do not remove, and exclude it when re-running the sweep |

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

Nine of the twenty-one are delivered in the main stack, three are delivered on
branches outside it, and the rest are partial or not started. **"Delivered" means
the acceptance criteria are met, not that a branch was opened.**

| Planned PR | Content | State | Where |
|---|---|---|---|
| 1 | PRD + SCRATCHPAD | **delivered** | main stack |
| 2 | Flatten `src/` to root, generated docs pipeline | **delivered** | main stack |
| 3 | Delete metadata-only tests, close docstring gaps, drop unused aliases | **delivered** | main stack |
| 4 | CI: native self-contained workflows, remove DarkFactory | **delivered, outside the main stack** | `feature/native-ci-workflows` |
| 5 | Governance rules: `AGENTS.md` 1, 2, 4, 7, 9, 10, 11, 12 | **delivered, outside the main stack** | `feature/governance-rules`, on top of PR 4 |
| 6 | Packaging, entry point, git-ignored log directory | **delivered** | main stack |
| 7 | README honesty | **not started in the main stack**; `feature/readme-honesty` holds a rewrite that predates the view layer, `games/` and the packaging, so every claim in it is now false. It must be superseded, not merged — see §4.6 | `feature/readme-honesty` |
| 8 | Board generalisation | **delivered** | main stack |
| 9 | `Quest` parent with built-in subclasses | **delivered** — twenty classes, split twelve `after_move` and eight `at_game_end` | main stack |
| 10 | `Rule` parent, five hooks, configuration loading | **delivered** | main stack |
| 11 | Orthodox chess rules, removal of type coupling | **delivered** — thirteen `Rule` subclasses, and no `getType()`/`hasattr` coupling anywhere under `model/`, `controller/` or `view/` | main stack |
| 12 | Multi-hop moves | **delivered, as a different design from the one planned** — `Move` is unchanged and `games/checkers/moves.py` declares `HopMove(Move)`, which carries the hops. See §4.7 | main stack |
| 13 | Migrate chess into `games/chess/` | **delivered** | main stack |
| 14 | Wire the orphan subsystems | **delivered** | main stack |
| 15 | View layer with the game-start modal | **delivered** — `BoardView`, `PlayerGameView`, `PlayerView`, `QuestCard`, `QuestList`, `StartModal` | main stack |
| 16 | Settings surface | **delivered** — the five sections, the corner configuration selector with create/rename/delete/duplicate, and a code editor that validates before the code joins a configuration | main stack |
| 17 | `games/checkers/` | **partial** — the board, two piece kinds, eight rules, the clock and four quests, held to the published perft counts. Absent: its two exporters, *letter* and the metadata header | main stack |
| 18 | Export generalised | **not started** — the `ExportWriter` base and `formats()` exist, but the format switch does, and there is no per-format subclass in `games/<variant>/export/` | — |
| 19 | Export formats: PGN, FEN, field-field-extra, stenographic | **not started** | — |
| 20 | Czech aliases and remaining dead code | **partial** — all fifteen aliases ship, `Knight` is canonical, `Tower`, `Horse` and `Controller` are gone. Absent: the `controller/controller.py` → `game_manager_controller.py` rename, and the dead-code re-check | main stack |
| 21 | Behavioural test coverage | **partial** — no surviving test asserts on repository metadata, and §4.3's list is unreferenced rather than untriaged | main stack |

### 4.6 The stack has grown past twenty-one

The twenty-one are the plan; the branches are the truth. Four items were added to
the main stack after the plan was written, and each is a real pull request:

| Added item | What it is | Where |
|---|---|---|
| The perft gate | Draughts move generation held to the published perft counts, and chess perft(4) corrected | `tests/test_draughts_perft.py`, `tests/test_perft.py` |
| The engine-leakage cleanup | `tests/test_engine_holds_no_chess.py`, which asserts the invariant the plan stated and the code had broken | main stack |
| The knight rename | `Horse` → `Knight`, with `Kun` as the alias and `games/chess/pieces/knight.py` as the file | main stack |
| The checkers configuration | `games/checkers/` as its own directory | main stack |

**`feature/readme-honesty` and `feature/native-ci-workflows` are not on the main
stack**, and neither is `feature/governance-rules`, which is built on
`feature/native-ci-workflows`. Planned PR 4 and PR 5 therefore exist only there.
Any statement in this file about PR 4, PR 5 or PR 7 describes work a reader of the
main stack cannot see.

**The plan issues' labels lag their contents.** #127 (PR 1) and #129 are labelled
`In Progress`; #126 (PR 4) and #124 (PR 5) carry no status label at all, though
both are delivered; #131 covers PRs 2, 3, 6 and 7, of which only 7 is outstanding.
Move them to `Done` when the pull requests merge.

### 4.7 Multi-hop moves were not built as planned

Planned PR 12 and `notes/object_model.md` section 11 both say `Move` grows a
sequence of hops alongside `start_pos` and `end_pos`. **It does not.** `Move`
carries a start, an end, a piece, a move type and an optional promotion piece,
and nothing else. `games/checkers/moves.py` declares `HopMove(Move)`, which adds
`hops`, `captures`, `captured_pieces` and `route`, and overrides
`apply_to_board`; the engine's `unapply_from_board` is reused verbatim, because
`HopMove` returns the engine's own `Applied` record.

This is the better outcome — nothing under `model/`, `controller/` or `view/`
grows a draughts-shaped member, and `notes/object_model.md` section 11 now records
it — and the plan is what is wrong.

---

## 5. Test strategy

Current: every test in the suite is behavioural. Target: behaviour-only, and that
is where the suite is.

**The metadata assertions are gone.** Planned PR 3 deleted the sixty-two tests
that asserted on repository metadata rather than on the product — import smoke
tests, workflow YAML, `AGENTS.md` text, the `CLAUDE.md` symlink, `README.md`
URLs, and the notes files. Two consequences for anyone reading this section:

- **The tests that police the rulebook are deleted, not rewritten.** Nothing in
  the suite now keeps `AGENTS.md`, `README.md` or a workflow honest. That is the
  decision `PRD.md` section 3.2 records, and it means the documents in this
  repository are maintained by reading them, not by running a test.
- **The one test that asserted on notes content has been rewritten, not
  deleted.** `tests/test_docs_and_docstrings.py` held a test that read the real
  `notes/*.md` files from disk and asserted the generated pages equalled them
  byte for byte, plus substring assertions on the notes' text. That is a
  metadata assertion wearing a behavioural hat: it would pass with the product
  deleted. It is now driven from `tmp_path`, so it asserts what
  `.github/scripts/docs_hooks.py` *does* — that every Markdown file in a notes
  directory is published verbatim and linked from a hub page — against a fixture
  it owns, and it reads nothing from the repository.

**What the suite covers that it did not.** The perft gate for chess and draughts,
the engine-holds-no-chess invariant, the rules of draughts position by position,
the copied-configuration boundary, the game loop end to end, the alias table,
the manager reading its writers and quests, and the configuration directory
operations.

**What PR 21 still owes.** §4.3 lists what is unreferenced; unreferenced is not
the same as uncovered, and PR 21 is the pass that distinguishes them. Two
coverage gaps this file recorded earlier are closed — a `Board` of non-8×8
dimensions is built and played on in `tests/test_board_generalisation.py`, and
`ChessNotationWriter.export` is exercised by `tests/test_manager_exporters.py` —
and the export writers' *outputs* remain largely unverified because the outputs
are largely wrong (§4.1).

---

## 6. Phase 1 — quick wins

No product behaviour changes. Reviewed and merged one at a time before Phase 2
begins. **The maintainer merges; do not merge.**

| PR | Content | Needs | State |
|---|---|---|---|
| 1 | PRD + SCRATCHPAD | — | delivered |
| 2 | Flatten `src/` to root, and reconfigure the docs pipeline with it | 1 | delivered |
| 3 | Delete metadata-only tests, close docstring gaps, drop the unused aliases | 2 | delivered |
| 4 | CI: native self-contained workflows, then remove the DarkFactory dependency | 3 | delivered on `feature/native-ci-workflows` |
| 5 | Governance rules: `AGENTS.md` 1, 2, 4, 7, 9, 10, 11, 12 | 4 | delivered on `feature/governance-rules` |
| 6 | Packaging, entry point, and the git-ignored log directory | 2 | delivered |
| 7 | README: stop claiming what the product does not yet do | 1 | not started; see §4.5 |

**The order is load-bearing.** PR 4 deletes `.github/darkfactory.json` and the
workflows that `tests/test_workflow_rules.py` and
`tests/test_auto_format_workflow.py` assert on; PR 5 rewrites `AGENTS.md` Rules 7
and 11, which those tests also assert on. Both would land red. PR 3 removes the
tests, so it must precede them.

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
`AGENTS.md`, a workflow, `notes/` or `README.md`; both `Returns:` gaps closed; the
only remaining `pass` is `ExportWriter.export`'s abstract raise; and no note file
describes a class or member the diagram does not draw.

**Risk**: deleting tests could mask regressions. Every deletion is import-only or
metadata-only, and PR 21 adds behavioural coverage to offset.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.

### PR 4 — CI: native workflows, then remove DarkFactory

**State**: delivered on `feature/native-ci-workflows`, which is not on the main
stack.

**Goal**: the repository's CI depends on no external repository's workflow.

11 of 12 workflows are thin delegates to `marius-patrik/DarkFactory` at the
pinned ref `7ecba16` in `.github/darkfactory.json`.

**Delete**: `.github/darkfactory.json`, `agent.yml`, `open-pr.yml`,
`pr-approval-automerge.yml`, `project-automation.yml`, `report-failure.yml`, the
`pipeline` git remote, the empty gitignored `.pipeline/`, and `AGENTS.md` Rule
13.

**Reimplement natively and self-contained**: `ci.yml` (matrix `3.10`–`3.13`,
pytest plus black), `auto-format.yml`, `deploy-docs.yml`, `preview-docs.yml`,
`release.yml`, `verify-pr-issue.yml`.

**Unchanged**: `verify-docs.yml` is already self-contained.

**Order inside the PR — non-negotiable**: land the replacement `ci.yml` and
`auto-format.yml` first and get them green, *then* remove the delegates. The
repository must never sit without working required checks.

**Acceptance criteria**: `git remote -v` shows only `origin` and `upstream`; no workflow
contains a `uses:` pointing at **another repository's workflow** — `actions/checkout`
and `actions/setup-python` are expected and are not a DarkFactory dependency; CI green on all four Python
versions.

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
- **Rule 12** — it requires a `Request` issue per prompt with a linked `Plan`
  child and an `approve` comment, enforced by that same deleted workflow. Keep the
  discipline, drop the claim of automated enforcement, and note that this track's
  Request and Plan issues are #123 to #130.

**Acceptance criteria**: no rule references `.github/darkfactory.json`,
`open-pr.yml`, or a bot author; no rule claims automated enforcement by a workflow
PR 4 deletes; Rule 4 permits Czech aliases; Rules 1 and 2 name the flattened
layout and `properdocs`.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.

### PR 6 — Packaging, entry point, and the log directory

**State**: delivered, with one gap — `pyproject.toml` ships `games.chess` and
omits `games.checkers` (§4.1).

Add a `[project]` table and a build backend. **`packages` must be set
explicitly** — a flat layout plus setuptools auto-discovery trips over `tests/`
sitting at the root.

**Three things the product needs that have no other home:**

1. **An entry point.** `python -m <entrypoint>` must start a window (FR-58).
2. **`games/` must ship with the package.** It sits outside `model/`,
   `controller/` and `view/`, so an install shipping only packages would not find
   its own default configuration and every later phase would look broken. Either
   declare the configurations as package data or have the loader locate them
   relative to the installed distribution.
3. **`logs/` must be git-ignored.** FR-55 requires it; `.gitignore` has no such
   entry today.

**Acceptance criteria**: the package builds and installs; `pip install .` in a
clean venv imports `model`, `controller` and `view` **and finds `games/chess/`**;
the entry point starts the application; `git check-ignore logs/` succeeds; no
runtime dependency is declared beyond the standard library.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.

### PR 7 — README honesty

**State**: not started on the main stack. `feature/readme-honesty` holds a
rewrite that predates the view layer, `games/` and the packaging, so every
capability claim in it is now false; supersede it rather than merge it (§4.5).

**Goal**: `README.md` stops claiming what the product does not yet do. It
currently advertises "custom board configurations", which is false until PR 8.
State what is true, and add the documentation and diagram links it already has.

**Acceptance criteria**: every capability claimed in `README.md` is covered by a passing
test.

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
Three edges have been satisfied out of order and the plan does not say so: PR 12
needed only PR 10 and landed with the checkers configuration, PR 17 landed
without PR 18 and is therefore partial, and PR 20's alias half landed without
PR 15 or the `controller.py` rename. Nothing else in the graph moved.

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

`Move` is left alone and a `Move` subclass carries the hops. `HopMove(Move)` adds
`hops`, `captures`, `captured_pieces` and `route`, overrides `apply_to_board`,
and reuses the engine's `Applied` record so the engine's `unapply_from_board`
undoes a chain with no second mechanism.

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

**State**: delivered — thirteen rules, and no coupling left in the engine.

**Needs**: 10. **Blocks**: 13, 14, 18.

**Goal**: every rule in `notes/chess_rules.md` implemented, and the engine stops
knowing what a king is.

**Thirteen chess rules** as `Rule` subclasses in `games/chess/rules/`, one per
file:

| Class | Rule |
|---|---|
| `CastlingRule` | castling |
| `EnPassantRule` | en passant |
| `PromotionRule` | promotion |
| `CheckRule` | check |
| `CheckmateRule` | checkmate |
| `StalemateRule` | stalemate |
| `InsufficientMaterialRule` | insufficient material |
| `FiftyMoveRule` | the fifty-move rule |
| `ThreefoldRepetitionRule` | threefold repetition |
| `MutualAgreementRule` | mutual-agreement draw |
| `FlagFallRule` | loss on time, and only where the opponent retains mating material |
| `BishopColourRule` | each bishop confined to the shade of square it started on |
| `RoyalPieceKind` | which piece kind may be put in check |

**The count this file used to give was eleven, and two rules were outside it.**
`BishopColourRule` was never named anywhere in this file, though
`notes/chess_rules.md` section 2 mandates the confinement it enforces.
`RoyalPieceKind` was named in the same sentence as the count and not counted; it
is a `Rule` subclass like the other twelve, which is why the count was eleven
where the directory holds thirteen. It declares a kind rather than judging a
position, and FR-14 is what it exists for.

**Also removes**, from the validator: `find_king`, `is_check`, `is_checkmate`,
and every `getType() == "king"` / `== "pawn"` comparison and every `hasattr`
probe. Those become behaviour of the chess configuration. The three remaining
`getType()` comparisons are in `games/chess/rules/` — `attacks.py`, `castling.py`
and `draws.py` — which is where they belong.

Rank-relative rules generalise: the home rank, the knight-forward file and the
castling rook files are derived from the configured board rather than assumed to
be 1, 8 and `a`–`h`.

**Acceptance criteria**: each rule passes a game with it enabled and a game with it disabled,
and the difference is the setting rather than a code path; no `getType()` or
`hasattr` coupling is left anywhere under `model/`, `controller/` or `view/`; a
custom piece whose kind is not `"king"` neither crashes nor silently disables
check.

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

### Wave C — three PRs

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 14 — Wire the orphan subsystems

**State**: delivered.

**Needs**: 9, 11. **Blocks**: 15.

`QuestManager`, `UserManager`, `User`, `MetadataWriter`, `ChessNotationWriter`,
`WindowController` are instantiated and driven by the game loop.
`GameManager.players` is linked to users. `Timer.add_time` actually applies
increment. The `hasattr(user, "add_quest")` probe becomes a real call:
`manager.py:375` calls `user.add_quest(quest)`.

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

**State**: not started.

**Needs**: 11. **Blocks**: 17, 19.

One class per format extending `ExportWriter`, living in `games/<variant>/export/`.
The `format_type` switch in `ChessNotationWriter.export` and the format-name
string are deleted — that is the `Extends` relation the diagram draws. Ship the
mechanism plus *letter* (algebraic) and the metadata header, both of which the
game needs immediately.

**Acceptance criteria**: no format switch and no format-name string exists anywhere in the
engine; adding a format is one file and no engine change; the metadata header is
derived from the players and result, with no placeholder strings.

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
one renderer turns that declaration into widgets. Sections for Board, Pieces,
Rules, Quests, Clocks. A corner selector meaning *which configuration is being
edited* — settings only. An "edit logic" code editor for rules and quests,
writing into the configuration directory and validating before the code may join.

**Acceptance criteria**: a form is assembled for each section without hand-built widgets; a
new field kind is one widget and every section inherits it; the editor refuses
invalid code and reports the error in the editor; a configuration can be created,
renamed, duplicated, edited, deleted and copied as a folder.

**Needs**: 15. **Blocks**: 20.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 17 — `games/checkers/`

**State**: partial — the game is delivered and held to the published perft
counts. Its two exporters are not.

**Needs**: 12, 13, 18 — it ships *letter* and metadata exports, and PR 18 is what makes those possible. **Blocks**: 21.

Full English draughts: twelve pieces a side, men moving one square forward
diagonally, kings sliding any distance diagonally, **mandatory capture including
chains**, promotion to king on reaching the far rank, and a win by immobilisation
or by losing all pieces. Exports: *letter* and the metadata header. **No FEN** —
a draughts position has none, and the structure says so rather than a runtime
check.

**This PR is the executable proof of the abstraction.** If it needs an engine
change that chess did not, the seam is in the wrong place — treat that as a
failure of the abstraction, not of the PR.

**Acceptance criteria**: **zero engine changes**; mandatory capture is one `permits_move`
rule; a three-capture chain is offered as one move; a man reaching the far rank
is crowned; a player with no legal move loses; nothing in the engine mentions a
king, a pawn, a check or a mate.


**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 19 — Export formats

**State**: not started.

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

**Quality gates**

1. `pytest` green, and no surviving test asserts only on repository metadata.
2. Every public method is reachable from at least one test.
3. `black --check .` clean at line length 100.
4. `properdocs build --strict` clean, zero warnings.
5. No third-party runtime import anywhere under the project source.
6. No board dimension is hard-coded outside `Board.DEFAULT_DIMENSIONS` and a configuration's own `DIMENSIONS`. The invariant is asserted against the board API, not by grepping every `8` in the tree — docstrings legitimately say "8-direction" and file paths contain `utf-8`.

**Rules and configurations**

7. `Rule` has the five hooks, each defaulting permissively, and `Result` carries
   a kind, a precedence and an optional winner.
8. Every rule in `notes/chess_rules.md` implemented, each driven on and off
   through one game.
9. Logic beyond any shipped set is expressible without touching the engine.
10. Two colliding rules resolve by precedence, tested with rules written to
    collide.
11. A rule's configured `value` persists; its runtime `state` resets each game
    and never reaches disk.
12. Those rules hold on non-8×8 boards, rank-relative rules generalised.
13. A move may consist of several hops.
14. Nothing in the engine mentions a king, a pawn, a check or a mate.

**Quests**

15. `Quest.validate()` takes no arguments and matches the diagram.
16. Every built-in quest completes on its intended event and not before.
17. Quests in play and quests completed are held separately; XP is derived.

**Configurations**

18. `chess` plays orthodox chess with nothing configured, and cannot be edited or
    deleted.
19. A configuration is a directory that can be copied to create a variant.
20. `checkers` is full English draughts and requires **no engine change**, and it
    offers the two formats that mean something for it.

**Interface**

21. Starting a game shows the modal with configuration selector, Settings and
    Start.
22. Every data-based configuration is form-exposed from one renderer.
23. The editor refuses invalid code before it joins a configuration.
24. A game is played end to end from the entry point to a result.
24a. `games/` ships with the installed package, so a clean install finds its own
    default configuration **and the second one** — `pyproject.toml` lists
    `games.chess` and omits `games.checkers` today (§4.1).

**Export**

25. Every format the diagram names is implemented: *letter*, *PGN*, *FEN*,
    *Field - Field - Extra*, *Stenographic*, and the game transcript.
26. No format switch and no format-name string exists in the engine.
27. FEN round-trips for the three positions named in the product requirements.
28. PGN movetext is genuine SAN, verified against known-good PGN.

**Object model and hygiene**

29. All fifteen Czech aliases importable and identical to their canonical
    objects; `Tower`, `Horse` and `Controller` gone.
30. Every deviation recorded in `notes/object_model.md` with approval context.
31. `notes/chess_rules.md` amended where board generalisation departs from it.
32. Nothing in §4.3's unreferenced list survives the PR 20 re-check; the §4.4
    docstring gaps are closed.
33. CI green across `3.10`, `3.11`, `3.12`, `3.13`, depending on no external
    repository's workflow.

---

## 9. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Real PGN requires SAN disambiguation, which is easy to get subtly wrong — `Nbd7` versus `N1d7` versus `Nd7` | High | Each case gets its own test: two knights, three queens, two rooks on one rank, a pinned piece that can still legally reach the square, promotion capture. A round-trip against known-good PGN is the backstop |
| `getType()` and `hasattr` coupling fails **silently** on rename or on a custom piece | High | PR 11 removes it. PR 20 ships tests that fail when a probe breaks, not only when a name changes |
| The flatten makes the whole repo the docs tree, and `exclude_docs` has to do work `docs_dir: src` did by construction | High | PR 2. Fallback is a dedicated docs directory rather than widening the tree |
| A flat layout breaks setuptools auto-discovery over `tests/` | Medium | PR 6 sets `packages` explicitly |
| Removing DarkFactory leaves the repository without working required checks | High | PR 4 lands the replacement and gets it green before removing anything |
| `checkers` needs an engine change that chess did not | High | That is the point of shipping it. Treat it as a failure of the abstraction and fix the abstraction, not the game |
| A multi-hop move model change destabilises ordinary single-hop moves | Medium | PR 12 tests a one-hop move through the same path as a three-hop chain |
| Deleting 62 tests masks a regression | Medium | Every deletion is import-only, metadata-only, or a `docs_hooks.py` test rewritten to avoid asserting on `notes/` content. PR 21 adds behavioural coverage |
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
| 14 | No `define_ruleset` and no registry | A configuration is composed explicitly, so the rule type set is closed and greppable. A registry adds surface for nothing |
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
