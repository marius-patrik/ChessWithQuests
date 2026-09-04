import pytest
from model.game.player import Player, Hrac


class MockUser:
    def __init__(self, username, elo):
        self.username = username
        self.elo = elo


def test_player_initialization():
    player = Player(1)
    assert player.getColor() == 1
    assert player.getUser() is None
    assert player.getEloRating() == 1200


def test_player_with_user():
    user = MockUser("grandmaster", 2500)
    player = Player(-1, user=user)
    assert player.getColor() == -1
    assert player.getUser() is user
    assert player.getEloRating() == 2500


def test_player_set_user():
    player = Player(1)
    user = MockUser("beginner", 1000)
    player.setUser(user)
    assert player.getEloRating() == 1000


def test_hrac_alias():
    hrac = Hrac(1)
    assert hrac.get_color() == 1
