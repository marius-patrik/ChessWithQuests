from typing import Dict, Optional, Any
try:
    from model.users.user import User
except ImportError:
    from .user import User


class UserManager:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self._next_id: int = 1
        self.log_uzivatelu: str = ""
        self.historie_uzivatele: str = ""
        self.player_map: Dict[int, Any] = {}

    def register_user(self, user: User, user_id: Optional[int] = None) -> int:
        uid = user_id if user_id is not None else self._next_id
        if user_id is None:
            self._next_id += 1
        self.users[uid] = user
        self.log_action(f"User registered: {user.username} (id: {uid})")
        return uid

    def najdi_uzivatele(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)

    def link_player(self, user_id: int, player: Any) -> None:
        self.player_map[user_id] = player

    def log_action(self, message: str) -> None:
        self.log_uzivatelu += message + "\n"

    def record_history(self, entry: str) -> None:
        self.historie_uzivatele += entry + "\n"

    def proved_tah(self, move: Optional[Any] = None, board: Optional[Any] = None) -> bool:
        if move is not None and board is not None:
            success = move.execute(board) if hasattr(move, "execute") else False
            if success:
                self.record_history(f"Executed move: {move}")
            return success
        return True

    # English aliases
    get_user = najdi_uzivatele
    find_user = najdi_uzivatele
    execute_move = proved_tah
    Id_uzivatele = property(lambda self: self.player_map)
