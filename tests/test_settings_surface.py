"""The settings surface: the parts of it that are rules about data, not widgets.

`SCRATCHPAD.md` item 18 says the default configuration "cannot be edited or deleted", and
`PRD.md` FR-27 says a variant starts by duplicating it. Nothing enforced either: a
configuration is a directory, and `Configuration.save_values()` wrote into it with no guard
at all. These tests hold the guard in place and the directory operations around it — copy,
rename, delete — because those are the moves that make "duplicate it and edit that"
reachable rather than an instruction nobody can follow.

The second half of this file is the code editor's gate. `PRD.md` FR-34 requires the editor
to validate before code joins a configuration, and definition-of-done item 23 says the editor
refuses invalid code before it joins. A rule file with a typo in an import otherwise loads at
game start and fails there, mid-game, with the player holding no idea why.

What that check does and does not do is worth stating plainly, because the alternative is a
claim the code cannot support: it confirms a module parses, imports, and exposes an interface
the framework can call. It cannot confirm the logic is right. A rule that forbids every move
passes it, and the last test in this file says so.

The widget-level surface is exercised where there is a display and skipped where there is
not, as `tests/test_view.py` already does.
"""

import inspect
import os
import pathlib
import shutil
import tkinter as tk

import pytest

from model.game.configuration import (
    Configuration,
    copy_configuration,
    delete_configuration,
    load_configuration,
    load_configuration_at,
    rename_configuration,
)
from model.game.games import DEFAULT_GAME, games_root
from model.game.source_validation import validate_source
from view.code_editor import CodeEditor, editable_sources
from view.settings_dialog import SECTIONS, SettingsDialog


