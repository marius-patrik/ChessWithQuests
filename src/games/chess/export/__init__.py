"""The chess export: one file per notation the diagram's writer box enumerates.

Five notations ship here, one writer each, in the order `games/chess/__init__.py` declares
them: the transcript as PGN, the moves in the algebraic naming, the game's own header
record, the position as FEN, and the moves as coordinate pairs. Which notations a game can
write is the configuration's answer, so the engine holds only the protocol every one of them
answers and a variant is a directory that composes its own.

Adding a notation is one file in this directory and one line in `games/chess/__init__.py`.
"""
