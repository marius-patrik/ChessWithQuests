# ChessWithQuests Documentation Index

Comprehensive index of all architecture, module, and component documentation in the `docs/` directory. Each document corresponds to a source file in `src/`.

---

## Table of Contents
- [Controllers (`docs/controller/`)](#controllers)
- [Model - Game Domain (`docs/model/game/`)](#model---game-domain)
- [Model - Pieces (`docs/model/pieces/`)](#model---pieces)
- [Model - Users (`docs/model/users/`)](#model---users)
- [Model - Miscellaneous & Notations (`docs/model/misc/`)](#model---miscellaneous--notations)
- [Model Root (`docs/model/`)](#model-root)
- [Views (`docs/view/`)](#views)

---

## Controllers
Documentation for application controllers handling gameplay orchestration and user interface lifecycle.

- [docs/controller/__init__.md](docs/controller/__init__.md): Controller package root initialization and module exports.
- [docs/controller/controller.md](docs/controller/controller.md): `GameController` (`Controller`) orchestrating board state, move execution, turn switching, and game flow.
- [docs/controller/window_controller.md](docs/controller/window_controller.md): `WindowController` managing the GUI window, square clicks, dialog prompts, timer updates, and status displays.

---

## Model - Game Domain
Core game entities, rule enforcement, move representations, timers, and logging.

- [docs/model/game/board.md](docs/model/game/board.md): `Board` (`Sachovnice`) managing the 8x8 grid, piece placement, removals, and boundary checks.
- [docs/model/game/logger.md](docs/model/game/logger.md): `GameLogger` logging moves, alerts, events, and file output.
- [docs/model/game/manager.md](docs/model/game/manager.md): `GameManager` (`Hra`) coordinating turn order, move history, clocks, and game completion.
- [docs/model/game/move.md](docs/model/game/move.md): `Move` (`Tah`) representing coordinate transitions, captures, checks, and pawn promotions.
- [docs/model/game/player.md](docs/model/game/player.md): `Player` (`Hrac`) encapsulating player color, active clock, and optional user profile.
- [docs/model/game/quest.md](docs/model/game/quest.md): `Quest` representing in-game objective conditions, status, and experience rewards.
- [docs/model/game/timer.md](docs/model/game/timer.md): `Timer` handling player countdown clocks, time increments per move, and time expiration.
- [docs/model/game/validator.md](docs/model/game/validator.md): `MoveValidator` (`Revizor`) verifying legal moves, check conditions, checkmate, and stalemate.

---

## Model - Pieces
Individual chess piece implementations defining move vectors, attack patterns, and special movement rules.

- [docs/model/pieces/piece.md](docs/model/pieces/piece.md): `Piece` (`Figurka`) base class with color encapsulation, vector calculations, and leaping flags.
- [docs/model/pieces/pawn.md](docs/model/pieces/pawn.md): `Pawn` (`Pesec`) with single/double forward pushes, diagonal captures, and promotion triggers.
- [docs/model/pieces/rook.md](docs/model/pieces/rook.md): `Rook` (`Vez`) with orthogonal sliding vectors and castling eligibility tracking.
- [docs/model/pieces/tower.md](docs/model/pieces/tower.md): `Tower` diagram alias pointing directly to `Rook`.
- [docs/model/pieces/horse.md](docs/model/pieces/horse.md): `Horse` / `Knight` (`Jezdec`) with L-shaped leaping move vectors.
- [docs/model/pieces/bishop.md](docs/model/pieces/bishop.md): `Bishop` (`Strelec`) with diagonal sliding vectors.
- [docs/model/pieces/queen.md](docs/model/pieces/queen.md): `Queen` (`Dama`) combining orthogonal and diagonal ray movements.
- [docs/model/pieces/king.md](docs/model/pieces/king.md): `King` (`Kral`) with single-step movement in all directions, check avoidance, and castling.

---

## Model - Users
User account management, statistics tracking, quest progression, and player linkage.

- [docs/model/users/user.md](docs/model/users/user.md): `User` account entity storing username, password hashes, ratings, completed quests, and match statistics.
- [docs/model/users/manager.md](docs/model/users/manager.md): `UserManager` managing registered user profiles and binding users to active players.

---

## Model - Miscellaneous & Notations
Game export writers, PGN metadata tagging, algebraic notation converters, and quest management.

- [docs/model/misc/export_writers.md](docs/model/misc/export_writers.md): `ExportWriter` and `ChessNotationWriter` supporting FEN, PGN, and stenographic notation exports.
- [docs/model/misc/metadata.md](docs/model/misc/metadata.md): `MetadataWriter` managing event, site, date, round, and player metadata headers.
- [docs/model/misc/notation.md](docs/model/misc/notation.md): Pure utility functions converting between zero-indexed board coordinates and algebraic notation (e.g., `(4, 1) <-> "e2"`).
- [docs/model/misc/quest_manager.md](docs/model/misc/quest_manager.md): `QuestManager` evaluating active player quests after moves and granting user achievements.

---

## Model Root
- [docs/model/__init__.md](docs/model/__init__.md): Model package initialization.

---

## Views
User interface presentations and graphical views.

- [docs/view/__init__.md](docs/view/__init__.md): View package initialization.
