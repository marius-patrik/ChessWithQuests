# UserManager (`model/users/manager.py`)

## Diagram Reference
Maps directly to **`User Manager`** in the reference diagram.

## Classes
### `UserManager`
Stores user registrations, profiles, match histories, and player linkages.

#### Attributes
- `users: Dict[int, User]`: Map of user IDs to `User` objects.
- `log_uzivatelu: str`: User activity log string.
- `historie_uzivatele: str`: User game match history string.
- `player_map: Dict[int, Player]` (`Id_uzivatele: hrac`): Links users to players.

#### Methods
- `register_user(user: User, user_id: Optional[int] = None) -> int`: Registers user and generates/assigns ID.
- `najdi_uzivatele(user_id: int) -> Optional[User]` (`get_user`): Looks up user by ID.
- `link_player(user_id: int, player: Any) -> None`: Links player entity.
- `log_action(message: str) -> None`: Appends to user log.
- `record_history(entry: str) -> None`: Appends to user match history.
- `proved_tah(move: Optional[Move] = None, board: Optional[Board] = None) -> bool`: Records and dispatches move.
