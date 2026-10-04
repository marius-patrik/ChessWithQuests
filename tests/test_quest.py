import inspect

import pytest

from model.game.board import Board
from model.game.events import OUTCOME_DRAW, OUTCOME_LOSS, OUTCOME_WIN, MoveEvent, ResultEvent
from model.game.field import KINDS, Field
from model.game.move import Move
from model.game.quest import WHEN_AFTER_MOVE, WHEN_AT_GAME_END, Quest
from model.game.quests import (
    ANY_COLOR,
    BUILT_IN_QUESTS,
    CaptureN,
    CaptureOfType,
    CastleN,
    CompositeQuest,
    EnPassantN,
    FirstBlood,
    GameAtLeast,
    GameResult,
    KingOnlyGame,
    MakeCheckN,
    MaterialAhead,
    MovePieceNTimes,
    NeverInCheck,
    Pacifist,
    PromoteN,
    ReachedSquare,
    SurvivePlies,
    SurviveWithoutCapture,
    VisitNSquares,
    WonBy,
)
from model.misc.quest_manager import QuestManager


def move_event(index=0, color=1, piece_type="rook", captured=None, **flags):
    """Build a move event with only the facts a test cares about."""
    move = Move((0, index), (1, index), move_type="capture" if captured else "normal")
    return MoveEvent(
        move=move,
        position=Board(setup_pieces=False),
        color=color,
        piece_type=piece_type,
        captured_piece_type=captured,
        **flags,
    )


def result_event(outcome=OUTCOME_DRAW, winner=None, history=()):
    """Build a finished-game event."""
    return ResultEvent(outcome=outcome, winner=winner, history=list(history))


# --- the shape the diagram draws


def test_validate_takes_no_arguments():
    """The diagram draws `validate() : bool`. Anything else changes the signature the
    specification fixes, so the signature is asserted directly."""
    assert list(inspect.signature(Quest.validate).parameters) == ["self"]

    for quest_type in BUILT_IN_QUESTS:
        assert list(inspect.signature(quest_type.validate).parameters) == [
            "self"
        ], quest_type.__name__


def test_there_is_no_condition_class_and_no_condition_callable():
    """`condition_fn` is gone, and so is any stand-in for it: quest logic lives on the
    quest subclass, exactly as `Pawn(Piece)` carries its own logic."""
    assert not hasattr(Quest, "condition_fn")
    assert not any("condition" in name.lower() for name in dir(Quest))


def test_every_quest_declares_the_four_requirements():
    """FR-20 and FR-21: a quest declares a name, a description, a reward and a `when`."""
    for quest_type in BUILT_IN_QUESTS:
        quest = _minimal(quest_type)
        assert quest.name
        assert isinstance(quest.description, str)
        assert quest.reward >= 0
        assert quest.when in (WHEN_AFTER_MOVE, WHEN_AT_GAME_END)


def _minimal(quest_type):
    """Build one instance of a built-in quest with only its required parameters."""
    import inspect as _inspect

    kwargs = {}
    for parameter in _inspect.signature(quest_type.__init__).parameters.values():
        if parameter.name == "self":
            continue
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        if parameter.default is not parameter.empty:
            continue
        kwargs[parameter.name] = _REQUIRED[parameter.name]
    return quest_type(**kwargs)


#: A valid value for each parameter a built-in quest insists on.
_REQUIRED = {
    "piece_type": "pawn",
    "royal_kind": "king",
    "square": (4, 4),
    "quests": [FirstBlood()],
}


def test_there_are_twenty_built_in_quests():
    assert len(BUILT_IN_QUESTS) == 20
    assert len({quest_type.__name__ for quest_type in BUILT_IN_QUESTS}) == 20


def test_progress_reports_current_and_target():
    quest = CaptureN(count=3)

    assert quest.progress() == (0, 3)
    quest.observe_move(move_event(captured="pawn"))
    assert quest.progress() == (1, 3)
    quest.observe_move(move_event(index=1, captured="pawn"))
    assert quest.progress() == (2, 3)


def test_a_quest_completes_once_and_stays_completed():
    quest = FirstBlood()
    quest.observe_move(move_event(captured="pawn"))

    assert quest.validate() is True
    assert quest.is_completed is True

    quest.reset()
    assert quest.is_completed is False
    assert quest.progress()[0] == 0


def test_a_disabled_quest_is_never_judged():
    quest = FirstBlood(enabled=False)
    manager = QuestManager([quest])

    manager.observe_move(move_event(captured="pawn"))

    assert quest.validate() is False


