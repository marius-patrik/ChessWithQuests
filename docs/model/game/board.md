# Board (`model/game/board.py`)

## Diagram Reference
Maps directly to **`HerníPlocha`** in the reference architecture diagram.

## Classes
### `Board`
Represents the physical 8x8 chessboard and captures container.

#### Attributes
- `dimensions: Tuple[int, int]`: Board grid dimensions (default `(8, 8)`).
- `board: List[List[Optional[Piece]]]`: 2D matrix of squares containing pieces or `None`.
- `captured_white: List[Piece]`: Captured white pieces.
- `captured_black: List[Piece]`: Captured black pieces.

#### Methods
- `is_within_bounds(row: int, col: int) -> bool`: Checks if coordinates are valid on the grid.
- `get_piece_at(position: Tuple[int, int]) -> Optional[Piece]`: Retrieves piece at square.
- `set_piece_at(position: Tuple[int, int], piece: Optional[Piece]) -> None`: Places or clears square.
- `move_piece(start_pos: Tuple[int, int], end_pos: Tuple[int, int]) -> bool`: Executes movement and records captures.
- `replace_piece(position: Tuple[int, int], new_piece: Piece) -> None`: Swaps piece (e.g. pawn promotion).
- `setup_default_board() -> None`: Populates standard initial chess layout.
