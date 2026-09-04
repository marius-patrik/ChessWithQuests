try:
    from .piece import Piece
except ImportError:
    try:
        from model.pieces.piece import Piece
    except ImportError:
        from piece import Piece


class Pawn(Piece):
    def __init__(self, color, piece_type="pawn"):
        # Diagram note: "Pro pěšáka se vektor vynásobí barvou" (1 or -1)
        direction = 1 if color == 1 or color == "white" else -1
        vectors = [(direction, 0)]
        attack_vectors = [(direction, 1), (direction, -1)]
        super().__init__(
            color=color,
            piece_type=piece_type,
            vectors=vectors,
            attack_vectors=attack_vectors,
            can_jump=False,
            name="Pawn",
        )
        self._initial_vectors = [(direction * 2, 0)]
        self._has_moved = False

    def hasMoved(self):
        return self._has_moved

    def setMoved(self, moved=True):
        self._has_moved = moved

    def getInitialVectors(self):
        return self._initial_vectors
