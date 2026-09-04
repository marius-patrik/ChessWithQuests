try:
    from .piece import Piece
except ImportError:
    try:
        from model.pieces.piece import Piece
    except ImportError:
        from piece import Piece


class King(Piece):
    def __init__(self, barva, typ):
        super().__init__(barva, typ)
        self._vektory = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    def getSmery(self):
        return self._vektory
