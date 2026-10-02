import json
import os
import textwrap

import pytest

from model.game.board import Board
from model.game.configuration import (
    Configuration,
    load_configuration,
    load_configuration_at,
    load_default_configuration,
)
from model.game.manager import GameManager
from model.game.move import Move
from model.game.rule import KIND_DRAW, KIND_LOSS, KIND_WIN, Result, Rule, resolve_outcomes
from model.game.quest import Quest
from model.game.validator import MoveValidator
from model.game.field import Field
from games.chess.pieces.pawn import Pawn
from games.chess.pieces.rook import Rook

FIXTURE = '''
"""A configuration written entirely outside the engine."""

from model.game.board import Board
from model.game.configuration import Configuration
from model.game.field import Field
from model.game.move import Move
from model.game.quest import Quest
from model.game.rule import KIND_WIN, Result, Rule
from games.chess.pieces.pawn import Pawn
from games.chess.pieces.rook import Rook


class NoPawnMoves(Rule):
    """Forbid every move a pawn could make."""

    default_name = "No pawn moves"

    def permits_move(self, position, move):
        piece = position.get_piece_at(move.start_pos)
        return not (piece is not None and piece.getType() == "pawn")


class Teleport(Move):
    """A move nobody else can make."""

    def __init__(self, start, end):
        super().__init__(start, end, move_type="teleport")


class OfferATeleport(Rule):
    """Offer a move the piece's own vectors cannot express."""

    default_name = "Teleport"

    def available_moves(self, position, piece):
        if position.get_piece_at((0, 0)) is not piece:
            return ()
        return (Teleport((0, 0), (7, 7)),)

    def value_fields(self):
        return [Field("landing", "position", "Landing square", (7, 7))]


class WonAtThreeMoves(Rule):
    """End the game on the third move, whatever the position."""

    default_name = "Three moves"

    def __init__(self, **values):
        super().__init__(**values)
        self.state["moves"] = 0

    def on_move_made(self, position, move):
        self.state["moves"] += 1

    def outcome(self, position):
        if self.state["moves"] >= 3:
            return Result(KIND_WIN, precedence=1, winner=1, reason="three moves")
        return None


class QuietQuest(Quest):
    """A quest with no logic, used to prove quests travel with a configuration."""

    default_name = "Quiet"


def build_configuration():
    """Say exactly what this configuration is. Nothing is discovered by name."""
    return Configuration(
        name="fixture",
        path="",
        board=Board((8, 8), setup_pieces=False),
        pieces=[Rook, Pawn],
        rules=[NoPawnMoves(), OfferATeleport(), WonAtThreeMoves()],
        quests=[QuietQuest(reward=5)],
    )
'''


@pytest.fixture
def games_dir(tmp_path, monkeypatch):
    """A `games/` directory holding one configuration written entirely outside the engine."""
    games = tmp_path / "games"
    package = games / "fixture"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(textwrap.dedent(FIXTURE), encoding="utf-8")
    monkeypatch.setattr("model.game.configuration.games_root", lambda: str(games))
    return str(games)


# --- a rule is a parent class with permissive hooks


def test_the_five_hooks_default_permissively():
    rule = Rule()

    assert rule.permits_move(None, None) is True
    assert list(rule.available_moves(None, None)) == []
    assert rule.outcome(None) is None
    assert rule.on_move_made(None, None) is None
    assert rule.status(None) is None


def test_the_five_hooks_are_the_whole_surface():
    """Four cover forbidding a move or ending the game; the fifth is display. There is no
    sixth hook, because there is nothing else turn-based logic can do."""
    assert {"permits_move", "available_moves", "outcome", "on_move_made", "status"} <= set(
        dir(Rule)
    )


def test_a_rule_declares_its_configured_values():
    class Fifty(Rule):
        default_name = "Fifty"

        def value_fields(self):
            return [Field("plies", "integer", "Plies", 100, minimum=0)]

    rule = Fifty()
    assert rule.value == {"plies": 100}
    assert rule.plies == 100

    configured = Fifty(plies=40)
    assert configured.plies == 40


def test_a_rules_parameters_always_include_enabled():
    class Plain(Rule):
        default_name = "Plain"

        def value_fields(self):
            return [Field("plies", "integer", "Plies", 100)]

    names = [field.name for field in Plain().parameters()]
    assert names[0] == "enabled"
    assert "plies" in names


def test_a_disabled_rule_is_not_in_force():
    class Never(Rule):
        default_name = "Never"

        def permits_move(self, position, move):
            return False

    validator = MoveValidator(Board(setup_pieces=False), rules=[Never(enabled=False)])

    assert validator.is_permitted(Move((0, 0), (1, 1))) is True


# --- precedence


def test_a_decisive_outcome_outranks_a_draw_whatever_the_precedence():
    draw = Result(KIND_DRAW, precedence=1000)
    win = Result(KIND_WIN, precedence=0, winner=1)

    assert resolve_outcomes([draw, win]) is win


def test_the_higher_precedence_wins():
    weak = Result(KIND_DRAW, precedence=1)
    strong = Result(KIND_WIN, precedence=5, winner=-1)

    assert resolve_outcomes([weak, strong]) is strong


def test_equal_precedence_resolves_by_declared_order():
    first = Result(KIND_WIN, precedence=3, winner=1, reason="first")
    second = Result(KIND_WIN, precedence=3, winner=-1, reason="second")

    assert resolve_outcomes([first, second]) is first
    assert resolve_outcomes([second, first]) is second


def test_no_proposal_means_no_outcome():
    assert resolve_outcomes([]) is None


def test_a_result_rejects_an_unknown_kind():
    with pytest.raises(ValueError):
        Result("maybe")


