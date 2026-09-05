"""Bishop chess piece implementation with diagonal move vectors."""

try:
    from .piece import Piece
except ImportError:
    try:
        from model.pieces.piece import Piece
    except ImportError:
        from piece import Piece


class Bishop(Piece):
    """Bishop chess piece that moves and attacks along diagonals."""

    def __init__(self, color: int, piece_type: str = "bishop"):
        """Initialize a Bishop piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece type name (default: "bishop").
        """
        vectors = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        super().__init__(
            color=color,
            piece_type=piece_type,
            vectors=vectors,
            attack_vectors=vectors,
            can_jump=False,
            name="Bishop",
        )