@pytest.fixture
def games_dir(tmp_path):
    """Copy the shipped chess configuration into a throwaway `games/` root.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        str: The path of the `games/` root, which is what the library functions are pointed
        at so the shipped directory is never touched.
    """
    root = tmp_path / "games"
    shutil.copytree(
        pathlib.Path(games_root()) / DEFAULT_GAME,
        root / DEFAULT_GAME,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return str(root)


def test_the_default_configuration_refuses_to_be_written_into(games_dir):
    """Editing the default is the one edit that must not happen, and it now raises.

    Without the guard this writes `configuration.json` into `games/chess/` and the reference
    every variant is duplicated from is no longer what shipped.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    default = load_configuration(DEFAULT_GAME, root=games_dir)

    with pytest.raises(PermissionError):
        default.save_values()

    assert not os.path.exists(os.path.join(default.path, "configuration.json"))


def test_the_default_configuration_can_still_be_exported(games_dir, tmp_path):
    """Refusing to edit it is not refusing to read it: an export elsewhere still works.

    The guard is scoped to the default configuration's own directory, because writing a
    record of its values somewhere else is not editing the configuration.

    Args:
        games_dir: The throwaway `games/` root.
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    default = load_configuration(DEFAULT_GAME, root=games_dir)

    written = default.save_values(str(tmp_path / "chess.json"))

    assert os.path.isfile(written)


def test_the_default_configuration_cannot_be_renamed_or_deleted(games_dir):
    """FR-27 covers deletion and FR-28 covers renaming; both exclude the default.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    with pytest.raises(PermissionError):
        rename_configuration(DEFAULT_GAME, "renamed", root=games_dir)
    with pytest.raises(PermissionError):
        delete_configuration(DEFAULT_GAME, root=games_dir)

    assert os.path.isdir(os.path.join(games_dir, DEFAULT_GAME))


def test_a_variant_is_written_where_the_guard_does_not_reach(games_dir):
    """A copy is editable, which is what makes "duplicate it and edit that" true.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    written = variant.save_values()

    assert written.endswith(os.path.join("house", "configuration.json"))
    assert os.path.isfile(written)


def test_a_copied_configuration_is_a_variant_and_not_the_original(games_dir):
    """Copying is the extension mechanism, so the copy must be its own configuration.

    `SCRATCHPAD.md` section 2: `cp -r games/chess games/house` and change what differs. A copy
    whose files reached back into the original would look edited and play the original, so
    this asserts the copy has its own directory, its own source, and a board built from that
    source rather than from `games/chess`.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    assert variant.name == "house"
    assert variant.path == os.path.join(games_dir, "house")
    assert variant.path != os.path.join(games_dir, DEFAULT_GAME)

    board_source = pathlib.Path(variant.path) / "board.py"
    board_source.write_text(
        '"""The house board: ten by ten, which chess is not."""\n\n'
        "from model.game.board import Board\n\n"
        "DIMENSIONS = (10, 10)\n\n"
        "def build_board(rows=DIMENSIONS[0], cols=DIMENSIONS[1]):\n"
        '    """Build the house board."""\n\n'
        "    return Board((rows, cols))\n",
        encoding="utf-8",
    )
    assert "ten by ten" in board_source.read_text(encoding="utf-8")
    assert "ten by ten" not in (pathlib.Path(games_dir) / DEFAULT_GAME / "board.py").read_text(
        encoding="utf-8"
    )


def test_the_copied_directory_is_a_real_copy_and_not_a_link(games_dir):
    """A copy that shares one inode with the original is an alias, not a variant.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    original_board = os.path.join(games_dir, DEFAULT_GAME, "board.py")
    copied_board = os.path.join(variant.path, "board.py")
    assert os.path.isfile(copied_board)
    assert os.stat(original_board).st_ino != os.stat(copied_board).st_ino


def test_a_copy_carries_no_bytecode_from_the_configuration_it_came_from(games_dir):
    """A copy is source, not the original's compiled form of it.

    `copytree` copies everything by default, so a copy made naively arrives holding the
    original's `__pycache__`. Python discards bytecode whose source has moved on, so this is
    hygiene rather than a live failure — but the variant directory is what a player edits and
    re-reads, and shipping it full of another configuration's compiled modules is a trap
    with no upside.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    original_cache = pathlib.Path(games_dir) / DEFAULT_GAME / "rules" / "__pycache__"
    original_cache.mkdir(parents=True, exist_ok=True)
    (original_cache / "stale_marker.pyc").write_bytes(b"not real bytecode")

    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    assert (original_cache / "stale_marker.pyc").is_file()
    assert not (pathlib.Path(variant.path) / "rules" / "__pycache__" / "stale_marker.pyc").exists()


def test_copying_refuses_to_overwrite_a_configuration_that_exists(games_dir):
    """A copy that silently replaced an existing variant would destroy another variant.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    with pytest.raises(FileExistsError):
        copy_configuration(DEFAULT_GAME, "house", root=games_dir)


def test_a_name_that_is_not_a_directory_name_is_refused(games_dir):
    """A configuration name is a directory name and a module name at once.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    for name in ("../escape", "sub/house", "", ".", "not an identifier"):
        with pytest.raises(ValueError):
            copy_configuration(DEFAULT_GAME, name, root=games_dir)


def test_renaming_a_variant_leaves_it_loadable_and_changes_only_the_name(games_dir):
    """A rename is a directory move, so it must not disturb what the variant is.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    renamed = rename_configuration("house", "villa", root=games_dir)

    assert renamed.name == "villa"
    assert os.path.isdir(os.path.join(games_dir, "villa"))
    assert not os.path.exists(os.path.join(games_dir, "house"))
    assert len(renamed.enabled_rules()) > 0


def test_a_deleted_variant_is_gone_and_nothing_else_is(games_dir):
    """Deleting removes the variant directory and leaves the rest of `games/` alone.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    delete_configuration("house", root=games_dir)

    assert not os.path.exists(os.path.join(games_dir, "house"))
    assert os.path.isdir(os.path.join(games_dir, DEFAULT_GAME))


def test_a_name_that_is_not_one_path_segment_cannot_reach_the_disk(games_dir, tmp_path):
    """`delete_configuration("..")` removed the directory *containing* `games/`.

    The name was joined to the root and handed to `shutil.rmtree` without ever being asked
    whether it was a single path segment, so a relative marker reached everything above the
    configurations. The same hole let a rename move that directory aside.

    Args:
        games_dir: The throwaway `games/` root.
        tmp_path: pytest's temporary directory, the parent of `games/`.

    Returns:
        None
    """
    outside = tmp_path / "precious.txt"
    outside.write_text("not a configuration", encoding="utf-8")

    with pytest.raises(ValueError):
        delete_configuration("..", root=games_dir)
    with pytest.raises(ValueError):
        delete_configuration(os.path.join(DEFAULT_GAME, ".."), root=games_dir)
    with pytest.raises(ValueError):
        rename_configuration("..", "elsewhere", root=games_dir)
    with pytest.raises(ValueError):
        rename_configuration(DEFAULT_GAME, "../elsewhere", root=games_dir)

    assert outside.read_text(encoding="utf-8") == "not a configuration"
    assert os.path.isdir(os.path.join(games_dir, DEFAULT_GAME))
    assert os.path.isdir(str(tmp_path)), "the directory holding games/ must still be there"


def test_deleting_a_configuration_that_is_not_there_says_so(games_dir):
    """Deleting nothing must not read as having deleted the default.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    with pytest.raises(FileNotFoundError):
        delete_configuration("absent", root=games_dir)


def test_a_configuration_saved_outside_its_own_directory_is_allowed_for_any_name(games_dir):
    """The guard is the default configuration, not the act of writing a file.

    Args:
        games_dir: The throwaway `games/` root.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    assert variant.is_default is False
    assert Configuration(name="house", path=variant.path).is_default is False


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


# --- the editor itself


def test_the_editor_opens_a_rules_file_with_its_text(tk_root, games_dir):
    """The editor is where a rule is authored, so it must show what the file holds.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    target = os.path.join(variant.path, "rules", "royal.py")

    editor = CodeEditor(tk_root, target, "rule", package=variant.package, root=variant.path)

    assert "RoyalPieceKind" in editor.source()
    assert "RoyalPieceKind" in pathlib.Path(target).read_text(encoding="utf-8")
    editor.close()


def test_the_editor_refuses_a_file_outside_the_configuration_being_edited(
    tk_root, games_dir, tmp_path
):
    """The bound from `PRD.md` section 3.3: code loads from the variant directory, nowhere else.

    An editor that opened an arbitrary path would read and write anywhere on the disk, and a
    configuration's rules are Python the product runs. Refusing is better than trusting the
    caller, because the caller is a widget.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    outside = tmp_path / "elsewhere.py"
    outside.write_text('"""Not part of any configuration."""\n', encoding="utf-8")

    with pytest.raises(ValueError):
        CodeEditor(tk_root, str(outside), "rule", package=variant.package, root=variant.path)

    assert outside.read_text(encoding="utf-8") == '"""Not part of any configuration."""\n'


def test_the_editor_does_not_write_code_the_check_refuses(tk_root, games_dir):
    """FR-34 and definition-of-done item 23: the editor refuses invalid code before it joins.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    target = os.path.join(variant.path, "rules", "half_typed.py")
    pathlib.Path(target).write_text('"""What was there before."""\n', encoding="utf-8")

    editor = CodeEditor(tk_root, target, "rule", package=variant.package, root=variant.path)
    editor.text.delete("1.0", tk.END)
    editor.text.insert("1.0", "class HalfTyped(Rule)\n    pass\n")

    assert editor.save() is None
    assert pathlib.Path(target).read_text(encoding="utf-8") == '"""What was there before."""\n'
    assert "line 1" in editor.verdict.get()
    editor.close()


def test_the_editor_writes_code_the_check_accepts(tk_root, games_dir):
    """The other half: a rule that passes the check reaches the file it names.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    target = os.path.join(variant.path, "rules", "brand_new.py")
    saved = []

    editor = CodeEditor(
        tk_root,
        target,
        "rule",
        package=variant.package,
        root=variant.path,
        on_saved=saved.append,
    )
    editor.text.insert("1.0", GOOD_RULE)

    assert editor.save() == target
    assert "StayOnBoardRule" in pathlib.Path(target).read_text(encoding="utf-8")
    assert saved == [target]
    editor.close()


def test_the_editor_writes_into_the_variant_and_leaves_the_original_alone(tk_root, games_dir):
    """Editing a rule in a variant must not change the configuration it was duplicated from.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    original = pathlib.Path(games_dir) / DEFAULT_GAME / "rules" / "royal.py"
    before = original.read_text(encoding="utf-8")

    editor = CodeEditor(
        tk_root,
        os.path.join(variant.path, "rules", "royal.py"),
        "rule",
        package=variant.package,
        root=variant.path,
    )
    editor.text.insert(tk.END, "\n\nclass ExtraRule(Rule):\n    default_name = 'Extra'\n")
    editor.save()

    assert "ExtraRule" in pathlib.Path(variant.path, "rules", "royal.py").read_text(
        encoding="utf-8"
    )
    assert original.read_text(encoding="utf-8") == before
    editor.close()


def test_the_editor_holds_a_quest_file_to_the_quest_interface(tk_root, games_dir):
    """A rule offered where a quest belongs is refused, because the two are different things.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    target = os.path.join(variant.path, "quests", "not_a_quest.py")

    editor = CodeEditor(tk_root, target, "quest", package=variant.package, root=variant.path)
    editor.text.insert("1.0", GOOD_RULE)

    assert editor.save() is None
    assert not os.path.exists(target)
    assert "no class inheriting Quest" in editor.verdict.get()
    editor.close()


def test_editable_sources_lists_what_a_player_may_edit(games_dir):
    """The Rules and Quests sections offer the files, so this is what they offer from.

    Args:
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)

    found = editable_sources(variant.path, "rules")

    assert [os.path.basename(path) for path in found] == sorted(
        name for name in os.listdir(os.path.join(variant.path, "rules")) if name.endswith(".py")
    )
    assert all(path.endswith(".py") for path in found)
    assert editable_sources(os.path.join(variant.path, "nowhere"), "rules") == []