# --- each quest completes on its intended event and not before


def test_first_blood_completes_only_on_a_capture():
    quest = FirstBlood()

    quest.observe_move(move_event())
    assert quest.validate() is False

    quest.observe_move(move_event(index=1, captured="pawn"))
    assert quest.validate() is True


def test_capture_n_completes_only_at_its_count():
    quest = CaptureN(count=2)

    quest.observe_move(move_event(captured="pawn"))
    assert quest.validate() is False

    quest.observe_move(move_event(index=1, captured="rook"))
    assert quest.validate() is True


def test_capture_n_only_counts_its_own_colour_when_asked():
    quest = CaptureN(count=2, color=1)

    quest.observe_move(move_event(color=-1, captured="pawn"))
    quest.observe_move(move_event(index=1, color=-1, captured="pawn"))
    assert quest.validate() is False

    quest.observe_move(move_event(index=2, color=1, captured="pawn"))
    assert quest.progress() == (1, 2)


def test_capture_of_type_only_counts_the_named_kind():
    quest = CaptureOfType(piece_type="queen")

    quest.observe_move(move_event(captured="pawn"))
    assert quest.validate() is False

    quest.observe_move(move_event(index=1, captured="queen"))
    assert quest.validate() is True


def test_move_piece_n_times_can_be_limited_to_a_kind():
    quest = MovePieceNTimes(count=2, piece_type="knight")

    quest.observe_move(move_event(piece_type="rook"))
    assert quest.validate() is False

    quest.observe_move(move_event(index=1, piece_type="knight"))
    quest.observe_move(move_event(index=2, piece_type="knight"))
    assert quest.validate() is True


def test_reached_square_completes_only_on_that_square():
    quest = ReachedSquare(square=(5, 5))

    quest.observe_move(move_event(piece_type="rook"))
    assert quest.validate() is False

    quest.observe_move(MoveEvent(Move((0, 0), (5, 5)), Board(setup_pieces=False), 1, "rook"))
    assert quest.validate() is True


def test_visit_n_squares_counts_distinct_squares_only():
    quest = VisitNSquares(count=3)

    for _ in range(3):
        quest.observe_move(move_event(piece_type="knight"))
    assert quest.progress() == (1, 3)

    quest.observe_move(move_event(index=2, piece_type="knight"))
    quest.observe_move(move_event(index=3, piece_type="knight"))
    quest.observe_move(move_event(index=4, piece_type="knight"))
    assert quest.validate() is True


def test_survive_plies_completes_only_after_its_own_moves():
    quest = SurvivePlies(count=2, color=1)

    quest.observe_move(move_event(color=-1))
    assert quest.progress() == (0, 2)

    quest.observe_move(move_event(color=1))
    quest.observe_move(move_event(index=1, color=1))
    assert quest.validate() is True


def test_survive_without_capture_ignores_own_captures_but_not_own_moves():
    quest = SurviveWithoutCapture(count=2, color=1)

    quest.observe_move(move_event(color=1, captured="pawn"))
    quest.observe_move(move_event(index=1, color=-1, captured="pawn"))
    assert quest.progress() == (0, 2)

    quest.observe_move(move_event(index=2, color=1))
    quest.observe_move(move_event(index=3, color=1))
    assert quest.validate() is True


def test_castle_promote_and_en_passant_quests_read_their_own_flag():
    for quest_type, flag in (
        (CastleN, "is_castling"),
        (PromoteN, "is_promotion"),
        (EnPassantN, "is_en_passant"),
    ):
        quest = quest_type()

        quest.observe_move(move_event())
        assert quest.validate() is False, quest_type.__name__

        quest.observe_move(move_event(index=1, **{flag: True}))
        assert quest.validate() is True, quest_type.__name__


def test_make_check_n_reads_the_check_flag():
    quest = MakeCheckN(count=2)

    quest.observe_move(move_event(is_check=True))
    assert quest.validate() is False

    quest.observe_move(move_event(index=1, is_check=True))
    assert quest.validate() is True


def test_never_in_check_does_not_complete_before_the_game_ends():
    """The whole point is that nothing before the last move can establish it, so this quest
    is judged when the game ends."""
    quest = NeverInCheck(color=1)

    for index in range(5):
        quest.observe_move(move_event(index=index))
    assert quest.validate() is False

    quest.observe_result(result_event())
    assert quest.validate() is True


