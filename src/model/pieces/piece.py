class Piece:
    def __init__(
        self,
        color,
        piece_type,
        vectors=None,
        attack_vectors=None,
        can_jump=False,
        name=None,
    ):
        self.__color = color
        self._type = piece_type
        self._vectors = vectors
        self._attack_vectors = attack_vectors
        self._can_jump = can_jump
        self._name = name or (str(piece_type) if piece_type is not None else "Piece")

    def getDirections(self):
        return self._vectors

    def getAttackDirections(self):
        if self._attack_vectors is not None:
            return self._attack_vectors
        return self._vectors

    def canJump(self):
        return self._can_jump

    def getColor(self):
        return self.__color

    def getType(self):
        return self._type

    def getName(self):
        return self._name


if __name__ == "__main__":
    piece = Piece(1, False)
    print(piece.getDirections())
    print(piece.getColor())