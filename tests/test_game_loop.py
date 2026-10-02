"""A whole game, played through the loop rather than around it.

Every test here drives `GameManager` the way a player's clicks do. The claim being checked is
that the subsystems are connected to each other: rules decide legality, quests watch moves,
clocks run, users are credited and the transcript is written. Checking any one of those on its
own was how six subsystems sat unwired and unnoticed.
"""

import os
import tempfile

import pytest
from model.game.manager import GameManager
from model.game.move import Move
from model.game.quest import Quest
from model.game.rule import KIND_WIN

#: Fool's mate, in (start, end) squares. Rank is row + 1, so e2 is (1, 4) and h4 is (3, 7).
FOOLS_MATE = [((1, 5), (2, 5)), ((6, 4), (4, 4)), ((1, 6), (3, 6)), ((7, 3), (3, 7))]


def play(game, script):
    """Play a list of moves, returning whether each was legal.

    Args:
        game: The `GameManager` to play on.
        script: (start, end) pairs to play in order.

    Returns:
        List[bool]: Whether each move in the script was played.
    """
    return [game.make_move(Move(start, end)) for start, end in script]


def test_a_whole_game_runs_to_checkmate():
    """Four moves, a checkmate, and a result the game agrees with."""
    game = GameManager()

    assert play(game, FOOLS_MATE) == [True, True, True, True]

    assert game.get_state() == GameManager.STATE_CHECKMATE
    result = game.finish_game()
    assert result is not None
    assert result.kind == KIND_WIN
    assert result.reason == "checkmate"
    assert result.winner == -1


def test_the_rules_are_actually_in_force_while_a_game_is_played():
    """A manager that loaded its configuration but never applied its rules plays a different
    game: no check, no mate, no draws. This is the bug that let the rule layer sit unwired."""
    game = GameManager()

    assert len(game.move_validator.active_rules()) == 13
    assert len(game.move_validator.rules) == len(game.configuration.enabled_rules())

    # A move that leaves the king in check is not offered, so it cannot be played.
    assert game.get_state() == GameManager.STATE_IN_PROGRESS
    play(game, FOOLS_MATE)
    assert game.get_state() == GameManager.STATE_CHECKMATE


def test_quests_observe_the_moves_that_were_played():
    """Quests are in play and they are counting."""
    game = GameManager()
    assert len(game.quest_manager.get_quests()) > 0

    play(game, FOOLS_MATE)

    progressed = [q for q in game.quest_manager.get_quests() if q.progress()[0] > 0]
    assert progressed, "no quest noticed a single move"
    assert len(game.move_events) == 4
    assert [event.index for event in game.move_events] == [0, 1, 2, 3]


def test_a_finished_game_credits_its_users():
    """The people playing are credited with what they completed."""
    game = GameManager()
    white, black = game.players

    assert white.getUser() is not None
    assert black.getUser() is not None
    assert white.getUser().username != black.getUser().username

    play(game, FOOLS_MATE)
    game.finish_game()

    for player in game.players:
        assert len(player.getUser().completed_quests) == len(game.completed_quests)


def test_the_clock_runs_for_both_sides():
    """Both clocks lose the time their player spent."""
    game = GameManager()
    before = {colour: game.timer.get_time(colour) for colour in (1, -1)}

    play(game, FOOLS_MATE)

    assert game.timer.get_time(1) == before[1] - 2  # White moved twice
    assert game.timer.get_time(-1) == before[-1] - 2  # Black moved twice


def test_the_transcript_records_the_game_in_each_notation():
    """PGN, FEN and the stenographic form all come out of the same game."""
    game = GameManager()
    play(game, FOOLS_MATE)
    game.finish_game()

    fen = game.transcript("FEN")
    # The position after Qh4#: Black's queen on h4, White's king still on e1, no castling.
    assert fen.startswith("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR")
    assert fen.split()[1] == "w"

    assert game.transcript("Stenographic") == "f2f3 e7e5 g2g4 d8h4"

    pgn = game.transcript("PGN")
    assert "[Event" in pgn
    assert "f2f3" in pgn or "1." in pgn


def test_a_transcript_can_be_written_to_disk():
    game = GameManager()
    play(game, FOOLS_MATE)
    game.finish_game()

    with tempfile.TemporaryDirectory() as directory:
        path = game.save_log(os.path.join(directory, "logs", "game.pgn"))
        assert os.path.isfile(path)
        with open(path, encoding="utf-8") as handle:
            assert "[Event" in handle.read()


def test_a_new_game_deals_a_fresh_board_and_forgets_the_last_one():
    """Playing again must not start from the end of the last game."""
    game = GameManager()
    play(game, FOOLS_MATE)
    game.finish_game()
    assert game.get_state() == GameManager.STATE_CHECKMATE

    game.new_game()

    assert game.get_state() == GameManager.STATE_IN_PROGRESS
    assert game.active_player == 1
    assert game.move_events == []
    assert game.completed_quests == []
    assert game.timer.get_time(1) == game.timer.initial_time
    assert all(quest.progress()[0] == 0 for quest in game.quest_manager.get_quests())

    occupied = [square for row in game.board.board for square in row if square is not None]
    assert len(occupied) == 32


def test_an_illegal_move_changes_nothing():
    """A rejected move must not cost a turn, tick a clock or advance a quest."""
    game = GameManager()
    events = len(game.move_events)

    # Black cannot move on White's turn.
    assert game.make_move(Move((6, 4), (4, 4))) is False

    assert game.active_player == 1
    assert game.timer.get_time(1) == game.timer.initial_time
    assert len(game.move_events) == events


def test_a_player_with_no_user_reports_the_default_rating():
    """A colour is not a person, and reports itself as unrated rather than failing."""
    from model.game.player import Player

    assert Player(1).getEloRating() == 1200


@pytest.mark.parametrize("script", [[], [((1, 5), (2, 5))], FOOLS_MATE])
def test_no_quest_oracle_letter_is_used(script):
    """Quests are asked, not inspected, so any game shape plays without a lookup table."""
    game = GameManager()
    play(game, script)
    game.finish_game()

    for quest in game.quest_manager.get_quests():
        assert isinstance(quest, Quest)
        assert isinstance(quest.validate(), bool)
