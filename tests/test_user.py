import pytest
from model.users.user import User, Uzivatel


def test_user_initialization():
    user = User(username="alice", name="Alice Smith", email="alice@example.com", elo=1500)
    assert user.username == "alice"
    assert user.name == "Alice Smith"
    assert user.email == "alice@example.com"
    assert user.elo == 1500
    assert user.getEloRating() == 1500
    assert user.completed_quests == []


def test_user_add_quest():
    user = User("bob")
    quest1 = "first_win"
    quest2 = "knight_checkmate"
    user.add_quest(quest1)
    user.add_quest(quest2)
    user.add_quest(quest1)  # duplicate should not be added again
    assert user.get_completed_quests() == [quest1, quest2]


def test_user_diagram_aliases():
    user = Uzivatel(username="charlie", name="Charlie Brown")
    assert user.uzivatelske_jmeno == "charlie"
    assert user.jmeno == "Charlie Brown"
    user.pridej_quest("play_5_games")
    assert user.splnene_kwesty == ["play_5_games"]
