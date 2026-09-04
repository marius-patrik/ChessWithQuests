import pytest
from model.pieces.piece import Piece


def test_piece_initialization():
    piece = Piece("white", "pawn")
    assert piece.getColor() == "white"
    assert piece.getType() == "pawn"
    assert piece.getDirections() is None


def test_piece_different_types():
    piece = Piece(1, False)
    assert piece.getColor() == 1
    assert piece.getType() is False
    assert piece.getDirections() is None


def test_piece_color_encapsulation():
    piece = Piece("black", "rook")
    assert piece.getColor() == "black"
    assert hasattr(piece, "_Piece__color")
    with pytest.raises(AttributeError):
        _ = piece.__color  # type: ignore[attr-defined]


def test_piece_extended_attributes():
    piece = Piece(
        color=1,
        piece_type="custom",
        vectors=[(1, 0)],
        attack_vectors=[(1, 1)],
        can_jump=True,
        name="CustomPiece",
    )
    assert piece.getName() == "CustomPiece"
    assert piece.getDirections() == [(1, 0)]
    assert piece.getAttackDirections() == [(1, 1)]
    assert piece.canJump() is True


def test_piece_default_attack_directions():
    piece = Piece(color=1, piece_type="simple", vectors=[(0, 1)])
    assert piece.getAttackDirections() == [(0, 1)]
    assert piece.canJump() is False