# --- the five sections and the corner selector


def test_the_form_has_a_section_for_each_configurable_surface(tk_root, games_dir):
    """FR-31: Board, Pieces, Rules, Quests, Clocks — in that order, all of them present.

    The form had one tab per rule that declared anything and no board, pieces, quests or
    clocks at all, so a variant's board size and time control were unreachable.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    assert [dialog.notebook.tab(tab, "text") for tab in dialog.notebook.tabs()] == list(SECTIONS)
    dialog.cancel()


def test_the_board_section_asks_for_the_dimensions_the_board_declares(tk_root, games_dir):
    """FR-1 and FR-32: the board is configured through its declaration like everything else.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    board, values = dialog.section_values("Board")[0]
    assert board is variant.board
    assert set(values) == {field.name for field in variant.board.value_fields()}
    assert values["rows"] == 8 and values["cols"] == 8
    dialog.cancel()


def test_the_board_section_resizes_the_board_it_configures(tk_root, games_dir):
    """A form that shows the rows and columns and does not apply them configures nothing.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()
    editors = dialog.entries_by_section["Board"][0][2]
    editors["rows"].set("10")
    editors["cols"].set("12")

    assert dialog.save() is True
    assert variant.board.dimensions == (10, 12)
    assert variant.board.get_piece_at((9, 11)) is None


def test_the_pieces_section_configures_each_piece_separately(tk_root, games_dir):
    """Six pieces each declare a `name`; one widget per name would configure one of them six times.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    entries = dialog.section_values("Pieces")
    assert [type(piece).__name__ for piece, _values in entries] == [
        piece.__name__ for piece in variant.pieces
    ]
    by_name = {type(piece).__name__: (piece, values) for piece, values in entries}
    assert by_name["Knight"][1]["white_symbol"] == "♘"
    assert by_name["Rook"][1]["white_symbol"] == "♖"
    assert by_name["Knight"][1]["vectors"] != by_name["Rook"][1]["vectors"]

    _knight, _knight_fields, editors = next(
        entry
        for entry in dialog.entries_by_section["Pieces"]
        if type(entry[0]).__name__ == "Knight"
    )
    editors["white_symbol"].set("X")
    assert dialog.save() is True
    assert by_name["Knight"][0]._symbol_for(1) == "X"
    assert by_name["Rook"][0]._symbol_for(1) == "♖"


