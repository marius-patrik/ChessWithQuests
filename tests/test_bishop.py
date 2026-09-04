import pytest
from model.pieces.bishop import Bishop
from model.pieces.piece import Piece


def test_bishop_initialization():
    bishop = Bishop("white")
    assert isinstance(bishop, Piece)
    assert bishop.getColor() == "white"
    assert bishop.getType() == "bishop"
    assert bishop.getName() == "Bishop"
    assert bishop.canJump() is False


def test_bishop_vectors():
    bishop = Bishop(1)
    vectors = bishop.getDirections()
    expected = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    assert vectors == expected
    assert bishop.getAttackDirections() == expected
