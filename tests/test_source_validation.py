"""The code editor's gate: what may join a configuration and what may not.

`PRD.md` FR-34 requires the editor to validate before code joins a configuration, and
`SCRATCHPAD.md` definition-of-done item 23 says the editor refuses invalid code before it
joins. A rule file with a typo in an import otherwise loads at game start and fails there, in
the middle of a game, with the player holding no idea why.

These tests are about what the check does and, just as importantly, what it does not do: it
confirms a module parses, imports, and exposes the interface the framework calls. It cannot
confirm the logic is right, and the last test in this file says so.
"""

import inspect
import pathlib
import shutil

import pytest

from model.game.configuration import copy_configuration, load_configuration
from model.game.games import DEFAULT_GAME, games_root
from model.game.source_validation import validate_source

#: A rule that is correct, complete and composable. Everything below is a departure from it.
GOOD_RULE = '''
"""A rule that forbids moving off the board."""

from typing import Any, List, Optional

from model.game.rule import Rule


class StayOnBoardRule(Rule):
    """Forbid any move whose destination is outside the board."""

    default_name = "Stay on board"

    def value_fields(self) -> List:
        """Declare nothing configurable."""

        return []

    def permits_move(self, position: Any, move: Any) -> bool:
        """Refuse a move that leaves the board.

        Args:
            position: The board.
            move: The move being considered.

        Returns:
            bool: True when the destination is on the board.
        """
        row, col = move.end_pos
        return position.is_within_bounds(row, col)
'''

#: A quest that is composable, complete and judged.
GOOD_QUEST = '''
"""A quest that counts captures."""

from model.game.events import MoveEvent
from model.game.quest import Quest


class FirstCapture(Quest):
    """Complete on the first capture."""

    default_name = "First capture"
    default_description = "Capture one piece."

    def observe_move(self, event: MoveEvent) -> None:
        """Advance on a capture.

        Args:
            event: The move that was played.

        Returns:
            None
        """
'''


@pytest.fixture
def rules_dir(tmp_path):
    """Yield a configuration's `rules/` directory inside a throwaway `games/` root.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        tuple: The `rules/` directory, and the package name its modules import against.
    """
    configuration = load_configuration(DEFAULT_GAME, root=str(_copy_games(tmp_path)))
    return pathlib.Path(configuration.path) / "rules", configuration.package


def _copy_games(tmp_path) -> pathlib.Path:
    """Copy the shipped chess configuration into a throwaway `games/` root.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        pathlib.Path: The `games/` root the copy is in.
    """
    root = tmp_path / "games"
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        pathlib.Path(games_root()) / DEFAULT_GAME,
        root / DEFAULT_GAME,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return root


def test_a_rule_that_declares_the_interface_is_accepted(rules_dir):
    """The check must pass sound code, or it refuses everything and blocks the product.

    Args:
        rules_dir: The rule directory and its package name.

    Returns:
        None
    """
    directory, package = rules_dir

    report = validate_source(GOOD_RULE, str(directory / "stay.py"), "rule", package=package)

    assert report.ok, report.message()
    assert report.errors == []


@pytest.mark.parametrize(
    "source, expected",
    [
        ("class Broken(Rule)\n    def permits_move(self, p, m)\n        return True\n", "line 1"),
        ("def nothing():\n    return 1\n", "no class inheriting Rule"),
        ("class NotARule:\n    pass\n", "no class inheriting Rule"),
        ("import nonexistent_module_xyz\n", "ModuleNotFoundError"),
        ("raise ValueError('boom')\n", "ValueError"),
        ("from .nowhere import thing\n", "ModuleNotFoundError"),
    ],
)
def test_code_that_cannot_join_a_configuration_is_refused(rules_dir, source, expected):
    """Each way a module fails is refused, and says which failure it was.

    Args:
        rules_dir: The rule directory and its package name.
        source: The module text the player wrote.
        expected: A fragment of the message the report must carry.

    Returns:
        None
    """
    directory, package = rules_dir

    report = validate_source(source, str(directory / "candidate.py"), "rule", package=package)

    assert not report.ok
    assert any(expected in message for message in report.errors), report.errors


def test_a_syntax_error_names_the_line_it_is_on(rules_dir):
    """A syntax error with no line number is not actionable in an editor.

    Args:
        rules_dir: The rule directory and its package name.

    Returns:
        None
    """
    directory, package = rules_dir
    source = "class Fine(Rule):\n" "    pass\n" "\n" "class Broken(Rule)\n" "    pass\n"

    report = validate_source(source, str(directory / "candidate.py"), "rule", package=package)

    assert not report.ok
    assert report.line == 4
    assert "line 4" in report.message()