def test_never_in_check_fails_when_check_was_suffered():
    quest = NeverInCheck(color=1)

    quest.observe_move(move_event(in_check=True))
    quest.observe_result(result_event())

    assert quest.validate() is False


def test_king_only_game_passes_only_when_nothing_else_moved():
    quest = KingOnlyGame(royal_kind="king")

    quest.observe_move(move_event(piece_type="king"))
    quest.observe_result(result_event())
    assert quest.validate() is True

    other = KingOnlyGame(royal_kind="king")
    other.observe_move(move_event(piece_type="rook"))
    other.observe_result(result_event())
    assert other.validate() is False


def test_game_result_completes_only_on_its_outcome():
    quest = GameResult(outcome=OUTCOME_WIN)

    quest.observe_result(result_event(outcome=OUTCOME_DRAW))
    assert quest.validate() is False

    quest.observe_result(result_event(outcome=OUTCOME_WIN, winner=1))
    assert quest.validate() is True


def test_won_by_completes_only_for_its_colour():
    quest = WonBy(color=-1)

    quest.observe_result(result_event(outcome=OUTCOME_WIN, winner=1))
    assert quest.validate() is False

    quest.observe_result(result_event(outcome=OUTCOME_LOSS, winner=-1))
    assert quest.validate() is True


def test_game_at_least_completes_only_for_a_long_enough_game():
    quest = GameAtLeast(count=3)

    quest.observe_result(result_event(history=[move_event(), move_event(index=1)]))
    assert quest.validate() is False

    quest.observe_result(
        result_event(history=[move_event(), move_event(index=1), move_event(index=2)])
    )
    assert quest.validate() is True


def test_material_ahead_completes_only_when_the_margin_is_reached():
    history = [
        move_event(captured="pawn"),
        move_event(index=1, color=-1, captured="pawn"),
        move_event(index=2, captured="pawn"),
    ]
    quest = MaterialAhead(color=1, margin=2)

    quest.observe_result(result_event(history=history))
    assert quest.validate() is False

    quest = MaterialAhead(color=1, margin=1)
    quest.observe_result(result_event(history=history))
    assert quest.validate() is True


def test_pacifist_completes_only_when_nothing_was_captured():
    quest = Pacifist()

    quest.observe_result(result_event(history=[move_event(), move_event(index=1)]))
    assert quest.validate() is True

    quest = Pacifist()
    quest.observe_result(result_event(history=[move_event(captured="pawn")]))
    assert quest.validate() is False


def test_pacifist_can_be_scoped_to_one_colour():
    history = [move_event(color=-1, captured="pawn")]

    scoped = Pacifist(color=1)
    scoped.observe_result(result_event(history=history))
    assert scoped.validate() is True

    scoped = Pacifist(color=-1)
    scoped.observe_result(result_event(history=history))
    assert scoped.validate() is False


def test_composite_quest_requires_all_or_any():
    first = CaptureN(count=1)
    second = CastleN()

    all_of = CompositeQuest([first, second], mode="all")
    # A member that watches moves is told them live; `observe_result` must not replay them,
    # or a member's counts double and a composite asks for a target nothing reaches.
    all_of.observe_move(move_event(captured="pawn"))
    all_of.observe_result(result_event(history=[move_event(captured="pawn")]))
    assert first.progress()[0] == 1, f"the member counted {first.progress()[0]} captures, not 1"
    assert first.validate() is True
    assert second.validate() is False
    assert all_of.validate() is False

    any_of = CompositeQuest([first, second], mode="any")
    any_of.observe_move(move_event(captured="pawn"))
    any_of.observe_result(result_event(history=[move_event(captured="pawn")]))
    assert any_of.validate() is True


def test_composite_quest_passes_moves_through_to_its_members():
    member = CastleN()
    composite = CompositeQuest([member], mode="all")

    composite.observe_move(move_event())
    assert member.progress() == (0, 1)

    composite.observe_move(move_event(index=1, is_castling=True))
    assert member.validate() is True


# --- quest parameters are what a form asks the player for


def test_every_quest_declares_parameters_a_form_can_render():
    for quest_type in BUILT_IN_QUESTS:
        quest = _minimal(quest_type)
        spec = quest.parameters()

        assert spec, quest_type.__name__
        for field in spec:
            assert isinstance(field, Field)
            assert field.kind in KINDS, quest_type.__name__
            assert field.name, quest_type.__name__
            assert field.label, quest_type.__name__


def test_a_reward_is_always_a_declared_parameter():
    for quest_type in BUILT_IN_QUESTS:
        names = [field.name for field in _minimal(quest_type).parameters()]
        assert "reward" in names, quest_type.__name__


