import os
import pytest
from model.game.logger import GameLogger
from model.game.move import Move


def test_logger_in_memory():
    logger = GameLogger()
    assert logger.get_moves() == []
    move = Move((1, 0), (2, 0))
    logger.log_move(move)
    assert len(logger.get_moves()) == 1
    assert logger.get_moves()[0] is move


def test_logger_with_file(tmp_path):
    log_file = str(tmp_path / "game.log")
    logger = GameLogger()
    logger.create_file(log_file)
    assert os.path.exists(log_file)

    move = Move((1, 0), (3, 0), move_type="double_step")
    logger.log_move(move)

    with open(log_file) as f:
        content = f.read()
    assert "# Chess Game Log" in content
    assert "(1, 0) -> (3, 0)" in content
