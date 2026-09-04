import pytest
from model.pieces.queen import Queen
from model.pieces.piece import Piece


def test_queen_initialization():
    queen = Queen("white")
    assert isinstance(queen, Piece)
    assert queen.getColor() == "white"
    assert queen.getType() == "queen"
    assert queen.getName() == "Queen"
    assert queen.canJump() is False


def test_queen_vectors():
    queen = Queen(1)
    vectors = queen.getDirections()
    assert len(vectors) == 8
    expected = [
        (0, 1),
        (0, -1),
        (1, 0),
        (-1, 0),
        (1, 1),
        (1, -1),
        (-1, 1),
        (-1, -1),
    ]
    assert vectors == expected
    assert queen.getAttackDirections() == expected