# --- the manager holds the quests in play, and only those


def test_manager_holds_only_the_quests_in_play():
    in_play = [FirstBlood(), GameResult()]
    manager = QuestManager(in_play)

    assert manager.get_quests() == in_play
    assert manager.in_play(WHEN_AFTER_MOVE) == [in_play[0]]
    assert manager.in_play(WHEN_AT_GAME_END) == [in_play[1]]


def test_manager_takes_a_copy_of_the_list_it_is_given():
    quests = [FirstBlood()]
    manager = QuestManager(quests)
    quests.append(GameResult())

    assert len(manager.get_quests()) == 1


def test_manager_routes_each_event_to_the_quests_waiting_for_it():
    after_move = CaptureN(count=1)
    at_end = WonBy(color=1)
    manager = QuestManager([after_move, at_end])

    completed = manager.observe_move(move_event(captured="pawn"))

    assert completed == [after_move]
    assert at_end.validate() is False

    completed = manager.observe_result(result_event(outcome=OUTCOME_WIN, winner=1))
    assert completed == [at_end]


def test_manager_reports_a_quest_as_completed_only_once():
    quest = FirstBlood()
    manager = QuestManager([quest])

    assert manager.observe_move(move_event(captured="pawn")) == [quest]
    assert manager.observe_move(move_event(index=1, captured="pawn")) == []


def test_manager_clears_quests_for_the_next_game():
    """Quests in play belong to one game; a new game starts from the configuration, not
    from the last game's answers."""
    manager = QuestManager([FirstBlood(), GameResult()])
    manager.observe_move(move_event(captured="pawn"))
    manager.observe_result(result_event(outcome=OUTCOME_DRAW))
    assert len(manager.get_completed_quests()) == 2

    manager.reset()

    assert manager.get_completed_quests() == []
    assert all(quest.progress()[0] == 0 for quest in manager.get_quests())


def test_experience_is_derived_from_the_completed_quests():
    """FR-24: the total is the sum of the completed rewards, so a user needs no field."""
    done = [FirstBlood(reward=25), GameAtLeast(reward=40)]
    manager = QuestManager([*done, CaptureN(count=5, reward=99)])

    manager.observe_move(move_event(captured="pawn"))
    manager.observe_result(result_event(history=[move_event()]))

    assert manager.total_reward() == 65


def test_a_disabled_quest_contributes_no_experience():
    manager = QuestManager([FirstBlood(reward=25, enabled=False)])
    manager.observe_move(move_event(captured="pawn"))

    assert manager.total_reward() == 0


def test_material_ahead_is_not_satisfied_by_being_behind():
    """The quest says "ahead". `abs(taken - lost)` also answered yes to three pieces down."""
    from model.game.events import ResultEvent
    from model.game.quests import MaterialAhead

    def result_with(white_took, black_took):
        """Build a finished game in which each side took the given number of pieces."""
        history = [
            MoveEvent(
                move=object(),
                position=None,
                color=1,
                captured_piece_type="pawn",
            )
            for _ in range(white_took)
        ]
        history += [
            MoveEvent(
                move=object(),
                position=None,
                color=-1,
                captured_piece_type="pawn",
            )
            for _ in range(black_took)
        ]
        return ResultEvent(outcome="win", winner=1, history=history)

    behind = MaterialAhead(color=1, margin=3)
    behind.observe_result(result_with(white_took=0, black_took=3))
    assert behind.validate() is False, "three pieces down completed a quest asking to be ahead"

    ahead = MaterialAhead(color=1, margin=3)
    ahead.observe_result(result_with(white_took=3, black_took=0))
    assert ahead.validate() is True


def test_a_composite_does_not_count_its_members_moves_twice():
    """Each move was given live and then the whole history replayed, doubling every count."""
    from model.game.events import MoveEvent
    from model.game.quests import CaptureN, CompositeQuest

    member = CaptureN(count=3)
    composite = CompositeQuest([member])

    history = [
        MoveEvent(move=object(), position=None, color=1, captured_piece_type="pawn")
        for _ in range(3)
    ]
    composite.observe_move(history[0])
    composite.observe_move(history[1])
    composite.observe_move(history[2])
    from model.game.events import ResultEvent

    composite.observe_result(ResultEvent(outcome="win", winner=1, history=history))

    assert member.progress()[0] == 3, f"the member counted {member.progress()[0]} captures, not 3"
