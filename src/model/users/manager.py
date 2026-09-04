"""User registry managing profile persistence, player associations, and activity logs."""

from typing import Dict, Optional, Any

try:
    from model.users.user import User
except ImportError:
    from .user import User


class UserManager:
    """Manages registered user accounts, player linkages, and audit logging."""

    def __init__(self):
        """Initialize an empty UserManager."""
        self.users: Dict[int, User] = {}
        self._next_id: int = 1
        self.user_log: str = ""
        self.user_history: str = ""
        self.player_map: Dict[int, Any] = {}

    def register_user(self, user: User, user_id: Optional[int] = None) -> int:
        """Register a user in the repository.

        Args:
            user: User instance to register.
            user_id: Optional explicit user ID (auto-incremented if omitted).

        Returns:
            Assigned user ID integer.
        """
        uid = user_id if user_id is not None else self._next_id
        if user_id is None:
            self._next_id += 1
        self.users[uid] = user
        self.log_action(f"User registered: {user.username} (id: {uid})")
        return uid

    def get_user(self, user_id: int) -> Optional[User]:
        """Fetch a registered user by ID.

        Args:
            user_id: User identifier.

        Returns:
            User instance if found, None otherwise.
        """
        return self.users.get(user_id)

    find_user = get_user

    def link_player(self, user_id: int, player: Any) -> None:
        """Associate a User ID with a live Player game participant.

        Args:
            user_id: Registered user ID.
            player: Player instance to link.
        """
        self.player_map[user_id] = player

    def log_action(self, message: str) -> None:
        """Append an audit log entry.

        Args:
            message: Text message describing the action.
        """
        self.user_log += message + "\n"

    def record_history(self, entry: str) -> None:
        """Append an entry to the user history string.

        Args:
            entry: History record string.
        """
        self.user_history += entry + "\n"

    def execute_move(self, move: Optional[Any] = None, board: Optional[Any] = None) -> bool:
        """Execute a move in the context of user management and record history.

        Args:
            move: Optional Move instance to execute.
            board: Optional Board instance.

        Returns:
            True if executed or move is None, False if execution failed.
        """
        if move is not None and board is not None:
            success = move.execute(board) if hasattr(move, "execute") else False
            if success:
                self.record_history(f"Executed move: {move}")
            return success
        return True
