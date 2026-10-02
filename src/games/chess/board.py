"""The chess board: eight by eight, and where the pieces start.

This is the chess configuration speaking about its own board. The engine's `Board` knows
how to hold a rectangle; only this file knows what a chess board is.
"""

from model.game.board import Board

#: A chess board is eight ranks by eight files.
DIMENSIONS = (8, 8)


def build_board() -> Board:
    """Build the chess board with the standard starting position.

    Returns:
        Board: An eight by eight board with White on the first two ranks and Black on the
        last two.
    """
    return Board(DIMENSIONS)
