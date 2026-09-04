import pytest
from model.misc.quest_manager import QuestManager
from model.game.quest import Quest
from model.users.user import User


def test_quest_manager_registration():
    qm = QuestManager()
    q1 = Quest("Q1")
    qm.register_quest(q1)
    qm.register_quest(q1)  # no duplicates
    assert len(qm.get_quests()) == 1
    assert qm.get_quests()[0] is q1


def test_quest_manager_check_quests_and_award_user():
    qm = QuestManager()
    user = User("player1")

    # Quest: check if total moves >= 10
    q_moves = Quest(
        name="10 Moves",
        condition_fn=lambda ctx: ctx.get("move_count", 0) >= 10,
    )
    qm.register_quest(q_moves)

    # 5 moves: not completed
    completed = qm.check_quests({"move_count": 5}, user=user)
    assert completed == []
    assert user.get_completed_quests() == []

    # 12 moves: completed
    completed = qm.check_quests({"move_count": 12}, user=user)
    assert completed == [q_moves]
    assert user.get_completed_quests() == [q_moves]
    assert qm.get_completed_quests() == [q_moves]
