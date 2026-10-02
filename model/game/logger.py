"""Game logging system recording played moves to in-memory history and log files."""

import os
from typing import Optional, List, Any


class GameLogger:
    """Logs chess moves to memory and optionally writes them to a persistent file."""

    def __init__(self, filename: Optional[str] = None):
        """Initialize a GameLogger instance.

        Args:
            filename: Optional filesystem path for appending move logs.
        """
        self.filename: Optional[str] = filename
        self.moves: List[Any] = []
        if filename:
            self.create_file(filename)

    def create_file(self, filename: str) -> None:
        """Create or overwrite a log file with an initial header.

        Args:
            filename: Target file path.
        """
        self.filename = filename
        dirname = os.path.dirname(filename)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write("# Chess Game Log\n")

    def log_move(self, move: Any) -> None:
        """Record a played move in memory and append to file if configured.

        Args:
            move: Move object or string representation.
        """
        self.moves.append(move)
        if self.filename:
            move_str = str(move)
            if hasattr(move, "start_pos") and hasattr(move, "end_pos"):
                move_str = (
                    f"{move.start_pos} -> {move.end_pos} ({getattr(move, 'move_type', 'normal')})"
                )
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(f"{move_str}\n")

    def get_moves(self) -> List[Any]:
        """Get copy of all recorded moves.

        Returns:
            List of recorded Move instances or strings.
        """
        return list(self.moves)

    @property
    def file_path(self) -> Optional[str]:
        """Path to the underlying log file, if any."""
        return self.filename
