"""The draughts numbering: squares one to thirty-two, counted from the board.

`games/checkers/board.py` knows which squares English draughts is played on, and
`square_number` counts those in board order from one — which is what makes one to four
White's back row and twenty-nine to thirty-two the crown row. It is counted rather than
written out, so it cannot disagree with the rule it is derived from.

**Every test here that names a square pins it against
`tests/test_draughts_perft.py`'s independent derivation of the same arrangement.** That file
derives the numbering from the geometry of the dark squares on purpose, so the published counts
it is gated against cannot be restated in terms of whatever the game happens to implement. Two
derivations asserted equal are one numbering; one derivation asserted equal to itself is
nothing.
"""

import pytest

from games.checkers.board import square_number
from tests.test_draughts_perft import coordinates, square_of

# --- the numbering, which is the board's and the perft gate's at once


def test_the_board_numbers_its_squares_the_way_draughts_does():
    """One to four is White's back row, twenty-nine to thirty-two the crown row.

    Both ends and the count, because a numbering that starts at one and ends at thirty-two is
    not the same thing as the standard arrangement.

    Returns:
        None
    """
    assert square_number(0, 1) == 1
    assert square_number(0, 7) == 4
    assert square_number(7, 0) == 29
    assert square_number(7, 6) == 32

    numbered = {
        square_number(row, col) for row in range(8) for col in range(8) if (row + col) % 2 == 1
    }
    assert numbered == set(range(1, 33))


def test_the_board_numbering_is_the_numbering_the_perft_gate_derives():
    """Two independent derivations of the arrangement, asserted equal for all thirty-two squares.

    `tests/test_draughts_perft.py` derives the numbering from the geometry of the dark squares
    on purpose, so that the published counts it is gated against cannot be restated in terms
    of whatever the game happens to implement. This is the assertion that keeps the production
    numbering from drifting away from it.

    Returns:
        None
    """
    for square in range(1, 33):
        assert square_number(*coordinates(square)) == square
        assert square_of(*coordinates(square)) == square


def test_a_light_square_has_no_number_and_says_so():
    """A square no piece can stand on has no name in this game's numbering.

    Returns:
        None
    """
    with pytest.raises(ValueError, match="light square"):
        square_number(0, 0)

    with pytest.raises(ValueError, match="not on"):
        square_number(8, 1)
