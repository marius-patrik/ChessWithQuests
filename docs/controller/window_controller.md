# WindowController (`controller/window_controller.py`)

## Diagram Reference
Manages window lifecycle and coordinates visual view components with `GameController`.

## Classes
### `WindowController`
High-level desktop window manager.

#### Attributes
- `game_controller: GameController`: Underlying game controller instance.
- `title: str`: Window title (default: `"ChessWithQuests"`).
- `width, height: int`: Window dimensions (default: `800x600`).
- `is_running: bool`: Current window running status.
- `status_message: str`: Status bar text displayed to the player.
- `active_dialog: Optional[str]`: Active modal dialog prompt (e.g. draw offer or confirmation).

#### Methods
- `start() -> None`: Launches the window loop and marks running state.
- `stop() -> None`: Terminates window loop.
- `set_status(message: str) -> None`: Updates status bar text.
- `show_dialog(message: str) -> None` / `close_dialog() -> None`: Modal dialog controls.
- `on_square_clicked(pos: Tuple[int, int]) -> Dict[str, Any]`: Delegates board clicks to `GameController` and updates status.
- `tick_timer() -> None`: Updates clock on timer tick events.
