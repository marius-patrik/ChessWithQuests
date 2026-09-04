"""Horse (Knight) chess piece implementation with L-shaped jumping movement."""

try:
    from .piece import Piece
except ImportError:
    try:
        from model.pieces.piece import Piece
    except ImportError:
        from piece import Piece


class Horse(Piece):
    """Horse (Knight) chess piece that moves in an L-shape and can leap over pieces."""

    def __init__(self, color: int, piece_type: str = "horse"):
        """Initialize a Horse piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece type descriptor (default: "horse").
        """
        vectors = [
            (1, 2),
            (2, 1),
            (2, -1),
            (1, -2),
            (-1, -2),
            (-2, -1),
            (-2, 1),
            (-1, 2),
        ]
        super().__init__(
            color=color,
            piece_type=piece_type,
            vectors=vectors,
            attack_vectors=vectors,
            can_jump=True,
            name="Horse",
        )


Knight = Horse
