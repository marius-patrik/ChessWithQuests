# Export Writers (`model/misc/export_writers.py`)

## Diagram Reference
Maps directly to **`export writers`** and **`ChessNotationWriter`** in the reference diagram.

## Classes
### `ExportWriter`
Abstract base class for match notation serialisation.

### `ChessNotationWriter`
Serialises chess match moves and board positions into standard formats:
- **PGN (Portable Game Notation)**: `to_pgn(moves, metadata)`
- **FEN (Forsyth-Edwards Notation)**: `to_fen(board, active_color)`
- **Stenographic Notation**: `to_stenographic(moves)`
- `export(format_type: str, **kwargs) -> str`: Generic format dispatcher.
