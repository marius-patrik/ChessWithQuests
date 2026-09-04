import pytest
from model.game.timer import Timer


def test_timer_initialization():
    timer = Timer(300)
    assert timer.player_times == [300, 300]
    assert timer.get_time(0) == 300
    assert timer.get_time(1) == 300
    assert timer.get_time(-1) == 300


def test_timer_countdown():
    timer = Timer(60)
    timer.tick(player=1, elapsed_seconds=10)
    assert timer.get_time(1) == 50
    assert timer.get_time(-1) == 60

    timer.tick(player=-1, elapsed_seconds=20)
    assert timer.get_time(-1) == 40


def test_timer_reset_and_increment():
    timer = Timer(100)
    timer.tick(1, 50)
    assert timer.get_time(1) == 50

    timer.add_time(1, 15)
    assert timer.get_time(1) == 65

    timer.reset_time()
    assert timer.player_times == [100, 100]


def test_timer_expired():
    timer = Timer(5)
    assert not timer.is_expired(1)
    timer.tick(1, 10)
    assert timer.get_time(1) == 0
    assert timer.is_expired(1) is True
