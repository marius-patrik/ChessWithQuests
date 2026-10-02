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
9. **One transitional contradiction is live until PR 5 lands, and is expected.**
   `AGENTS.md` Rule 4 states that all identifiers are English, which contradicts
   the fifteen Czech aliases `PRD.md` section 5 requires. `AGENTS.md` governs
   until amended, so an agent working from the rule text alone will write the
   aliases *out*. **PR 5 closes this.** Until it merges, the aliases are the later
   and more specific statement, recorded with approval in
   `notes/object_model.md` section 1. No other contradiction between `AGENTS.md`
   and this plan survives.

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

## 2. Target repository layout

```
controller/   model/   view/        the engine
model/                          parent classes + shared machinery
games/
  chess/                        default configuration, shipped
    board.py                    rows, columns, starting placement
    pieces/                     one file per piece
    rules/                      one file per rule
    quests/                     one file per quest
    clocks/                     clock configuration
    export/                     one file per export format
  checkers/                     second configuration, shipped
logs/                           game logs, configurable, git-ignored
tests/  notes/  theme/  .github/
```

`model/` keeps the parent classes — `Piece`, `Rule`, `Quest`, `Board`, `Clock` —
and the machinery every configuration shares: the move, the validator, the game
manager, the timer, the logger, the player, the user and the notation base.

**Everything in a configuration directory is a Python file.** It could not all be
data: rules and quests carry logic, so one language avoids a format split and
keeps the tree readable.

**A configuration is a folder that can be copied.** `cp -r games/chess
games/house`, change what differs, and a variant exists. Duplication is the
extension mechanism. One game runs one board.

---

## 3. How to read the pull-request numbers

This manual numbers **planned** pull requests 1 to 21. Those numbers are **not**
GitHub pull-request numbers — the repository already has merged pull requests
numbered 1 to 105, and this document's own pull request is **128**. Every "PR N"
below means *the planned pull request with that number here*. Do not type a
planned number into the GitHub interface.

Each planned pull request becomes a real GitHub pull request when executed, and
the plan issue it belongs to is named in that issue's `Placement` section.

---

## 4. Current state

`138` tests pass. `black --check` clean. `properdocs build --strict` clean.

What exists is a competent chess **model** — board, move, validator,
check/checkmate/stalemate, timer, logger, notation, quest and user types — with
thorough Google-style docstrings and no third-party imports.

**Path convention**: `file:line` references below are written in the post-flatten
layout, which is PR 2. The audit ran against the pre-flatten tree, so a path that
does not resolve yet is expected and is not by itself a defect.

### 3.1 Gaps

| Gap | Evidence |
|---|---|
| **The entire view layer** | `view/__init__.py` is one docstring line. No GUI, no renderer, no entry point |
| **Most chess rules** | Check, checkmate and stalemate **are** implemented and wired into `get_state`. Absent: castling, en passant, promotion wiring, fifty-move, threefold repetition, insufficient material, mutual-agreement draw, the flag-fall nuance, and the bishop colour confinement `notes/chess_rules.md` also mandates. `King._has_moved` and `Rook._has_moved` are read only by their own getters and are consulted by no rule |
| **Board size hard-coded** | Nine sites assume 8×8: `move.py:44,46`, `board.py:41,134,138-146`, `export_writers.py:77,80`, `validator.py:101,187`. `board.py:26` holds the exempt `Board` default |
| **Engine hard-codes chess** | Eight coupling sites in the two files PR 11 rewrites — five `getType()` and two `hasattr` in `validator.py`, one `hasattr` at `board.py:106`. Eight further occurrences live in `export_writers.py`, `logger.py`, `player.py`, `quest_manager.py` and `users/manager.py`, which PR 11 must also handle. A missed probe returns `False` rather than raising, so check and checkmate fail **silently** |
| **Not a running application** | No `[project]` table, no build backend, no entry point. Importable only because pytest sets `pythonpath` |
| **Subsystems never wired** | Four are imported by nothing else and never constructed: `QuestManager`, `UserManager`, `ChessNotationWriter`, `WindowController`. Two more are imported but unused: `User` by `users/manager.py`, `MetadataWriter` by `export_writers.py`. None of the six is ever constructed |
| **Export is wrong** | `export_writers.py:101` hard-codes castling, en passant, halfmove and fullmove, so every export past move 1 is invalid. `to_pgn` emits destination squares labelled as PGN. `metadata.py:21-22` hard-codes `"White": "Player 1"`. `PIECE_CHARS` is an engine table and unknown types serialise as pawns |
| **Multi-hop moves unsupported** | `Move` is `start → end`. A checkers capture chain is one move |
| **Logging writes nothing by default** | `GameLogger()` with no filename persists nothing and nothing calls it with a path |

