"""Move validation engine enforcing chess rules, checks, pins, and terminal conditions."""

from typing import List, Tuple, Optional, Any

try:
    from model.game.board import Board
    from model.game.move import Move
    from model.pieces.piece import Piece
    from model.pieces.pawn import Pawn
    from model.pieces.king import King
except ImportError:
    from .board import Board
    from .move import Move
    from ..pieces.piece import Piece
    from ..pieces.pawn import Pawn
    from ..pieces.king import King


class MoveValidator:
    """Validates piece movement legality, checks, checkmates, and stalemates."""

    def __init__(self, board: Optional[Board] = None, move: Optional[Move] = None):
        """Initialize a MoveValidator instance.

        Args:
            board: Optional Board instance to validate moves on.
            move: Optional Move instance being inspected.
        """
        self.board = board
        self.move = move

    def set_board(self, board: Board) -> None:
        """Assign the active chessboard.

        Args:
            board: Board instance.
        """
        self.board = board

    def set_move(self, move: Move) -> None:
        """Assign the active move to evaluate.

        Args:
            move: Move instance.
        """
        self.move = move

    def find_king(self, color: int, board: Optional[Board] = None) -> Optional[Tuple[int, int]]:
        """Find the coordinates of a specified player's king.

        Args:
            color: King's color (1 for White, -1 for Black).
            board: Optional Board instance (defaults to self.board).

        Returns:
            Tuple of (row, col) coordinates or None if king is missing.
        """
        b = board or self.board
        if b is None:
            return None
        for r in range(b.rows):
            for c in range(b.cols):
                p = b.get_piece_at((r, c))
                if p is not None and p.getColor() == color and p.getType() == "king":
                    return (r, c)
        return None

    def is_square_attacked(
        self, target_square: Tuple[int, int], by_color: int, board: Optional[Board] = None
    ) -> bool:
        """Determine whether a given square is under attack by pieces of a given color.

        Args:
            target_square: (row, col) target coordinates.
            by_color: Color of the attacking side (1 for White, -1 for Black).
            board: Optional Board instance (defaults to self.board).

        Returns:
            True if target_square is attacked by by_color pieces, False otherwise.
        """
        b = board or self.board
        if b is None:
            return False

        tr, tc = target_square
        for r in range(b.rows):
            for c in range(b.cols):
                piece = b.get_piece_at((r, c))
                if piece is None or piece.getColor() != by_color:
                    continue

                if isinstance(piece, Pawn) or piece.getType() == "pawn":
                    for dr, dc in piece.getAttackDirections():
                        if (r + dr, c + dc) == (tr, tc):
                            return True
                    continue

                directions = piece.getAttackDirections()
                can_jump = piece.canJump()
                max_steps = (
                    1 if (can_jump or piece.getType() == "king" or isinstance(piece, King)) else 8
                )

                for dr, dc in directions:
                    step = 1
                    while step <= max_steps:
                        nr, nc = r + dr * step, c + dc * step
                        if not b.is_within_bounds(nr, nc):
                            break
                        if (nr, nc) == (tr, tc):
                            return True
                        if not can_jump and b.get_piece_at((nr, nc)) is not None:
                            break
                        step += 1
        return False

    def is_check(self, color: int, board: Optional[Board] = None) -> bool:
        """Check if the king of the given color is currently under attack.

        Args:
            color: Player color to check (1 for White, -1 for Black).
            board: Optional Board instance (defaults to self.board).

        Returns:
            True if the king is attacked, False otherwise.
        """
        b = board or self.board
        if b is None:
            return False
        king_pos = self.find_king(color, b)
        if king_pos is None:
            return False
        opponent_color = -1 if color == 1 else 1
        return self.is_square_attacked(king_pos, opponent_color, b)

    def get_pseudo_legal_moves(
        self, start_pos: Tuple[int, int], board: Optional[Board] = None
    ) -> List[Tuple[int, int]]:
        """Compute candidate move destinations ignoring check constraints.

        Args:
            start_pos: (row, col) origin coordinates.
            board: Optional Board instance (defaults to self.board).

        Returns:
            List of valid geometric destination squares.
        """
        b = board or self.board
        if b is None:
            return []

        piece = b.get_piece_at(start_pos)
        if piece is None:
            return []

        r, c = start_pos
        moves: List[Tuple[int, int]] = []

        if isinstance(piece, Pawn) or piece.getType() == "pawn":
            # Pawn single forward step
            for dr, dc in piece.getDirections():
                nr, nc = r + dr, c + dc
                if b.is_within_bounds(nr, nc) and b.get_piece_at((nr, nc)) is None:
                    moves.append((nr, nc))
                    # Initial 2-step advance
                    if hasattr(piece, "hasMoved") and not piece.hasMoved():
                        if hasattr(piece, "getInitialVectors"):
                            for idr, idc in piece.getInitialVectors():
                                inr, inc = r + idr, c + idc
                                if (
                                    b.is_within_bounds(inr, inc)
                                    and b.get_piece_at((inr, inc)) is None
                                ):
                                    moves.append((inr, inc))

            # Pawn diagonal attacks
            for dr, dc in piece.getAttackDirections():
                nr, nc = r + dr, c + dc
                if b.is_within_bounds(nr, nc):
                    target = b.get_piece_at((nr, nc))
                    if target is not None and target.getColor() != piece.getColor():
                        moves.append((nr, nc))
            return moves

        directions = piece.getDirections() or []
        can_jump = piece.canJump()
        max_steps = 1 if (can_jump or piece.getType() == "king" or isinstance(piece, King)) else 8

        for dr, dc in directions:
            step = 1
            while step <= max_steps:
                nr, nc = r + dr * step, c + dc * step
                if not b.is_within_bounds(nr, nc):
                    break
                target = b.get_piece_at((nr, nc))
                if target is None:
                    moves.append((nr, nc))
                else:
                    if target.getColor() != piece.getColor():
                        moves.append((nr, nc))
                    break
                step += 1
        return moves

    def get_valid_moves(
        self, start_pos: Tuple[int, int], board: Optional[Board] = None
    ) -> List[Tuple[int, int]]:
        """Get strictly legal move destinations ensuring the friendly king is safe from check.

        Args:
            start_pos: (row, col) origin coordinates.
            board: Optional Board instance (defaults to self.board).

        Returns:
            List of strictly legal destination squares.
        """
        b = board or self.board
        if b is None:
            return []

        piece = b.get_piece_at(start_pos)
        if piece is None:
            return []

        color = piece.getColor()
        pseudo_moves = self.get_pseudo_legal_moves(start_pos, b)
        legal_moves: List[Tuple[int, int]] = []

        for target_pos in pseudo_moves:
            # Simulate move to ensure it does not leave/place king in check
            original_target = b.get_piece_at(target_pos)
            b.set_piece_at(target_pos, piece)
            b.set_piece_at(start_pos, None)

            in_check = self.is_check(color, b)

            # Rollback
            b.set_piece_at(start_pos, piece)
            b.set_piece_at(target_pos, original_target)

            if not in_check:
                legal_moves.append(target_pos)

        return legal_moves

    def get_all_valid_moves(self, color: int, board: Optional[Board] = None) -> List[Move]:
        """Compute all strictly legal moves for all pieces belonging to a color.

        Args:
            color: Player color (1 for White, -1 for Black).
            board: Optional Board instance (defaults to self.board).

        Returns:
            List of all strictly legal Move instances.
        """
        b = board or self.board
        if b is None:
            return []
        all_moves: List[Move] = []
        for r in range(b.rows):
            for c in range(b.cols):
                piece = b.get_piece_at((r, c))
                if piece is not None and piece.getColor() == color:
                    destinations = self.get_valid_moves((r, c), b)
                    for dest in destinations:
                        move_type = "capture" if b.get_piece_at(dest) is not None else "normal"
                        all_moves.append(
                            Move(start_pos=(r, c), end_pos=dest, piece=piece, move_type=move_type)
                        )
        return all_moves

    def is_valid_move(self, move: Move, board: Optional[Board] = None) -> bool:
        """Verify whether a specific Move is strictly legal.

        Args:
            move: Move instance to evaluate.
            board: Optional Board instance (defaults to self.board).

        Returns:
            True if the move is legal, False otherwise.
        """
        b = board or self.board
        if b is None or not move.validate():
            return False
        valid_destinations = self.get_valid_moves(move.start_pos, b)
        return move.end_pos in valid_destinations

    def is_checkmate(self, color: int, board: Optional[Board] = None) -> bool:
        """Check if the given player is in checkmate.

        Args:
            color: Player color (1 for White, -1 for Black).
            board: Optional Board instance (defaults to self.board).

        Returns:
            True if player is in check with zero legal responses, False otherwise.
        """
        b = board or self.board
        if not self.is_check(color, b):
            return False
        return len(self.get_all_valid_moves(color, b)) == 0

    def is_stalemate(self, color: int, board: Optional[Board] = None) -> bool:
        """Check if the given player is stalemated (not in check, but no legal moves).

        Args:
            color: Player color (1 for White, -1 for Black).
            board: Optional Board instance (defaults to self.board).

        Returns:
            True if stalemate condition holds, False otherwise.
        """
        b = board or self.board
        if self.is_check(color, b):
            return False
        return len(self.get_all_valid_moves(color, b)) == 0

    def simulate_move(
        self, move: Optional[Move] = None
    ) -> List[Tuple[Tuple[int, int], Optional[Piece]]]:
        """Simulate move execution and return previous state for rollback.

        Args:
            move: Optional Move instance (defaults to self.move).

        Returns:
            List of ((row, col), previous_piece) tuples for restoration.
        """
        m = move or self.move
        b = self.board
        if m is None or b is None:
            return []
        saved_state = [
            (m.start_pos, b.get_piece_at(m.start_pos)),
            (m.end_pos, b.get_piece_at(m.end_pos)),
        ]
        m.execute(b)
        return saved_state
