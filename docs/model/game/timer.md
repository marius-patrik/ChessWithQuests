# Timer (`model/game/timer.py`)

## Diagram Reference
Maps directly to **`Timer`** in the reference architecture diagram.

## Classes
### `Timer`
Tracks remaining clock time for both players in seconds.

#### Attributes
- `initial_time: int`: Starting clock allocation (default: `600` seconds).
- `cas_hrac: List[int]` (`+ cas_hrac: List(int)`): `[white_seconds, black_seconds]`.

#### Methods
- `nuluj_cas() -> None` (`reset_time`): Resets times to initial values.
- `pocitej_cas(hrac: int, elapsed_seconds: int = 1) -> None` (`tick`): Deducts time from specified player.
- `add_time(hrac: int, increment_seconds: int) -> None`: Adds increment bonus.
- `get_time(hrac: int) -> int`: Returns current remaining seconds for player.
- `is_expired(hrac: int) -> bool`: Returns `True` if time is zero.