### 3.2 Why the integration gap matters most

The feature count looks high and the wiring is zero. `GameManager.players` is
created at `manager.py:48` and never read, so players are never linked to users
and never consulted by move execution or state evaluation. Six subsystems were
built standalone and never connected to a game.

### 3.3 Dead code

**Never called from any other module.** `GameManager.start_turn:55`,
`cancel_move:74`, `save_log:78` (the only `pass` in the package),
`MoveValidator.set_board:32`, `GameLogger.file_path:58`, `Timer.add_time:51`
(tests only), `ChessNotationWriter.export:138`, `ExportWriter.export:20`,
`Quest.complete:48` (tests only).

**Already called — not dead, do not remove.** `MoveValidator.is_square_attacked:68`
is called internally at `:134`. `Board.setup_default_board:119` is called from the
constructor at `board.py:42`.

**Aliases with zero references.** `Tower` `tower.py:11`, `Controller`
`controller.py:97`, `Horse` `horse.py:42`, `Timer.countdown:49`,
`Player.get_color:58`, `Player.get_user:59`, `Player.get_elo_rating:57`.

**Aliases referenced only by tests.** `Knight` `horse.py:42` (`test_horse.py`),
`Controller` `controller.py:97` (`test_controller.py`),
`GameManager.possible_moves:72` (`test_game_manager.py`),
`UserManager.find_user:50` (`test_user_manager.py`). Removing one breaks a test,
so each needs its call sites updated rather than deleted in place.

**Written but never read.** `Board.captured_white:38` and `Move.captured_piece:32`
are assigned and never consulted. `GameManager.players:48` is created and read
only by a test. `WindowController.title/width/height:28-29` are stored and never
read. `ExportWriter.field:18` is never read.

**Already read — not dead, do not remove.** `Move.promotion_piece:33` is read at
`move.py:75`. `GameManager.STATE_CHECK:25` is returned at `manager.py:96`.
`Board.dimensions:33` is asserted by `test_board.py`. `Player.user` is read at
`player.py:49-52` and set by `test_player.py`.

Several become live once PR 14 wires the subsystems. **PR 20 re-checks each one
and removes only what is still dead** — an attribute written in anticipation of a
consumer that now exists must not be deleted.

### 3.4 Docstring gaps

Two concrete violations: `export_writers.py:20` (`ExportWriter.export` returns
`str`, no `Returns:`) and `logger.py:58` (`GameLogger.file_path` returns
`Optional[str]`, no `Returns:`). Plus a leftover `__main__` demo block at
`piece.py:94-97` in library code. All three are PR 5.

Coverage is otherwise complete: every module, class and method has a docstring,
and `Args:` is present for every non-self parameter.

---

## 5. Test strategy

Current: `138` tests. Target: behaviour-only.

**Delete outright** — 62 of the 138 assert nothing about the product:

