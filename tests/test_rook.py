import pytest
from model.pieces.rook import Rook
from model.pieces.piece import Piece


def test_rook_initialization():
    rook = Rook("white")
    assert isinstance(rook, Piece)
    assert rook.getColor() == "white"
    assert rook.getType() == "rook"
    assert rook.getName() == "Rook"
    assert rook.canJump() is False


def test_rook_directions():
    rook = Rook(1)
    expected = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    assert rook.getDirections() == expected
    assert rook.getAttackDirections() == expected


def test_rook_moved_state():
    rook = Rook(1)
    assert not rook.hasMoved()
    rook.setMoved(True)
    assert rook.hasMoved()
