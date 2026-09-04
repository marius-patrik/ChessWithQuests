import os
from typing import Optional, List, Any


class GameLogger:
    def __init__(self, filename: Optional[str] = None):
        self.filename: Optional[str] = filename
        self.moves: List[Any] = []
        if filename:
            self.create_file(filename)

    def create_file(self, filename: str) -> None:
        self.filename = filename
        dirname = os.path.dirname(filename)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write("# Chess Game Log\n")

    def log_move(self, move: Any) -> None:
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
        return list(self.moves)

    @property
    def file_path(self) -> Optional[str]:
        return self.filename