def test_a_rule_whose_declaration_is_not_fields_is_refused(rules_dir):
    """The settings form renders what a rule declares, so a wrong-shaped declaration is a fault.

    The framework builds a rule before the form ever sees it, so the report says the class
    raised rather than that its declaration was the wrong shape. Both are refusals and both
    name the class and the line; which of the two fires first is an artefact of the order the
    framework does things in, not something this test should depend on.

    Args:
        rules_dir: The rule directory and its package name.

    Returns:
        None
    """
    directory, package = rules_dir
    source = '''
"""A rule whose field declaration is not a list of fields."""

from model.game.rule import Rule


class SilentRule(Rule):
    """Declare its configuration as text rather than as fields."""

    default_name = "Silent"

    def value_fields(self):
        """Declare nothing, wrongly."""

        return "nothing"
'''

    report = validate_source(source, str(directory / "candidate.py"), "rule", package=package)

    assert not report.ok
    assert any("SilentRule (line 7)" in message for message in report.errors), report.errors
    assert any("value_fields" in message for message in report.errors), report.errors


def test_a_member_replaced_with_something_unusable_is_refused(rules_dir):
    """Inheriting is fine; replacing a member the framework reads with a wrong type is not.

    The framework calls `value_fields` and reads `default_name` off every rule it composes. A
    subclass that shadows either with something of the wrong shape breaks the settings form for
    the whole configuration, and it would break at game start with nothing to point at.

    Args:
        rules_dir: The rule directory and its package name.

    Returns:
        None
    """
    directory, package = rules_dir
    source = '''
"""A rule whose name is not text and whose declaration is not callable."""

from model.game.rule import Rule


class MislabelledRule(Rule):
    """A rule whose members are the wrong types."""

    default_name = 42
    value_fields = "not a method"
'''

    report = validate_source(source, str(directory / "candidate.py"), "rule", package=package)

    assert not report.ok
    assert any("default_name is int" in message for message in report.errors)
    assert any("value_fields is str" in message for message in report.errors)


def test_a_quest_replacing_a_method_with_data_is_refused(rules_dir):
    """The quest framework calls `validate` on every quest it judges.

    Args:
        rules_dir: The rule directory and its package name.

    Returns:
        None
    """
    directory, package = rules_dir
    source = '''
"""A quest that cannot be judged."""

from model.game.quest import Quest


class Unjudgeable(Quest):
    """Declare validate as data rather than as a method."""

    default_name = "Unjudgeable"
    default_description = "Nothing can judge this."
    validate = True
'''

    report = validate_source(source, str(directory / "candidate.py"), "quest", package=package)

    assert not report.ok
    assert any("validate is bool" in message for message in report.errors)


def test_a_rule_requiring_an_argument_is_not_refused_for_that(rules_dir):
    """A quest may quite properly demand the piece type it judges.

    Chess's own `CaptureOfType("queen")` does exactly this, and refusing it would refuse the
    shipped configuration. The check has nothing to say about whether the configuration
    supplies the argument, so it must not refuse on that ground.

    Args:
        rules_dir: The rule directory and its package name.

    Returns:
        None
    """
    directory, package = rules_dir
    source = '''
"""A quest that insists on knowing which piece type it judges."""

from model.game.events import MoveEvent
from model.game.quest import Quest


class CaptureOneOf(Quest):
    """Complete on capturing one piece of a named kind."""

    default_name = "Capture one of"
    default_description = "Capture a piece of the named kind."

    def __init__(self, piece_type: str, **values):
        """Require the kind to capture.

        Args:
            piece_type: The kind that must be captured.
            values: Passed to `Quest`.

        Raises:
            ValueError: If no kind is named.
        """
        if not piece_type:
            raise ValueError("a capture-of-type quest must name the piece type")
        super().__init__(**values)
        self.piece_type = piece_type

    def observe_move(self, event: MoveEvent) -> None:
        """Advance on a capture of the named kind.

        Args:
            event: The move that was played.

        Returns:
            None
        """
'''

    report = validate_source(source, str(directory / "candidate.py"), "quest", package=package)

    assert report.ok, report.message()


def test_a_rule_overriding_no_hook_is_warned_about_rather_than_refused(rules_dir):
    """Legal and useless: it changes nothing, but refusing it would be wrong.

    A configuration may compose a rule that only declares values — a rule whose effect is
    carried by its siblings reading those values. That is `RoyalPieceKind`, which the chess
    configuration ships, and it is declared as a value field, so it is not this case. The case
    is a rule that declares no hook *and* no value, which is legal and does nothing at all.

    Args:
        rules_dir: The rule directory and its package name.

    Returns:
        None
    """
    directory, package = rules_dir
    source = '''
"""A rule that declares neither a hook nor a value."""

from model.game.rule import Rule


class InertRule(Rule):
    """Change nothing at all, in either way."""

    default_name = "Inert"
'''

    report = validate_source(source, str(directory / "candidate.py"), "rule", package=package)

    assert report.ok, report.message()
    assert any("overrides no rule hook" in message for message in report.warnings)


