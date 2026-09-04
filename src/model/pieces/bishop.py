try:
    from .piece import Piece
except ImportError:
    try:
        from model.pieces.piece import Piece
    except ImportError:
        from piece import Piece


class Bishop(Piece):
    def __init__(self, color, piece_type="bishop"):
        vectors = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        super().__init__(
            color=color,
            piece_type=piece_type,
            vectors=vectors,
            attack_vectors=vectors,
            can_jump=False,
            name="Bishop",
        )
