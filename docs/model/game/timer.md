# Timer (`model/game/timer.py`)

## Diagram Reference
Maps directly to **`Timer`** in the reference architecture diagram.

## Classes
### `Timer`
Tracks remaining clock time for both players in seconds.

#### Attributes
- `initial_time: int`: Starting clock allocation (default: `600` seconds).
- `player_times: List[int]`: `[white_seconds, black_seconds]`.
- `increment: int`: Clock increment in seconds (default: `0`).

#### Methods
- `reset_time() -> None`: Resets times to initial values.
- `tick(player: int, elapsed_seconds: int = 1) -> None`: Deducts time from specified player (`1` for White, `-1` for Black).
- `add_time(player: int, increment_seconds: int) -> None`: Adds increment bonus.
- `get_time(player: int) -> int`: Returns current remaining seconds for player.
- `is_expired(player: int) -> bool`: Returns `True` if time is zero.
