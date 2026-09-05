"""Queen chess piece implementation combining orthogonal and diagonal ray movements."""

try:
    from .piece import Piece
except ImportError:
    try:
        from model.pieces.piece import Piece
    except ImportError:
        from piece import Piece


class Queen(Piece):
    """Queen chess piece with 8-direction ray movement (orthogonal and diagonal)."""

    def __init__(self, color: int, piece_type: str = "queen"):
        """Initialize a Queen piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece descriptor (default: "queen").
        """
        vectors = [
            (0, 1),
            (0, -1),
            (1, 0),
            (-1, 0),
            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1),
        ]
        super().__init__(
            color=color,
            piece_type=piece_type,
            vectors=vectors,
            attack_vectors=vectors,
            can_jump=False,
            name="Queen",
        )
