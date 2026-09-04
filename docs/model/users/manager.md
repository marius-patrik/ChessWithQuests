# UserManager (`model/users/manager.py`)

## Diagram Reference
Maps directly to **`User Manager`** in the reference diagram.

## Classes
### `UserManager`
Stores user registrations, profiles, match histories, and player linkages.

#### Attributes
- `users: Dict[int, User]`: Map of user IDs to `User` objects.
- `user_log: str`: User activity log string.
- `user_history: str`: User game match history string.
- `player_map: Dict[int, Player]`: Links users to players.

#### Methods
- `register_user(user: User, user_id: Optional[int] = None) -> int`: Registers user and generates/assigns ID.
- `get_user(user_id: int) -> Optional[User]`: Looks up user by ID (also aliased as `find_user`).
- `link_player(user_id: int, player: Any) -> None`: Links player entity.
- `log_action(message: str) -> None`: Appends to user log.
- `record_history(entry: str) -> None`: Appends to user match history.
- `execute_move(move: Optional[Move] = None, board: Optional[Board] = None) -> bool`: Records and dispatches move.
