class Figurka:
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


class Kral(Figurka):
    def __init__(self, barva, typ):
        super().__init__(barva, typ)
        self._vektory = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    def getSmery(self):
        return self._vektory

if __name__ == "__main__":
    figurka = Figurka(1, False)
    print(figurka.getSmer())
    print(figurka.__barva)