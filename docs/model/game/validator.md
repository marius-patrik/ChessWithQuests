# MoveValidator (`model/game/validator.py`)

## Diagram Reference
Canonical English implementation of **`RevizorTahu`** from the architecture diagram.

## Architecture Decision (Hybrid Validation)
- Computes valid moves **on-demand** (`get_valid_moves`) when user selects a piece.
- Aggregates valid moves **eagerly** (`get_all_valid_moves`) only when evaluating Checkmate or Stalemate.

## Classes
### `MoveValidator`
Chess rule verification and legal move generation engine.

#### Attributes
- `board: Optional[Board]`: Reference board.
- `move: Optional[Move]`: Reference move.

#### Methods
- `find_king(color: int, board: Optional[Board] = None) -> Optional[Tuple[int, int]]`: Locates king position.
- `is_square_attacked(target_square: Tuple[int, int], by_color: int, board: Optional[Board] = None) -> bool`: Tests square vulnerability.
- `is_check(color: int, board: Optional[Board] = None) -> bool`: Tests if king is attacked.
- `get_valid_moves(start_pos: Tuple[int, int], board: Optional[Board] = None) -> List[Tuple[int, int]]`: Computes strictly legal destinations.
- `get_all_valid_moves(color: int, board: Optional[Board] = None) -> List[Move]`: Aggregates all legal moves for a player.
- `is_valid_move(move: Move, board: Optional[Board] = None) -> bool`: Validates a specific move.
- `is_checkmate(color: int, board: Optional[Board] = None) -> bool`: Tests checkmate condition.
- `is_stalemate(color: int, board: Optional[Board] = None) -> bool`: Tests stalemate condition.
- `simulate_move(move: Optional[Move] = None) -> List[...]`: Simulates execution and returns undo state.
