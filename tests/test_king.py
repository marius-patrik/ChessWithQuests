import pytest
from model.pieces.king import King
from model.pieces.piece import Piece


def test_king_inheritance():
    king = King("white", "king")
    assert isinstance(king, Piece)


def test_king_attributes():
    king = King("black", "king")
    assert king.getColor() == "black"
    assert king.getType() == "king"


def test_king_directions():
    king = King("white", "king")
    directions = king.getDirections()
    expected_directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    assert directions == expected_directions
    assert len(directions) == 4
