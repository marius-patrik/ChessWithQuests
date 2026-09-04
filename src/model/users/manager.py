from typing import Dict, Optional, Any

try:
    from model.users.user import User
except ImportError:
    from .user import User


class UserManager:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self._next_id: int = 1
        self.user_log: str = ""
        self.user_history: str = ""
        self.player_map: Dict[int, Any] = {}

    def register_user(self, user: User, user_id: Optional[int] = None) -> int:
        uid = user_id if user_id is not None else self._next_id
        if user_id is None:
            self._next_id += 1
        self.users[uid] = user
        self.log_action(f"User registered: {user.username} (id: {uid})")
        return uid

    def get_user(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)

    find_user = get_user

    def link_player(self, user_id: int, player: Any) -> None:
        self.player_map[user_id] = player

    def log_action(self, message: str) -> None:
        self.user_log += message + "\n"

    def record_history(self, entry: str) -> None:
        self.user_history += entry + "\n"

    def execute_move(self, move: Optional[Any] = None, board: Optional[Any] = None) -> bool:
        if move is not None and board is not None:
            success = move.execute(board) if hasattr(move, "execute") else False
            if success:
                self.record_history(f"Executed move: {move}")
            return success
        return True