def test_the_rules_section_asks_for_what_each_rule_declares_and_can_switch_it_off(
    tk_root, games_dir
):
    """FR-21: `enabled` is added by the framework, so the form's switch is part of the form.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    entries = {
        rule.label: (rule, fields) for rule, fields, _e in dialog.entries_by_section["Rules"]
    }
    check_rule, _fields, editors = next(
        entry
        for entry in dialog.entries_by_section["Rules"]
        if type(entry[0]).__name__ == "CheckRule"
    )
    assert "enabled" in editors
    editors["enabled"].set(False)
    assert dialog.save() is True
    assert check_rule.enabled is False
    assert check_rule not in variant.enabled_rules()
    assert entries  # every rule in the configuration is in the section


def test_the_quests_section_asks_for_each_quest_parameters(tk_root, games_dir):
    """FR-20: a quest's parameters are what the settings form asks the player for.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    entries = dialog.section_values("Quests")
    assert [quest.name for quest, _values in entries] == [quest.name for quest in variant.quests]
    hunting = next(values for quest, values in entries if quest.name == "Hunting a kind")
    assert hunting["piece_type"] == "queen"
    assert "count" in hunting and "reward" in hunting and "enabled" in hunting


def test_the_clocks_section_asks_for_a_clock_time_control(tk_root, games_dir):
    """FR-6: a clock declares an initial time and an increment, and the form asks for both.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    clock, values = dialog.section_values("Clocks")[0]
    assert values == {"initial_seconds": 600, "increment_seconds": 5}

    _clock, _fields, editors = dialog.entries_by_section["Clocks"][0]
    editors["initial_seconds"].set("30")
    assert dialog.save() is True
    assert clock.initial_seconds == 30
    assert clock.timer.initial_time == 30, "the countdown must start from the time the form saved"


def test_the_selector_offers_every_configuration_and_defaults_to_the_one_being_edited(
    tk_root, games_dir
):
    """FR-30: the selector says which configuration is being edited, so it lists them all.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    assert dialog.choice.get() == "house"
    assert set(dialog.selector.cget("values")) == {DEFAULT_GAME, "house"}
    assert dialog.configuration_names()[0] == DEFAULT_GAME
    dialog.cancel()


