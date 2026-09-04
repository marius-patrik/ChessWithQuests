# GameManager (`model/game/manager.py`)

## Diagram Reference
Canonical English implementation of **`GameManager`** (`Hra`) from the architecture diagram.

## Classes
### `GameManager`
Central game engine orchestrator binding Board, Players, Validator, Timer, and Logger together.

#### Constants
- `STATE_IN_PROGRESS = 0`
- `STATE_CHECK = 1`
- `STATE_CHECKMATE = 2`
- `STATE_STALEMATE = 3`
- `STATE_TIMEOUT = 4`

#### Attributes
- `board: Board`: Active chessboard instance.
- `active_player: int`: Color of player whose turn it is (`1` for White, `-1` for Black).
- `players: List[Player]`: Registered players.
- `current_move: Optional[Move]`: Move currently in progress.
- `timer: Timer`: Game clock.
- `game_logger: GameLogger`: Game log sink.
- `move_validator: MoveValidator`: Move and rule validator.

#### Methods
- `start_turn() -> Optional[Move]`: Prepares turn.
- `get_valid_moves() -> List[Move]` (`possible_moves`): Generates all legal moves for current player.
- `cancel_move() -> None`: Clears pending move.
- `save_log() -> None`: Persists game logs.
- `get_state() -> int`: Computes current state (in progress, check, checkmate, stalemate, timeout).
- `make_move(move: Move) -> bool`: Validates, executes, logs move, and switches turn.
