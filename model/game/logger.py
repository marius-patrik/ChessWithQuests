import os
from typing import Optional, List, Any


class GameLogger:
    def __init__(self, filename: Optional[str] = None):
        self.soubor: Optional[str] = filename
        self.moves: List[Any] = []
        if filename:
            self.vytvor_soubor(filename)

    def vytvor_soubor(self, filename: str) -> None:
        self.soubor = filename
        dirname = os.path.dirname(filename)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write("# Chess Game Log\n")

    def uloz_tah(self, tah: Any) -> None:
        self.moves.append(tah)
        if self.soubor:
            move_str = str(tah)
            if hasattr(tah, "start_pos") and hasattr(tah, "end_pos"):
                move_str = f"{tah.start_pos} -> {tah.end_pos} ({getattr(tah, 'move_type', 'normal')})"
            with open(self.soubor, "a", encoding="utf-8") as f:
                f.write(f"{move_str}\n")

    def get_moves(self) -> List[Any]:
        return list(self.moves)

    # English aliases
    log_move = uloz_tah
    create_file = vytvor_soubor
    file_path = property(lambda self: self.soubor)