| File | Tests | Why |
|---|---|---|
| `tests/test_structure.py` | 27 | `importlib.import_module(...) is not None`. Proves a module parses, nothing more |
| `tests/test_auto_format_workflow.py` | 2 | Asserts on `auto-format.yml` content and the `darkfactory.json` pin |
| `tests/test_workflow_rules.py` | 15 | Asserts `AGENTS.md` text, workflow YAML and pipeline pins |
| `tests/test_claude_symlink.py` | 3 | Asserts a symlink target and `.agents/` existence |
| `tests/test_readme.py` | 1 | Asserts `README.md` contains three URLs |
| `tests/test_chess_rules_notes.py` | 1 | Asserts keywords in `notes/chess_rules.md` |
| `tests/test_object_model_notes.py` | 1 | Asserts a URL and phrases in `notes/object_model.md` |
| `tests/test_reference_diagram_notes.py` | 1 | Asserts a diagram id in `notes/reference_diagram.md` |
| `tests/test_docs_and_docstrings.py` | 10 of 12 | The docstring-presence and strict-build checks stay. Seven of the ten removed are behavioural tests of `.github/scripts/docs_hooks.py`; they are rewritten, not lost |
| **Total** | **62** | |

PR 5 performs the deletions. PR 21 replaces them with behavioural coverage.

**Known coverage gaps to close.** `GameManager.start_turn`, `cancel_move`,
`save_log`, `STATE_CHECK`, `MoveValidator.set_board`, `is_square_attacked`,
`GameLogger.file_path`, `Board.captured_white`, `Move.captured_piece`,
`ChessNotationWriter.export`, `Timer.add_time`, `Board.setup_default_board`, and
any `Board` constructed with non-8×8 dimensions.

---

## 6. Phase 1 — quick wins

No product behaviour changes. Reviewed and merged one at a time before Phase 2
begins. **The maintainer merges; do not merge.**

| PR | Content | Needs |
|---|---|---|
| 1 | PRD + SCRATCHPAD | — *(in review)* |
| 2 | Flatten `src/` to root, and reconfigure the docs pipeline with it | 1 |
| 3 | Delete metadata-only tests, close docstring gaps, remove the `piece.py` demo block | 2 |
| 4 | CI: native self-contained workflows, then remove the DarkFactory dependency | 3 |
| 5 | Governance rules: `AGENTS.md` 1, 2, 4, 7, 9, 10, 11, 12 | 4 |
| 6 | Packaging, entry point, and the git-ignored log directory | 2 |
| 7 | README: stop claiming what the product does not yet do | 1 |

**The order is load-bearing.** PR 4 deletes `.github/darkfactory.json` and the
workflows that `tests/test_workflow_rules.py` and
`tests/test_auto_format_workflow.py` assert on; PR 5 rewrites `AGENTS.md` Rules 7
and 11, which those tests also assert on. Both would land red. PR 3 removes the
tests, so it must precede them.

### PR 1 — PRD and SCRATCHPAD

The requirements and this manual. *(already open for review)*

**Acceptance criteria**: every FR reference resolves across all tracked sources;
every PR number in this file falls within 1–21; the definition of done, the risk
table, the dependency graph and the decision log are present and internally
consistent; `pytest`, `black --check` and `properdocs build --strict` are green.

**Verification**: `pytest -q`, `black --check .`, `python -m properdocs build
--strict`, and a cross-reference sweep of every FR and PR reference.
### PR 2 — Flatten `src/` to root, and reconfigure the docs pipeline

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
### PR 3 — CI: native workflows, then remove DarkFactory

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
### PR 4 — Governance rules

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
### PR 5 — Cleanup

**Goal**: remove what asserts nothing about the product.

Perform the deletions in §4. Close the two docstring gaps and remove the
`piece.py` demo block. Remove the dead aliases listed in §4.3 that do not
collide with the rename: `Timer.countdown`, `Player.get_color`,
`Player.get_user`, `Player.get_elo_rating`, `UserManager.find_user`.
`Tower`, `Horse` and `Controller` are removed in PR 20 with the rename.

**Also corrects two notes that are stale against the diagram**, cheaply, while
the note tests are being removed anyway:

