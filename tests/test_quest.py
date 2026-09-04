import pytest
from model.game.quest import Quest


def test_quest_initialization():
    quest = Quest(name="First Blood", description="Capture your first piece", reward_points=25)
    assert quest.name == "First Blood"
    assert quest.description == "Capture your first piece"
    assert quest.nazev == "First Blood"
    assert quest.popis == "Capture your first piece"
    assert quest.reward_points == 25
    assert not quest.is_completed


def test_quest_validate_with_condition():
    # Condition: captured pieces count >= 1
    quest = Quest(
        name="Capture Master",
        description="Capture at least 1 piece",
        condition_fn=lambda ctx: len(ctx.get("captured", [])) >= 1,
    )
    assert quest.validate({"captured": []}) is False
    assert not quest.is_completed

    assert quest.validate({"captured": ["pawn"]}) is True
    assert quest.is_completed
    # Subsequent validations stay true
    assert quest.validate({}) is True


def test_quest_manual_complete():
    quest = Quest("Test Quest")
    assert not quest.validate()
    quest.complete()
    assert quest.validate() is True
