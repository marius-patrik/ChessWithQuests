# GameController (`controller/controller.py`)

## Diagram Reference
Controller component corresponding to the core game controller in the MVC architecture.

## Classes
### `GameController` (Alias: `Controller`)
Central coordinator for user interactions on the chessboard.

#### Attributes
- `game_manager: GameManager`: Reference to the active game engine instance.
- `selected_square: Optional[Tuple[int, int]]`: Currently selected board coordinate `(row, col)`.
- `highlighted_moves: List[Tuple[int, int]]`: Calculated valid target squares for the selected piece.

#### Methods
- `select_square(pos: Tuple[int, int]) -> List[Tuple[int, int]]`: Selects a friendly piece and computes valid moves.
- `handle_square_click(pos: Tuple[int, int]) -> Dict[str, Any]`: Manages 2-click move interaction (select -> move / reselect).
- `reset_selection() -> None`: Clears active selection and move highlights.
- `new_game() -> None`: Resets the board and begins a new match.
