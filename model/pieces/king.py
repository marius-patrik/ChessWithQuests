try:
    from .piece import Piece
except ImportError:
    try:
        from model.pieces.piece import Piece
    except ImportError:
        from piece import Piece


class King(Piece):
    def __init__(self, color, piece_type):
        super().__init__(color, piece_type)
        self._vectors = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    def getDirections(self):
        return self._vectors