def test_choosing_another_configuration_edits_that_one(tk_root, games_dir):
    """The selector is only worth having if choosing one changes what the form is over.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    dialog.choice.set(DEFAULT_GAME)
    chosen = dialog._selected()

    assert chosen is not None
    assert chosen.name == DEFAULT_GAME
    assert dialog.configuration is chosen
    assert [dialog.notebook.tab(tab, "text") for tab in dialog.notebook.tabs()] == list(SECTIONS)
    dialog.cancel()


def test_the_plus_button_duplicates_the_configuration_being_edited(tk_root, games_dir):
    """FR-27: a variant starts by duplicating, so the button next to the selector does that.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    created = dialog.add_configuration()

    assert created is not None
    assert created.name == "house_copy"
    assert created.path != variant.path
    assert os.path.isdir(os.path.join(games_dir, "house_copy"))
    assert dialog.choice.get() == "house_copy"
    assert "house_copy" in dialog.selector.cget("values")
    dialog.cancel()


def test_the_plus_button_picks_a_name_nothing_is_using(tk_root, games_dir):
    """Duplicating twice must not fail on the second attempt because the name was taken.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    first = dialog.add_configuration()
    second = dialog.add_configuration()

    assert first is not None and second is not None
    assert (first.name, second.name) == ("house_copy", "house_copy_copy")
    dialog.cancel()


def test_deleting_a_variant_removes_it_and_falls_back_to_the_default(tk_root, games_dir):
    """FR-28: a configuration can be deleted, and the form must be left over something real.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    assert dialog.delete_configuration() == "house"

    assert not os.path.exists(os.path.join(games_dir, "house"))
    assert dialog.configuration.name == DEFAULT_GAME
    assert dialog.choice.get() == DEFAULT_GAME
    dialog.cancel()


