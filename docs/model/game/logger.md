# GameLogger (`model/game/logger.py`)

## Diagram Reference
Canonical English implementation of **`GameLogger`** from the architecture diagram.

## Classes
### `GameLogger`
Records chronological moves in-memory and optionally appends to a disk file.

#### Attributes
- `filename: Optional[str]`: Path to output log file.
- `moves: List[Move]`: In-memory list of executed moves.

#### Methods
- `create_file(filename: str) -> None`: Creates/initializes log file with header.
- `log_move(move: Move) -> None`: Logs move coordinate and type.
- `get_moves() -> List[Move]`: Returns history of logged moves.
