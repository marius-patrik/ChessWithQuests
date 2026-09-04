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
