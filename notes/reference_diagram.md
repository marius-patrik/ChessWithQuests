# Reference Architecture Diagram

## Link to Live Diagram
[Draw.io Architecture Diagram](https://app.diagrams.net/#G19OY7iySOQWRAZDFKy1r-7tJKG_L-_Qn8#%7B%22pageId%22%3A%22C5RBs43oDa-KdzZeNtuy%22%7D)

- **File**: `Šachy - diagram tříd.drawio`
- **Pages**:
  - `Page-1`: Full object model encompassing User Management, Quests, Game Management, Board, Pieces, and Exporters.
  - `MVC - GameView`: Focus on the Model-View-Controller integration and GameView bindings.

---

## Diagram Structure & Component Inventory

### 1. Pieces Layer (`model.pieces`)
- **`Figurka` (`Piece`)**: Base class with `name`, `color` (`1` / `-1`), `vectors`, `attack_vectors`, and `can_jump`.
- **`Pěšák` (`Pawn`)**: Forward step `(1 * color, 0)`, initial 2-step advance, diagonal attack `(1 * color, ±1)`.
- **`Věž` (`Rook`)** & **`Tower`**: Orthogonal ray-marching sliding piece.
- **`Kůň` (`Horse` / `Knight`)**: L-shaped jumping piece (`can_jump = True`).
- **`Střelec` (`Bishop`)**: Diagonal ray-marching sliding piece.
- **`Dáma` (`Queen`)**: 8-direction ray-marching sliding piece.
- **`Král` (`King`)**: 8-direction 1-step piece with check/checkmate tracking.

### 2. Game Core Layer (`model.game`)
- **`HerníPlocha` (`Board`)**: 8×8 board grid, piece indexing, capture pools (`vyhozene_figurky_b`, `vyhozene_figurky_c`).
- **`Tah` (`Move`)**: Move execution, coordinate tracking, promotion handling, and basic geometry validation.
- **`Hrac` (`Player`)**: Player color code and linked user account with ELO rating lookup.
- **`Timer`**: Dual clock countdown and time increment management.
- **`GameLogger`**: In-memory and file-based move transcript logging.
- **`RevizorTahu` (`MoveValidator`)**: Ray-marching attack detection, check, checkmate, and stalemate validation.
- **`GameManager`**: Central engine tying board, players, timer, validator, and state machine together.
- **`Quest`**: In-game achievement tracking with conditional predicates.

### 3. Users Layer (`model.users`)
- **`Uzivatel` (`User`)**: User profile with username, display name, email, ELO rating, and completed quests.
- **`User Manager` (`UserManager`)**: User directory, profile registration, match logging, and player linkage.

### 4. Serialization & Notation Layer (`model.misc`)
- **`MetadataWriter`**: PGN header tags roster.
- **`ChessNotationWriter`**: PGN, FEN, and Stenographic notation generation.
- **`QuestManager`**: Registry for tracking and awarding in-game quests.

### 5. Controllers (`controller`)
- **`GameController`**: Handles user board clicks, piece selections, and move executions.
- **`WindowController`**: Manages window loop, dialog prompts, timer ticks, and UI events.
