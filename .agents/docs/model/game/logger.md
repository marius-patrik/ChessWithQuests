# GameLogger (`model/game/logger.py`)

## Diagram Reference
Maps directly to **`GameLogger`** in the reference architecture diagram.

## Classes
### `GameLogger`
Records chronological moves in-memory and optionally appends to a disk file.

#### Attributes
- `soubor: Optional[str]`: Path to output log file (`soubor: File`).
- `moves: List[Move]`: In-memory list of executed moves.

#### Methods
- `vytvor_soubor(filename: str) -> None` (`create_file`): Creates/initializes log file with header.
- `uloz_tah(tah: Move) -> None` (`log_move`): Logs move coordinate and type.
- `get_moves() -> List[Move]`: Returns history of logged moves.
