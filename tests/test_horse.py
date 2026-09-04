import pytest
from model.pieces.horse import Horse, Knight
from model.pieces.piece import Piece


def test_horse_initialization():
    horse = Horse("white")
    assert isinstance(horse, Piece)
    assert horse.getColor() == "white"
    assert horse.getType() == "horse"
    assert horse.getName() == "Horse"
    assert horse.canJump() is True


def test_horse_vectors():
    horse = Horse(1)
    vectors = horse.getDirections()
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
    assert horse.getAttackDirections() == expected


def test_knight_alias():
    knight = Knight("black")
    assert isinstance(knight, Horse)
    assert knight.canJump() is True
