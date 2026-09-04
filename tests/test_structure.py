import importlib
import pytest

MODULES = [
    "controller",
    "controller.controller",
    "controller.window_controller",
    "model",
    "model.game.board",
    "model.game.logger",
    "model.game.manager",
    "model.game.move",
    "model.game.player",
    "model.game.quest",
    "model.game.timer",
    "model.game.validator",
    "model.misc.export_writers",
    "model.misc.metadata",
    "model.misc.notation",
    "model.misc.quest_manager",
    "model.pieces.bishop",
    "model.pieces.horse",
    "model.pieces.king",
    "model.pieces.pawn",
    "model.pieces.piece",
    "model.pieces.queen",
    "model.pieces.rook",
    "model.pieces.tower",
    "model.users.manager",
    "model.users.user",
    "view",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_module_importable(module_name):
    module = importlib.import_module(module_name)
    assert module is not None
