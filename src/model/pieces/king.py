try:
    from .piece import Piece
except ImportError:
    try:
        from model.pieces.piece import Piece
    except ImportError:
        from piece import Piece


class King(Piece):
    def __init__(self, color, piece_type="king"):
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
            name="King",
        )
        self._has_moved = False

    def hasMoved(self):
        return self._has_moved

    def setMoved(self, moved=True):
        self._has_moved = moved