def test_the_form_refuses_to_save_the_default_and_says_why(tk_root, games_dir):
    """The guard, reached the way a player reaches it: open settings, press Save.

    This is the whole point of the guard being in `save_values` as well as in the library
    functions: the form is the path a player takes, and a permission error they are told about
    is a lesson while a traceback is a bug.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    default = load_configuration(DEFAULT_GAME, root=games_dir)
    dialog = SettingsDialog(tk_root, default, root=games_dir)
    tk_root.update()

    assert dialog.save() is False

    assert "cannot be edited" in dialog.message.get()
    assert not os.path.exists(os.path.join(default.path, "configuration.json"))
    dialog.cancel()


def test_saving_a_variant_writes_its_values_to_disk(tk_root, games_dir):
    """A variant's settings survive, which is FR-29 and the point of writing them at all.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    import json

    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()
    check_entry = next(
        entry
        for entry in dialog.entries_by_section["Rules"]
        if type(entry[0]).__name__ == "CheckRule"
    )
    check_entry[2]["royal_kind"].set("monarch")

    assert dialog.save() is True

    with open(os.path.join(variant.path, "configuration.json"), encoding="utf-8") as handle:
        written = json.load(handle)
    assert written["rules"]["Check"]["royal_kind"] == "monarch"
    assert "state" not in json.dumps(written)


def test_reset_returns_a_field_to_its_declaration(tk_root, games_dir):
    """FR-35: settings can be reset to the shipped defaults.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()
    # A rule that declares `royal_kind`, chosen by what it declares rather than by its
    # position: the section composes its files in file-name order, so which rule the form
    # lists first is a property of the file names and not something this test is about.
    _subject, fields, editors = next(
        entry
        for entry in dialog.entries_by_section["Rules"]
        if any(field.name == "royal_kind" for field in entry[1])
    )
    royal = next(field for field in fields if field.name == "royal_kind")
    editors["royal_kind"].set("monarch")

    dialog.reset()

    assert editors["royal_kind"].get() == royal.default
    dialog.cancel()


def test_reset_returns_each_rule_to_its_own_declaration(tk_root, games_dir):
    """Several rules declare `royal_kind`; resetting one must not reset another's widget.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()
    declaring = [
        (fields, editors)
        for _rule, fields, editors in dialog.entries_by_section["Rules"]
        if any(field.name == "royal_kind" for field in fields)
    ]
    assert len(declaring) > 1, "chess declares royal_kind on more than one rule"
    for _fields, editors in declaring:
        editors["royal_kind"].set("monarch")

    dialog.reset()

    for fields, editors in declaring:
        royal = next(field for field in fields if field.name == "royal_kind")
        assert editors["royal_kind"].get() == royal.default
    dialog.cancel()


def test_the_rules_section_offers_the_editor_for_every_rule_it_shows(tk_root, games_dir):
    """FR-33: the Rules section offers a code editor, because a rule's logic is code.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()
    pages = {
        dialog.notebook.tab(tab, "text"): dialog.notebook.nametowidget(tab)
        for tab in dialog.notebook.tabs()
    }

    assert set(_button_labels(pages["Rules"])) >= {"Edit logic"}
    dialog.cancel()


def test_saving_a_rule_file_tells_the_player_it_is_in_force(tk_root, games_dir):
    """The gap in the flow: the editor's verdict is about the code, not about the game.

    A rule file used to be written, checked, reported sound — and joined nothing, because
    nothing composed it. So the form now loads the configuration again once a file in one of
    its sections has been written and says what is in force, which is the one thing a player
    cannot work out from the editor. The rules the section composed are on the tab it
    rebuilds, so the claim in the message is visible rather than merely asserted.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    path = dialog.create_source("no_pawn_moves", "rule")
    editor = dialog.editors_open[-1]
    editor.text.insert("1.0", GOOD_RULE)

    assert editor.save() == path
    tk_root.update()

    assert "no_pawn_moves.py is part of house" in dialog.message.get()
    assert f"{len(variant.rules) + 1} rules" in dialog.message.get()
    labels = [rule.label for rule in dialog.configuration.rules]
    assert "Stay on board" in labels
    dialog.cancel()


