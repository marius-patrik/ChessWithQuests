# Player (`model/game/player.py`)

## Diagram Reference
Maps directly to **`Hrac`** in the reference architecture diagram.

## Classes
### `Player`
Represents a game participant.

#### Attributes
- `color: int`: Player color (`1` for White, `-1` for Black).
- `user: Optional[User]`: Linked user account profile.

#### Methods
- `getColor() -> int`: Returns assigned color code.
- `getUser() -> Optional[User]`: Returns linked user profile.
- `setUser(user: User) -> None`: Sets linked user profile.
- `getEloRating() -> int`: Returns user rating or default `1200`.
