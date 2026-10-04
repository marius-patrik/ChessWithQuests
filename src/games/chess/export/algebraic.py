"""Algebraic coordinate conversion: the chess naming of the squares.

`e4` is a chess name for a square, and it belongs to chess. The engine deals in `(row, col)`
pairs, and this is the one place that knows a column is a letter and a row is counted from
White's side. A game whose board is not eight files wide has no such naming, so it writes
nothing here — which is what "a game with no FEN representation has no FEN exporter" means in
`notes/object_model.md`.

Only the letters `a` to `h` and the single-digit ranks of a chess board are handled. That is
deliberate rather than merely convenient: `algebraic_to_pos` reads the rank as
`int(algebraic[1])`, which is the whole reason this conversion cannot describe a board of any
other width, and pretending otherwise would move the defect rather than remove it.
"""

from typing import Tuple


def file_letter(col: int) -> str:
    """Return the letter chess names a file by.

    A board is told the name of each of its columns rather than computing one: the engine's
    `Board.file_label` numbers them, and this is what chess's board answers instead. Keeping
    the letter here rather than in the board is what stops the naming being written twice.

    Args:
        col: The file's 0-indexed number.

    Returns:
        str: The file's letter, so column 0 is `a`.
    """
    return chr(ord("a") + col)


def pos_to_algebraic(position: Tuple[int, int]) -> str:
    """Convert a (row, col) coordinate tuple to chess algebraic notation (e.g. (0, 4) -> 'e1').

    Args:
        position: Tuple of (row, col) 0-indexed coordinates. Row 0 is White's first rank.

    Returns:
        str: Algebraic string notation (e.g. 'e4').
    """
    row, col = position
    return f"{file_letter(col)}{row + 1}"


def algebraic_to_pos(algebraic: str) -> Tuple[int, int]:
    """Convert an algebraic notation coordinate string to a 0-indexed (row, col) tuple.

    Args:
        algebraic: Coordinate string (e.g. 'e4', 'a1').

    Returns:
        Tuple[int, int]: Tuple of (row, col) 0-indexed coordinates.
    """
    col = ord(algebraic[0].lower()) - ord("a")
    row = int(algebraic[1]) - 1
    return (row, col)