def test_a_rule_file_that_declares_nothing_is_named_in_the_form(tk_root, games_dir):
    """A file the player started and did not finish is not the same as a helper, and only the
    name says so — so the form says the name.

    `house/rules/attacks.py` is a helper three rule files share and declares no rule, and a
    half-written `zz_notes.py` looks exactly like it. The editor will not save such a file —
    its own check refuses one — so the only way to have one is to write it outside the product,
    which is why the report belongs on the load rather than on the save.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()
    target = os.path.join(variant.path, "rules", "zz_notes.py")
    pathlib.Path(target).write_text(
        '"""Not finished."""\n\n\ndef helper():\n    return 1\n', "utf-8"
    )

    copied = dialog.add_configuration()
    tk_root.update()

    assert copied.name == "house_copy"
    assert "Not in force:" in dialog.message.get()
    assert "rules/zz_notes.py declares no Rule" in dialog.message.get()
    assert "rules/attacks.py declares no Rule" in dialog.message.get()
    assert len(copied.rules) == len(variant.rules)
    dialog.cancel()


def test_the_quests_section_says_so_when_a_quest_is_declared_by_the_engine(tk_root, games_dir):
    """FR-33 asks for an editor in the Quests section, and chess's quests are the engine's.

    `FirstBlood` and its siblings live in `model/game/quests.py`, so offering to edit them
    would write to the engine from a variant's settings form. Saying so is the honest answer,
    and it is what the section does.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()
    pages = {
        dialog.notebook.tab(tab, "text"): dialog.notebook.nametowidget(tab)
        for tab in dialog.notebook.tabs()
    }
    labels = list(_labels(pages["Quests"]))

    assert "Declared by the engine; not editable here." in labels
    assert "Edit logic" not in set(_button_labels(pages["Quests"]))
    dialog.cancel()


def test_a_quest_declared_by_the_engine_is_not_offered_for_editing(tk_root, games_dir):
    """`FirstBlood` lives in `model/game/quests.py`; editing it would write to the engine.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    variant = copy_configuration(DEFAULT_GAME, "house", root=games_dir)
    dialog = SettingsDialog(tk_root, variant, root=games_dir)
    tk_root.update()

    editor_buttons = 0
    for _quest, _fields, editors in dialog.entries_by_section["Quests"]:
        del editors
    dialog.cancel()
    for quest in variant.quests:
        path = os.path.abspath(inspect.getfile(type(quest)))
        inside = os.path.commonpath([os.path.abspath(variant.path), path]) == os.path.abspath(
            variant.path
        )
        if inside:
            editor_buttons += 1
    assert (
        editor_buttons == 0
    ), "chess's quests are all declared by the engine, so none is editable in the variant"


def _labels(widget):
    """Yield the text of every label under a widget.

    Args:
        widget: The widget to walk.

    Yields:
        str: Each label's text.
    """
    for child in widget.winfo_children():
        if child.winfo_class() in ("TLabel", "Label"):
            yield str(child.cget("text"))
        yield from _labels(child)


def _button_labels(widget):
    """Yield the label of every button under a widget.

    Args:
        widget: The widget to walk.

    Yields:
        str: Each button's text.
    """
    for child in widget.winfo_children():
        if child.winfo_class() in ("TButton", "Button"):
            yield child.cget("text")
        yield from _button_labels(child)


def test_rebuilding_the_form_does_not_leave_the_old_pages_behind(tk_root, games_dir):
    """Choosing another configuration rebuilds the form, and `forget` is not enough.

    `notebook.forget` takes a page out of the notebook and leaves the widget alive as a child
    of it, with every entry, label and editor still bound. Switching configuration five times
    left thirty children on the notebook and twenty-five of them unreachable; a hundred-odd
    live widgets after a dozen switches, each holding a StringVar and an editor pointing at a
    file that may since have been renamed.

    Args:
        tk_root: The session's Tk root.
        games_dir: A throwaway `games/` root holding the default configuration.

    Returns:
        None
    """
    dialog = SettingsDialog(
        tk_root, load_configuration(DEFAULT_GAME, root=games_dir), root=games_dir
    )
    tk_root.update()
    sections = len(dialog.notebook.tabs())

    for _ in range(25):
        dialog._rebuild()
        tk_root.update()

    assert len(dialog.notebook.tabs()) == sections, "the form lost or gained a section"
    assert (
        len(dialog.notebook.winfo_children()) == sections
    ), f"{len(dialog.notebook.winfo_children())} pages are alive where {sections} should be"
