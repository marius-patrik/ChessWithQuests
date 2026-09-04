# Move (`model/game/move.py`)

## Diagram Reference
Maps directly to **`Tah`** in the reference architecture diagram.

## Classes
### `Move`
Represents an action moving a piece from start square to end square.

#### Attributes
- `start_pos: Tuple[int, int]`: Source square `(row, col)`.
- `end_pos: Tuple[int, int]`: Target square `(row, col)`.
- `piece: Optional[Piece]`: Moving piece.
- `move_type: str`: e.g. `"normal"`, `"capture"`, `"castling"`, `"promotion"`, `"en_passant"`.
- `captured_piece: Optional[Piece]`: Piece captured by this move, if any.
- `promotion_piece: Optional[Piece]`: New piece instantiated upon promotion.

#### Methods
- `validate(board: Optional[Board] = None) -> bool`: Validates boundaries and coordinates.
- `execute(board: Board) -> bool`: Applies movement and promotions onto board.
