"""Rook chess piece implementation with orthogonal ray moves and moved state."""

try:
    from .piece import Piece
except ImportError:
    try:
        from model.pieces.piece import Piece
    except ImportError:
        from piece import Piece


class Rook(Piece):
    """Rook piece with rank and file ray marching movement and castling readiness tracking."""

    def __init__(self, color: int, piece_type: str = "rook"):
        """Initialize a Rook piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece descriptor (default: "rook").
        """
        vectors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        super().__init__(
            color=color,
            piece_type=piece_type,
            vectors=vectors,
            attack_vectors=vectors,
            can_jump=False,
            name="Rook",
        )
        self._has_moved = False

    def hasMoved(self) -> bool:
        """Check whether the rook has moved from its initial square.

        Returns:
            bool: True if the rook has moved, False otherwise.
        """
        return self._has_moved

    def setMoved(self, moved: bool = True) -> None:
        """Update whether the rook has moved.

        Args:
            moved: New moved state flag (default: True).
        """
        self._has_moved = moved
