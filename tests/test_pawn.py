import pytest
from model.pieces.pawn import Pawn
from model.pieces.piece import Piece


def test_pawn_inheritance_and_name():
    pawn = Pawn(1)
    assert isinstance(pawn, Piece)
    assert pawn.getName() == "Pawn"
    assert pawn.getType() == "pawn"
    assert pawn.canJump() is False


def test_white_pawn_vectors():
    pawn = Pawn(1)
    assert pawn.getDirections() == [(1, 0)]
    assert pawn.getAttackDirections() == [(1, 1), (1, -1)]
    assert pawn.getInitialVectors() == [(2, 0)]
    assert pawn.hasMoved() is False


def test_black_pawn_vectors():
    pawn = Pawn(-1)
    assert pawn.getDirections() == [(-1, 0)]
    assert pawn.getAttackDirections() == [(-1, 1), [(-1, -1)]] or pawn.getAttackDirections() == [
        (-1, 1),
        (-1, -1),
    ]
    assert pawn.getInitialVectors() == [(-2, 0)]


def test_pawn_moved_state():
    pawn = Pawn(1)
    assert not pawn.hasMoved()
    pawn.setMoved(True)
    assert pawn.hasMoved()
