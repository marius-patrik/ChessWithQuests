"""Algebraic coordinate conversion helpers for translating between (row, col) and chess notation."""

from typing import Tuple


def pos_to_algebraic(position: Tuple[int, int]) -> str:
    """Convert a (row, col) coordinate tuple to standard algebraic notation (e.g. (0, 4) -> 'e1').

    Args:
        position: Tuple of (row, col) 0-indexed coordinates.

    Returns:
        Algebraic string notation (e.g. 'e4').
    """
    row, col = position
    col_letter = chr(ord("a") + col)
    row_num = str(row + 1)
    return f"{col_letter}{row_num}"


def algebraic_to_pos(algebraic: str) -> Tuple[int, int]:
    """Convert an algebraic notation coordinate string to a 0-indexed (row, col) tuple.

    Args:
        algebraic: Coordinate string (e.g. 'e4', 'a1').

    Returns:
        Tuple of (row, col) 0-indexed coordinates.
    """
    col = ord(algebraic[0].lower()) - ord("a")
    row = int(algebraic[1]) - 1
    return (row, col)
