# GameManager (`model/game/manager.py`)

## Diagram Reference
Maps directly to **`GameManager`** in the reference architecture diagram.

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
- `plocha: Board`: Active chessboard instance (`plocha: HerníPlocha`).
- `aktivni_hrac: int`: Color of player whose turn it is (`1` for White, `-1` for Black).
- `hraci: List[Player]`: Registered players (`hraci: List(Hrac)`).
- `aktualni_tah: Optional[Move]`: Move currently in progress (`aktualni_tah: Tah`).
- `casovac: Timer`: Game clock (`casovac: Timer`).
- `game_logger: GameLogger`: Game log sink (`game_logger: GameLogger`).
- `revizor_tahu: MoveValidator`: Move and rule validator (`+ revizor_tahu: RevizorTahu`).

#### Methods
- `zacni_tah() -> Optional[Move]` (`start_turn`): Prepares turn.
- `mozne_tahy() -> List[Move]` (`possible_moves`): Generates all legal moves for current player.
- `zrus_tah() -> None` (`cancel_move`): Clears pending move.
- `uloz_log() -> None` (`save_log`): Persists game logs.
- `get_stav() -> int` (`get_state`): Computes current state (in progress, check, checkmate, stalemate, timeout).
- `make_move(move: Move) -> bool`: Validates, executes, logs move, and switches turn.
