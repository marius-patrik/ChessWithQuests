class Piece:
    def __init__(self, barva, typ):
        self.__barva = barva
        self._typ = typ
        self._vektory = None

    def getSmery(self):
        return self._vektory

    def getBarva(self):
        return self.__barva

    def getTyp(self):
        return self._typ


if __name__ == "__main__":
    piece = Piece(1, False)
    print(piece.getSmery())
    print(piece.getBarva())