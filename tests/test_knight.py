import pytest
from games.chess.pieces.knight import Knight, Knight
from model.pieces.piece import Piece


def test_knight_initialization():
    knight = Knight("white")
    assert isinstance(knight, Piece)
    assert knight.getColor() == "white"
    assert knight.getType() == "horse"
    assert knight.getName() == "Knight"
    assert knight.canJump() is True


def test_knight_vectors():
    knight = Knight(1)
    vectors = knight.getDirections()
    assert len(vectors) == 8
    expected = [
        (1, 2),
        (2, 1),
        (2, -1),
        (1, -2),
        (-1, -2),
        (-2, -1),
        (-2, 1),
        (-1, 2),
    ]
    assert vectors == expected
    assert knight.getAttackDirections() == expected


def test_knight_alias():
    knight = Knight("black")
    assert isinstance(knight, Knight)
    assert knight.canJump() is True