def test_the_check_reports_every_problem_not_just_the_first(rules_dir):
    """An editor that reports one error at a time is an editor to iterate against slowly.

    Args:
        rules_dir: The rule directory and its package name.

    Returns:
        None
    """
    directory, package = rules_dir
    source = '''
"""Two rules, both broken."""

from model.game.rule import Rule


class First(Rule):
    """Missing its name."""

    def value_fields(self):
        """Declare nothing, wrongly."""

        return 42


class Second(Rule):
    """Also missing its name."""

    def value_fields(self):
        """Declare nothing, wrongly."""

        return 42
'''

    report = validate_source(source, str(directory / "candidate.py"), "rule", package=package)

    assert not report.ok
    assert len(report.errors) >= 4


def test_a_quest_is_checked_against_the_quest_interface(rules_dir):
    """A rule is not a quest: each kind is held to its own parent class.

    Args:
        rules_dir: The rule directory and its package name.

    Returns:
        None
    """
    directory, package = rules_dir
    path = str(directory / "candidate.py")

    accepted = validate_source(GOOD_QUEST, path, "quest", package=package)
    assert accepted.ok, accepted.message()

    # A rule offered where a quest belongs is not a quest, and saying so is the point.
    refused = validate_source(GOOD_RULE, path, "quest", package=package)
    assert not refused.ok
    assert any("no class inheriting Quest" in message for message in refused.errors)


def test_a_quest_judged_at_an_impossible_moment_is_refused(rules_dir):
    """`when` is the one thing a quest declares about itself, and the engine dispatches on it.

    Args:
        rules_dir: The rule directory and its package name.

    Returns:
        None
    """
    directory, package = rules_dir
    source = '''
"""A quest judged at a moment the engine does not watch for."""

from model.game.quest import Quest


class NeverJudged(Quest):
    """Complete at a moment that does not exist."""

    default_name = "Never judged"
    default_description = "Nothing will ever judge this."
    when = "whenever_i_feel_like_it"
'''

    report = validate_source(source, str(directory / "candidate.py"), "quest", package=package)

    assert not report.ok
    assert any("when=" in message for message in report.errors)


def test_every_rule_the_shipped_configurations_declare_passes_the_check():
    """The check must accept what ships, or it refuses the player's first save for no reason.

    Returns:
        None
    """
    for name in ("chess", "checkers"):
        configuration = load_configuration(name)
        for rule in configuration.rules:
            report = validate_source(
                _module_source(rule),
                str(_module_path(rule)),
                "rule",
                package=configuration.package,
            )
            assert report.ok, f"{name}: {rule.label}: {report.message()}"


def test_every_quest_the_shipped_configurations_declare_passes_the_check():
    """As for rules: the shipped quests are what a player's first quest is copied from.

    Returns:
        None
    """
    for name in ("chess", "checkers"):
        configuration = load_configuration(name)
        for quest in configuration.quests:
            report = validate_source(
                _module_source(quest),
                str(_module_path(quest)),
                "quest",
                package=configuration.package,
            )
            assert report.ok, f"{name}: {quest.name}: {report.message()}"


def test_a_copy_of_the_default_configuration_passes_the_check_too(tmp_path):
    """A variant's rules are the same code under a different package, and must pass as well.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=str(_copy_games(tmp_path)))

    for rule in variant.rules:
        report = validate_source(
            _module_source(rule),
            str(_module_path(rule)),
            "rule",
            package=variant.package,
        )
        assert report.ok, f"{rule.label}: {report.message()}"


def test_the_check_does_not_claim_to_verify_the_logic(rules_dir):
    """A rule that forbids every move is refused by no amount of parsing.

    This is the limit of the gate and it is worth a test, because the alternative is a claim
    the code cannot support: the editor reports that a module is *sound*, never that the rule
    it declares is *right*. Only playing it can say the second.

    Args:
        rules_dir: The rule directory and its package name.

    Returns:
        None
    """
    directory, package = rules_dir
    source = '''
"""A rule that forbids every move, which parses perfectly well."""

from typing import Any

from model.game.rule import Rule


class NoMovesAtAllRule(Rule):
    """Forbid everything. The game becomes unplayable and no check can tell."""

    default_name = "No moves"

    def permits_move(self, position: Any, move: Any) -> bool:
        """Refuse every move.

        Args:
            position: The board.
            move: The move.

        Returns:
            bool: Always False.
        """
        return False
'''

    report = validate_source(source, str(directory / "candidate.py"), "rule", package=package)

    assert report.ok, report.message()
    assert report.warnings == [], "the check must not pretend to have an opinion on logic"


def _module_path(subject) -> pathlib.Path:
    """Return the file a configuration's rule or quest class came from.

    Args:
        subject: The rule or quest instance.

    Returns:
        pathlib.Path: The source file the class was declared in.
    """
    return pathlib.Path(inspect.getfile(type(subject)))


def _module_source(subject) -> str:
    """Return the text of the file a configuration's rule or quest class came from.

    Args:
        subject: The rule or quest instance.

    Returns:
        str: The file's text.
    """
    return _module_path(subject).read_text(encoding="utf-8")
