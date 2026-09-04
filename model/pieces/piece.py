class Piece:
    def __init__(self, color, piece_type):
        self.__color = color
        self._type = piece_type
        self._vectors = None

    def getDirections(self):
        return self._vectors

    def getColor(self):
        return self.__color

    def getType(self):
        return self._type


if __name__ == "__main__":
    piece = Piece(1, False)
    print(piece.getDirections())
    print(piece.getColor())