"""Rook: a ray mover along the ranks and files."""

from model.pieces.piece import Piece


class Rook(Piece):
    """Slides any distance along the ranks and files."""

    def __init__(self, color: int, piece_type: str = "rook"):
        """Initialize a Rook piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece descriptor (default: "rook").
        """
        vectors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        super().__init__(
            symbols=("♖", "♜"),
            fen="R",
            color=color,
            piece_type=piece_type,
            vectors=vectors,
            attack_vectors=vectors,
            can_jump=False,
            name="Rook",
        )


#: Czech alias for `Rook`, as `PRD.md` section 5 and `Věž` in the diagram require.
Vez = Rook
