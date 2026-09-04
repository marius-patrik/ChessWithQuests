from typing import Tuple


def pos_to_algebraic(position: Tuple[int, int]) -> str:
    row, col = position
    col_letter = chr(ord("a") + col)
    row_num = str(row + 1)
    return f"{col_letter}{row_num}"


def algebraic_to_pos(algebraic: str) -> Tuple[int, int]:
    col = ord(algebraic[0].lower()) - ord("a")
    row = int(algebraic[1]) - 1
    return (row, col)
