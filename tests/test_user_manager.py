import pytest
from model.users.user import User
from model.users.manager import UserManager
from model.game.player import Player


def test_user_manager_registration():
    manager = UserManager()
    alice = User("alice", elo=1300)
    uid1 = manager.register_user(alice)
    assert uid1 == 1
    assert manager.get_user(1) is alice

    bob = User("bob", elo=1400)
    uid2 = manager.register_user(bob, user_id=42)
    assert uid2 == 42
    assert manager.find_user(42) is bob
    assert "alice" in manager.user_log


def test_user_manager_link_player():
    manager = UserManager()
    user = User("carol")
    uid = manager.register_user(user)
    player = Player(1, user=user)
    manager.link_player(uid, player)
    assert manager.player_map[uid] is player


def test_user_manager_execute_move():
    manager = UserManager()
    assert manager.execute_move() is True
    manager.record_history("Move recorded")
    assert "Move recorded" in manager.user_history