def test_a_result_knows_whether_it_names_a_winner():
    assert Result(KIND_WIN, 1, winner=1).is_decisive is True
    assert Result(KIND_LOSS, 1).is_decisive is True
    assert Result(KIND_DRAW, 1).is_decisive is False


# --- a rule loaded from outside the engine participates in a game


def test_a_configuration_is_loaded_by_name_and_by_path(games_dir):
    by_name = load_configuration("fixture", root=games_dir)
    by_path = load_configuration_at(os.path.join(games_dir, "fixture"), root=games_dir)

    assert by_name.name == "fixture"
    assert by_path.name == "fixture"
    assert [rule.label for rule in by_path.rules] == [
        "No pawn moves",
        "Teleport",
        "Three moves",
    ]


def test_a_custom_rule_participates_in_a_game_without_an_engine_edit(games_dir):
    """The rule forbids pawn moves and offers a teleport the vectors cannot express, and
    both take effect in a game driven through the ordinary manager."""
    configuration = load_configuration("fixture", root=games_dir)
    board = configuration.board
    board.set_piece_at((1, 0), Pawn(1))
    board.set_piece_at((0, 0), Rook(1))

    manager = GameManager(configuration=configuration)

    assert manager.make_move(Move((1, 0), (2, 0))) is False, "the custom rule must forbid it"

    teleport = [move for move in manager.get_valid_moves() if move.end_pos == (7, 7)]
    assert teleport, "the custom rule must offer its move"
    assert manager.make_move(teleport[0]) is True
    assert board.get_piece_at((7, 7)).getName() == "Rook"


def test_two_colliding_rules_resolve_by_precedence(games_dir):
    configuration = load_configuration("fixture", root=games_dir)

    strong = Result(KIND_WIN, precedence=50, winner=1, reason="strong")
    weak = Result(KIND_DRAW, precedence=1)

    class Overrules(Rule):
        default_name = "Overrules"

        def outcome(self, position):
            return strong

    class Underrules(Rule):
        default_name = "Underrules"

        def outcome(self, position):
            return weak

    configuration.rules = [Overrules(), Underrules()]
    manager = GameManager(configuration=configuration)
    manager.move_validator.set_rules(configuration.rules)

    assert manager.get_result() is strong


def test_a_disabled_rule_never_proposes_anything(games_dir):
    configuration = load_configuration("fixture", root=games_dir)
    configuration.rules[2].enabled = False
    manager = GameManager(configuration=configuration)

    for _ in range(5):
        manager.move_validator.notify_move_made(Move((0, 0), (1, 0)), manager.board)

    assert manager.get_result() is None


def test_rules_are_told_about_a_move_that_was_played(games_dir):
    configuration = load_configuration("fixture", root=games_dir)
    manager = GameManager(configuration=configuration)
    manager.board.set_piece_at((0, 0), Rook(1))

    assert manager.make_move(Move((0, 0), (1, 0))) is True
    assert configuration.rules[2].state["moves"] == 1


# --- value persists, state does not


def test_a_rules_state_resets_each_game_and_never_reaches_disk(games_dir, tmp_path):
    configuration = load_configuration("fixture", root=games_dir)

    for _ in range(3):
        configuration.rules[2].on_move_made(configuration.board, Move((0, 0), (1, 0)))
    assert configuration.rules[2].state["moves"] == 3

    written = configuration.save_values(str(tmp_path / "values.json"))
    with open(written, encoding="utf-8") as handle:
        recorded = json.load(handle)

    assert "state" not in json.dumps(recorded)
    assert recorded["rules"]["Three moves"] == {"enabled": True}
    assert configuration.rules[2].value == {}

    configuration.reset()
    assert configuration.rules[2].state == {}
    assert configuration.rules[2].enabled is True


def test_the_configured_value_survives_a_reset(games_dir):
    configuration = load_configuration("fixture", root=games_dir)
    configuration.rules[1].value["landing"] = (3, 3)

    configuration.reset()

    assert configuration.rules[1].value["landing"] == (3, 3)
    assert configuration.rules[1].landing == (3, 3)


# --- loading is bounded


def test_loading_from_outside_the_games_directory_is_refused(games_dir):
    outside = os.path.dirname(games_dir)

    with pytest.raises(ValueError, match="outside"):
        load_configuration_at(outside, root=games_dir)


def test_loading_from_an_absolute_path_elsewhere_is_refused(games_dir, tmp_path):
    sneaky = tmp_path / "sneaky"
    sneaky.mkdir()
    (sneaky / "__init__.py").write_text("def build_configuration(): pass\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside"):
        load_configuration_at(str(sneaky), root=games_dir)


def test_a_configuration_name_cannot_escape_the_directory():
    for name in ("", "..", "../chess", "chess/../secrets"):
        with pytest.raises(ValueError):
            load_configuration(name)


def test_a_directory_without_a_builder_is_reported(games_dir):
    empty = os.path.join(games_dir, "empty")
    os.makedirs(empty, exist_ok=True)
    open(os.path.join(empty, "__init__.py"), "w", encoding="utf-8").close()

    with pytest.raises(FileNotFoundError, match="build_configuration"):
        load_configuration("empty", root=games_dir)

    nothing = os.path.join(games_dir, "nothing-here")
    os.makedirs(nothing, exist_ok=True)

    with pytest.raises(FileNotFoundError, match="__init__"):
        load_configuration_at(nothing, root=games_dir)


def test_the_shipped_default_configuration_loads_with_no_configuration_at_all():
    configuration = load_default_configuration()

    assert configuration.name == "chess"
    assert configuration.board.rows == 8
    assert configuration.board.get_piece_at((0, 0)) is not None