- `notes/reference_diagram.md` documents `Tower` as a diagram class, `Kůň` as
  "`Horse` / `Knight`", `GameController` (the diagram's box is
  `GameManagerController`), `WindowController` (no such box exists), `Quest` as
  having "conditional predicates" (it has none), `Figurka` as carrying
  `can_jump` (declared on the six subclasses, not the parent), `MetadataWriter`
  as a "PGN header tags roster" (the box says "no parameters") and `Timer` as
  handling "time increment management" (no increment is drawn). Correct all of
  it against the diagram.
- `notes/chess_rules.md` reads `### Knight (N / Horse)`; `Knight` is canonical.

**Acceptance criteria**: `pytest` green at the reduced count; no test opens
`AGENTS.md`, a workflow, `notes/` or `README.md`; both `Returns:` gaps closed; the
only remaining `pass` is `ExportWriter.export`'s abstract raise, with `save_log`
either implemented or explicitly listed for PR 20; and no note file describes a
class or member the diagram does not draw.

**Risk**: deleting tests could mask regressions. Every deletion is import-only or
metadata-only, and PR 21 adds behavioural coverage to offset.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
### PR 6 — Packaging, entry point, and the log directory

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

**Goal**: board size is not restricted to 8×8.

**Scope**: the nine board-dimension sites listed in §4.1. `Move.validate` takes its bounds from the
board rather than a literal. `Board.setup_default_board` no longer silently
yields an empty board for a non-8×8 size. `MoveValidator` ray lengths come from
the board dimensions. FEN rank and file iteration comes from the board.

**Do not** change chess behaviour — the rules that depend on the home rank land
in PR 11.

**Acceptance criteria**: a `Board` of any dimensions can be constructed,
populated and moved on; `Move.validate` accepts an in-bounds move on any size and
rejects an out-of-bounds one; **none of the nine sites in §4.1 still assumes
8×8**; and a test builds boards of 8×8, 10×10 and 5×7 and exercises a move, a
capture, a promotion and a FEN export on each.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 9 — Quest parent with built-in subclasses

**Goal**: quests follow the same parent-and-subclass pattern as rules.

`Quest` gains `name`, `description`, `reward`, `when`, `parameters()`,
`progress()`, `observe_move()`, `observe_result()`, and `validate() -> bool`
matching the diagram exactly. **No condition class.** Twenty built-ins:

`after_move`: `FirstBlood`, `CaptureN`, `CaptureOfType`, `MovePieceNTimes`,
`ReachedSquare`, `VisitNSquares`, `SurvivePlies`, `SurviveWithoutCapture`,
`CastleN`, `PromoteN`, `EnPassantN`, `MakeCheckN`, `NeverInCheck`,
`KingOnlyGame`.
`at_game_end`: `GameResult`, `WonBy`, `GameAtLeast`, `MaterialAhead`, `Pacifist`,
`CompositeQuest`.

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

**Needs**: 10. **Blocks**: 17.

**Goal**: a capture chain is one move the player makes, not several.

`Move` grows a sequence of hops alongside `start_pos` and `end_pos`.

**Acceptance criteria**, using a **synthetic fixture in the test rather than a
checkers position** — PR 17 has not run when this lands: a three-hop chain built
from a constructed board is offered as a single move, executes atomically, and
rolls back completely if any hop is invalid. A single-hop move goes through the
same path as the degenerate case.

**Needs**: 10. **Blocks**: 17.

### Wave B — two PRs in parallel

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 11 — Orthodox chess rules, and removal of type coupling

**Needs**: 10. **Blocks**: 13, 14, 18.

**Goal**: every rule in `notes/chess_rules.md` implemented, and the engine stops
knowing what a king is.

All eleven chess rules as `Rule` subclasses in `games/chess/rules/`: castling, en
passant, promotion, check and checkmate, stalemate, insufficient material,
fifty-move, threefold repetition, mutual-agreement draw, flag fall, and a rule
declaring which piece kind is royal.

