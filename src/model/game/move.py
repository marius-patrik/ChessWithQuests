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
        capture_from: Optional[Tuple[int, int]] = None,
        companion_start: Optional[Tuple[int, int]] = None,
        companion_end: Optional[Tuple[int, int]] = None,
    ):
        """Initialize a Move instance.

        Args:
            start_pos: Starting (row, col) coordinates.
            end_pos: Destination (row, col) coordinates.
            piece: Moving piece instance, or None to infer from board.
            move_type: Type of move (e.g. "normal", "castling", "en_passant").
            captured_piece: Captured piece instance if any.
            promotion_piece: New piece instance if move involves promotion.
            capture_from: Square a captured piece stands on when it is not the destination.
                An en passant capture takes the piece that stepped past.
            companion_start: Square a second piece starts from, for a move that carries one
                along. Castling moves a rook with its king.
            companion_end: Square that second piece ends on.
        """
        self.start_pos = tuple(start_pos)
        self.end_pos = tuple(end_pos)
        self.piece = piece
        self.move_type = move_type
        self.captured_piece = captured_piece
        self.promotion_piece = promotion_piece
        self.capture_from = tuple(capture_from) if capture_from else None
        self.companion_start = tuple(companion_start) if companion_start else None
        self.companion_end = tuple(companion_end) if companion_end else None

    @staticmethod
    def _bounds(board: Optional[Any]) -> Tuple[int, int]:
        """Return the (rows, cols) a move is measured against.

        Args:
            board: The board the move is played on, or None to use `Board`'s default size.

        Returns:
            Tuple[int, int]: The board dimensions the move must fit inside.
        """
        if board is not None:
            return board.rows, board.cols
        from model.game.board import Board

        return Board.DEFAULT_DIMENSIONS

    def validate(self, board: Optional[Any] = None) -> bool:
        """Validate geometric boundaries and basic board rules for this move.

        Args:
            board: Optional Board instance to verify piece existence and target color. Its
                dimensions decide what is in bounds, so a move may be validated on a board
                of any size.

        Returns:
            True if basic validity checks pass, False otherwise.
        """
        rows, cols = self._bounds(board)
        if not (0 <= self.start_pos[0] < rows and 0 <= self.start_pos[1] < cols):
            return False
        if not (0 <= self.end_pos[0] < rows and 0 <= self.end_pos[1] < cols):
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

        if self.capture_from is not None:
            self.captured_piece = board.get_piece_at(self.capture_from)
            board.set_piece_at(self.capture_from, None)
        else:
            self.captured_piece = board.get_piece_at(self.end_pos)

        success = board.move_piece(self.start_pos, self.end_pos)
        if not success:
            return False

        if self.companion_start is not None and self.companion_end is not None:
            companion = board.get_piece_at(self.companion_start)
            board.set_piece_at(self.companion_start, None)
            if companion is not None:
                board.set_piece_at(self.companion_end, companion)

        if self.promotion_piece is not None:
            board.replace_piece(self.end_pos, self.promotion_piece)
        return True
