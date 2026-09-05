"""Move representation tracking positions, piece transitions, captures, and promotions."""

from typing import Tuple, Optional, Any


class Move:
    """Encapsulates a chess move with coordinates, piece states, and execution logic."""

    def __init__(
        self,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
        piece: Optional[Any] = None,
        move_type: str = "normal",
        captured_piece: Optional[Any] = None,
        promotion_piece: Optional[Any] = None,
    ):
        """Initialize a Move instance.

        Args:
            start_pos: Starting (row, col) coordinates.
            end_pos: Destination (row, col) coordinates.
            piece: Moving piece instance, or None to infer from board.
            move_type: Type of move (e.g. "normal", "castling", "en_passant").
            captured_piece: Captured piece instance if any.
            promotion_piece: New piece instance if move involves pawn promotion.
        """
        self.start_pos = tuple(start_pos)
        self.end_pos = tuple(end_pos)
        self.piece = piece
        self.move_type = move_type
        self.captured_piece = captured_piece
        self.promotion_piece = promotion_piece

    def validate(self, board: Optional[Any] = None) -> bool:
        """Validate geometric boundaries and basic board rules for this move.

        Args:
            board: Optional Board instance to verify piece existence and target color.

        Returns:
            True if basic validity checks pass, False otherwise.
        """
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
        """Execute this move on the given board.

        Args:
            board: Board instance on which the move is applied.

        Returns:
            True if the move executed successfully, False otherwise.
        """
        if self.piece is None:
            self.piece = board.get_piece_at(self.start_pos)
        if self.piece is None:
            return False

        self.captured_piece = board.get_piece_at(self.end_pos)
        success = board.move_piece(self.start_pos, self.end_pos)
        if success and self.promotion_piece is not None:
            board.replace_piece(self.end_pos, self.promotion_piece)
        return success
