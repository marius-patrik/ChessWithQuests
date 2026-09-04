from typing import Tuple, Optional, Any


class Move:
    def __init__(
        self,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
        piece: Optional[Any] = None,
        move_type: str = "normal",
        captured_piece: Optional[Any] = None,
        promotion_piece: Optional[Any] = None,
    ):
        self.start_pos = tuple(start_pos)
        self.end_pos = tuple(end_pos)
        self.piece = piece
        self.move_type = move_type
        self.captured_piece = captured_piece
        self.promotion_piece = promotion_piece

    def validate(self, board: Optional[Any] = None) -> bool:
        if not (0 <= self.start_pos[0] < 8 and 0 <= self.start_pos[1] < 8):
            return False
        if not (0 <= self.end_pos[0] < 8 and 0 <= self.end_pos[1] < 8):
            return False
        if self.start_pos == self.end_pos:
            return False
        if board is not None:
            moving = board.get_piece_at(self.start_pos)
            if moving is None:
                return False
            target = board.get_piece_at(self.end_pos)
            if target is not None and target.getColor() == moving.getColor():
                return False
        return True

    def execute(self, board: Any) -> bool:
        if self.piece is None:
            self.piece = board.get_piece_at(self.start_pos)
        if self.piece is None:
            return False

        self.captured_piece = board.get_piece_at(self.end_pos)
        success = board.move_piece(self.start_pos, self.end_pos)
        if success and self.promotion_piece is not None:
            board.replace_piece(self.end_pos, self.promotion_piece)
        return success

    # Czech aliases
    over_platnost = validate
    proved_tah = execute
    vychozi_pozice = property(lambda self: self.start_pos)
    cilova_pozice = property(lambda self: self.end_pos)
    figurka = property(lambda self: self.piece)
    typ_tahu = property(lambda self: self.move_type)


Tah = Move
