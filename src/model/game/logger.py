"""Game logging system recording played moves to in-memory history and log files."""

import os
from typing import Optional, List, Any


class GameLogger:
    """Records the moves of a game in memory and, optionally, in a file."""

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
        # A header for the file, in the same words for every game: the logger is handed a
        # filename and a move and knows nothing else about the game it is recording, so naming
        # one here would be a claim it has no way to keep true. `SCRATCHPAD.md` §8 item 14 is
        # that the engine names no game, and this line was the engine naming one in every log
        # file the product has ever written.
        with open(filename, "w", encoding="utf-8") as f:
            f.write("# Game log\n")

    def log_move(self, move: Any) -> None:
        """Record a played move in memory and append to file if configured.

        Args:
            move: Move object or string representation.
        """
        self.moves.append(move)
        if self.filename:
            move_str = str(move)
            start = getattr(move, "start_pos", None)
            end = getattr(move, "end_pos", None)
            if start is not None and end is not None:
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
        """Path to the underlying log file, if any.

        Returns:
            Optional[str]: The configured log file path, or None when logging is in memory only.
        """
        return self.filename
