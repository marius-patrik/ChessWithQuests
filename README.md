# ChessWithQuests

School project of a chess engine with quests on top of it.

**Status: mid-build.** What the repository contains today is the chess *engine* — the
board, the pieces, move generation and validation, check, checkmate, stalemate,
clocks, logging, notation and export prototypes, user records and the MVC
controller. There is no graphical interface yet, so nothing is playable by
clicking on it. The product requirements (`PRD.md`) and the implementation manual
(`SCRATCHPAD.md`) describe the finished product and track the remaining work,
issue by issue, in that order.

## What works today

Every item below is exercised by a test in `tests/`.

| Capability | Where it lives | Test |
|---|---|---|
| Board with the standard 8×8 starting position, bounds checking, moving, capture recording and piece replacement | `model/game/board.py` | `tests/test_board.py` |
| Pieces declaring their own movement vectors, attack vectors and jump flag: pawn, rook, knight, bishop, queen, king | `model/pieces/` | `tests/test_piece.py`, `tests/test_pawn.py`, `tests/test_rook.py`, `tests/test_horse.py`, `tests/test_bishop.py`, `tests/test_queen.py`, `tests/test_king.py` |
| Moves carrying a start square, a target square, a move type and an optional promotion piece, validated and executed on the board | `model/game/move.py` | `tests/test_move.py` |
| Legal move generation per piece and for a whole side, rejecting any move that would leave the mover's own king attacked | `model/game/validator.py` | `tests/test_validator.py`, `tests/test_game_manager.py` |
| Check, checkmate and stalemate detection, reported through the game manager's state constants | `model/game/validator.py`, `model/game/manager.py` | `tests/test_validator.py`, `tests/test_game_manager.py` |
| Turn alternation and illegal-move rejection in the game manager | `model/game/manager.py` | `tests/test_game_manager.py` |
| Per-player clocks that count down, take an increment, reset and report expiry, with expiry reaching the game state | `model/game/timer.py` | `tests/test_timer.py`, `tests/test_game_manager.py` |
| Move logging in memory and, when a path is given, appended to a log file | `model/game/logger.py` | `tests/test_logger.py`, `tests/test_game_manager.py` |
| Players, optionally linked to a user, whose Elo rating the player reads through that link | `model/game/player.py`, `model/users/` | `tests/test_player.py`, `tests/test_user.py`, `tests/test_user_manager.py` |
| Algebraic coordinate conversion in both directions | `model/misc/notation.py` | `tests/test_notation_and_writers.py` |
| Export writers: a FEN string built from board placement, coordinate-pair "stenographic" movetext, and a PGN-shaped export carrying a seven-tag header roster | `model/misc/export_writers.py`, `model/misc/metadata.py` | `tests/test_notation_and_writers.py`, `tests/test_metadata.py` |
| Quests with a name, a description, a condition and a reward, and a quest manager that registers quests and credits the completing user — standalone types, not yet wired into a game | `model/game/quest.py`, `model/misc/quest_manager.py` | `tests/test_quest.py`, `tests/test_quest_manager.py` |
| MVC controller: a square click selects a piece, reports its legal destinations, plays the move and switches the turn; a window controller maps those events onto status text and ticks the clock | `controller/controller.py`, `controller/window_controller.py` | `tests/test_controller.py`, `tests/test_window_controller.py` |

### Known limitations of the code above

- The engine assumes 8×8. `Board` accepts other dimensions, but the move and
  validator paths still hard-code eight, and no test covers a board of another
  size.
- The export writers are early. The FEN string carries the placement and the
  side to move; its remaining fields are placeholders. The PGN export writes
  destination squares as movetext rather than algebraic notation, and the header
  roster defaults to `Player 1` and `Player 2`.
- The quest, user and export subsystems are standalone: a game never constructs
  them yet, so no single call path exercises a game and its quests together.
- `view/` is a single docstring. No widget, renderer or entry point exists.

## Not built yet

No claims are made for any of this; it is listed so a reader knows the gap.

- No graphical interface. `view/` is empty and there is no entry point.
- No settings surface and no configuration pattern — no board or piece editor,
  no configurable board dimensions in practice, no variant directories.
- No pluggable rule system and no rule subclasses. Of the orthodox rules, only
  check, checkmate and stalemate are implemented; castling, en passant,
  promotion in the rules, the fifty-move rule, threefold repetition, insufficient
  material and drawn agreements are absent.
- No checkers, and no `games/` directory: the engine is chess-specific today.
- No packaging. The repository is imported from its checkout, not installed.
- No multi-hop moves, so a checkers capture chain cannot be expressed yet.

## Documentation and architecture

- **Generated documentation**: [ChessWithQuests Documentation](https://marius-patrik.github.io/ChessWithQuests/)
  — every page is emitted from the source docstrings at build time; this file is
  its overview page.
- **Reference architecture diagram**:
  [Draw.io diagram](https://app.diagrams.net/#G19OY7iySOQWRAZDFKy1r-7tJKG_L-_Qn8#%7B%22pageId%22%3A%22C5RBs43oDa-KdzZeNtuy%22%7D)
  — the class hierarchy and the Model-View-Controller split the object model
  follows.
- **Product requirements**: `PRD.md`.
- **Notes**: `notes/chess_rules.md`, `notes/object_model.md`,
  `notes/reference_diagram.md`.

## Development

Python 3.10 or newer. The engine itself uses the standard library only; the tools
below are development dependencies and never ship. Clone the repository and
install those tools into a virtual environment:

```
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

The package is not installed — `pyproject.toml` configures `pytest` with
`pythonpath = ["."]`, so run everything from the repository root:

```
python -m pytest -q
python -m black --check .
python -m properdocs build --strict
```