**Also removes**, from the validator: `find_king`, `is_check`, `is_checkmate`,
and every `getType() == "king"` / `== "pawn"` comparison and every `hasattr`
probe. Those become behaviour of the chess configuration.

Rank-relative rules generalise: the home rank, the knight-forward file and the
castling rook files are derived from the configured board rather than assumed to
be 1, 8 and `a`–`h`.

**Acceptance criteria**: each rule passes a game with it enabled and a game with it disabled,
and the difference is the setting rather than a code path; the twelve
`getType()`/`hasattr` sites are gone; a custom piece whose kind is not `"king"`
neither crashes nor silently disables check.

**Needs**: 10. **Blocks**: 13, 14, 18.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 13 — Migrate chess into `games/chess/`

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

**Needs**: 9, 11. **Blocks**: 15.

`QuestManager`, `UserManager`, `User`, `MetadataWriter`, `ChessNotationWriter`,
`WindowController` are instantiated and driven by the game loop.
`GameManager.players` is linked to users. `Timer.add_time` actually applies
increment. The `hasattr(user, "add_quest")` probe becomes a real call.

**Acceptance criteria**: a complete game runs end to end headless, from `new_game` through a
finished result, with quests firing, clocks ticking, the transcript recording
and a user credited.

**Needs**: 9, 11. **Blocks**: 15.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 15 — View layer with the game-start modal

**Needs**: 14. **Blocks**: 16, 20.

`GameView`, `PlayerView`, `PlayerGameView` in `view/`, in tkinter. Board with
coordinates and symbols, highlights, player panels with clocks and captured and
lost pieces, turn indicator, move history, status footer, quest cards with
progress and reward. Starting a game shows a modal with a **configuration
selector**, a **Settings** button and **Start**.

**Headless testing**: `tkinter` needs a display. Tests stay within
`tkinter.Tcl()` and `ttk.Style()`, which work without one, or run under
`xvfb-run`. CI installs `python3-tk` in this PR, the first to import tkinter.

**Acceptance criteria**: the modal appears and its three controls work; a game is played to a
result through the GUI; every widget is reachable by keyboard.

**Needs**: 14. **Blocks**: 16, 20.

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 18 — Export generalised

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

**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
#### PR 21 — Behavioural test coverage

**Needs**: 17, 19, 20.

Close everything §4 lists as missing.

**Acceptance criteria**: every public method under `model/`, `controller/`, `view/` and
`games/` is reachable from at least one test; no surviving test asserts only on
repository metadata; the invariant tests hold — no third-party runtime import
anywhere under the project source, no hard-coded `8` outside `Board`'s default,
all aliases importable, the default configuration cannot be edited or deleted,
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
6. No board dimension is hard-coded outside `Board`'s default. The invariant is asserted against the nine sites in §4.1, not by grepping every `8` in the tree — docstrings legitimately say "8-direction" and file paths contain `utf-8`.

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
20. `checkers` is full English draughts and requires **no engine change**.

**Interface**

21. Starting a game shows the modal with configuration selector, Settings and
    Start.
22. Every data-based configuration is form-exposed from one renderer.
23. The editor refuses invalid code before it joins a configuration.
24. A game is played end to end from the entry point to a result.
24a. `games/` ships with the installed package, so a clean install finds its own
    default configuration.

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
32. No dead code from §4.3 remains; the §4.4 docstring gaps are closed.
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
| Removing DarkFactory leaves the repository without working required checks | High | PR 3 lands the replacement and gets it green before removing anything |
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
| 27 | The log directory is configurable, defaulting to `logs/`, git-ignored | `GameLogger()` currently writes nothing at all, so this closes a gap rather than preserving a convention |
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
| Reinstalling the shared DarkFactory pipeline | Deliberately deferred; its pin is stale and the dependency is removed in PR 3 |
**Verification**: `pytest -q`, `black --check .`, and
`python -m properdocs build --strict`, plus the specific commands in the
corresponding issue.
