"""A file in a configuration's section is in force because it is a file in that section.

The defect this file exists for: `view/settings_dialog.py` wrote a player's rule into
`rules/<name>.py`, the editor checked it, reported "No problems found", and the game played on
without it. `games/chess/rules/__init__.py` held a literal tuple of the thirteen rules chess
ships, and its own docstring said there was no registry and nothing was discovered by name —
which was true, and was the problem. The editor worked, the file was written, and the product
said nothing at all about a rule it had just accepted.

So the composition is now the directory. `model/game/configuration.py` declares which sections
a configuration has and composes each one out of the files it holds, and the tests here hold
that to what it costs and what it protects:

- a written rule is in force, in the copy it was written into and not in the original;
- the order is the section's files, deterministically, because rule order is the tie-break
  when two rules propose an outcome at once;
- `__init__.py` is a file in the section like any other, so a rule declared there is composed;
- a file that cannot be imported refuses the load and names itself, and a file that declares
  nothing is left out and named — the two are the only outcomes, and neither is silence.

The bound that makes this safe is the one in `games/chess/__init__.py`: a configuration is
loaded as a package rooted at its own directory, and a section is composed as the package it
is rather than as a name looked up somewhere. `tests/test_configuration_copying.py` holds the
copy's-own property for the board, the pieces and the rules; the third test here holds it for
a rule the copy's own player wrote.
"""

import importlib.util
import os
import pathlib
import shutil
import sys

import pytest

from model.game.configuration import (
    CONFIGURATION_SECTIONS,
    ConfigurationSourceError,
    compose_section,
    load_configuration,
)
from model.game.games import games_root
from model.game.quest import Quest
from model.game.rule import Rule
from model.game.validator import MoveValidator

#: A rule as a player writes one: one file in a configuration's `rules/`, no registration.
WRITTEN_RULE = '''
"""No pawn moves, as a player wrote it."""

from typing import Any

from model.game.rule import Rule


class NoPawnMovesRule(Rule):
    """Forbid every move a pawn could make."""

    default_name = "No pawn moves"

    def permits_move(self, position: Any, move: Any) -> bool:
        """Refuse a move a pawn is making.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            bool: False for a pawn's move, True for anything else.
        """
        piece = position.get_piece_at(move.start_pos)
        return not (piece is not None and piece.getType() == "pawn")
'''


def _variant(tmp_path, name="house"):
    """Copy the shipped chess configuration into a throwaway `games/` root.

    Args:
        tmp_path: Pytest's temporary directory.
        name: The directory name the copy gets.

    Returns:
        str: The path of the `games/` root holding the copy.
    """
    games = tmp_path / "games"
    if not (games / name).exists():
        shutil.copytree(
            pathlib.Path(games_root()) / "chess",
            games / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    return str(games)


def _write(variant_path, section, filename, source):
    """Write a file into a section of a copied configuration.

    Args:
        variant_path: The copied configuration's directory.
        section: The section directory name, for instance `rules`.
        filename: The file's name.
        source: What to write into it.

    Returns:
        str: The path written.
    """
    path = pathlib.Path(variant_path) / section / filename
    path.write_text(source, encoding="utf-8")
    return str(path)


# --- the defect: a written rule joins the configuration it was written into


def test_a_rule_written_into_a_rules_directory_is_in_force(tmp_path):
    """The defect itself: the file the product writes is a rule the product plays by.

    Nothing else in the suite can catch this. The editor's own check passes — that is what
    "No problems found" means — and the file is written; what was missing was anything that
    composed it. So the proof is behavioural and not a count: a rule that forbids every pawn
    move must remove pawn moves from the legal moves of the copy that holds it.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    before = len(variant.rules)
    legal_before = len(_legal_pawn_targets(variant))

    _write(variant.path, "rules", "zz_no_pawn_moves.py", WRITTEN_RULE)
    reloaded = load_configuration("house", root=games)

    assert [type(rule).__name__ for rule in reloaded.rules][-1] == "NoPawnMovesRule"
    assert len(reloaded.rules) == before + 1
    assert _legal_pawn_targets(reloaded) == []
    assert legal_before > 0, "chess has no pawn moves to forbid, so this proves nothing"


def _legal_pawn_targets(configuration):
    """Return the squares a white pawn on its own square is allowed to move to.

    Args:
        configuration: The loaded configuration.

    Returns:
        list: The destinations the rules in force allow, which is empty once a rule forbids
        pawn moves and is a pair of squares while they do not.
    """
    validator = MoveValidator(configuration.board, rules=configuration.rules)
    return validator.get_valid_moves((1, 0), configuration.board)


def test_a_written_rule_is_the_copys_own_and_not_the_originals(tmp_path):
    """The copy plays the copy's written rule, which is the failure this whole design guards.

    `games/chess/__init__.py` exists to keep a copy loading its own files, and
    `tests/test_configuration_copying.py` holds it for what ships. A rule written by hand is
    the case where it is easiest to get wrong: composing by module *name* rather than by the
    section package would resolve the copy's `rules/` to `games.chess.rules` and hand back the
    original's thirteen rules plus nothing, while looking as though it had loaded the copy.

    The module a class came from is the proof, as it is for the board's pieces.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    _write(variant.path, "rules", "zz_no_pawn_moves.py", WRITTEN_RULE)

    copy_rules = load_configuration("house", root=games).rules
    original_rules = load_configuration("chess").rules

    written = next(rule for rule in copy_rules if type(rule).__name__ == "NoPawnMovesRule")
    module = type(written).__module__

    assert module.startswith("_configuration_")
    assert module.endswith("house.rules.zz_no_pawn_moves")
    assert not any(type(rule).__name__ == "NoPawnMovesRule" for rule in original_rules)
    for rule in copy_rules:
        assert type(rule).__module__.startswith("_configuration_"), type(rule).__name__


def test_a_quest_written_into_a_quests_directory_is_in_force(tmp_path):
    """Quests join the same way rules do, and a configuration's own `quests/` is the place.

    `games/chess/quests/` shipped empty, so there was nothing here to be in force; the section
    is composed now, so a quest written into it is one of the configuration's quests and the
    settings form lists it beside the six the engine roster is instantiated into.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    _write(
        variant.path,
        "quests",
        "zz_capture_everything.py",
        '''
"""A quest as a player wrote it."""

from typing import Any, Optional

from model.game.quest import Quest


class CaptureEverythingQuest(Quest):
    """Count every capture, and never be satisfied."""

    default_name = "Capture everything"

    def validate(self, position: Any, move: Any) -> bool:
        """Judge nothing; the quest is a counter the player watches fail.

        Args:
            position: The board before the move.
            move: The move being considered.

        Returns:
            bool: True, so this quest never stands in the way of one.
        """
        return True

    def progress(self) -> Optional[str]:
        """Report no progress, which is what makes it unsatisfiable.

        Returns:
            Optional[str]: Always None.
        """
        return None
''',
    )

    reloaded = load_configuration("house", root=games)

    assert "Capture everything" in [quest.name for quest in reloaded.quests]
    assert isinstance(reloaded.quests[-1], Quest)
    assert type(reloaded.quests[-1]).__module__.endswith("house.quests.zz_capture_everything")
    assert "Capture everything" not in [quest.name for quest in load_configuration("chess").quests]


# --- the order, which is a tie-break and therefore not a detail


def test_the_order_is_the_sections_files_and_it_is_the_same_every_time(tmp_path):
    """Rule order settles two equal outcomes, so it may not depend on a directory listing.

    `resolve_outcomes` takes the first of two equally strong proposals, and `Configuration`
    hands the rules on in the order it composed them. A listing from the filesystem is in
    whatever order the filesystem hands back, so a rule written into a copy could have gone in
    front of the rules that shipped or behind them depending on the disk.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    _write(variant.path, "rules", "zz_no_pawn_moves.py", WRITTEN_RULE)

    first = [type(rule).__module__ for rule in load_configuration("house", root=games).rules]
    second = [type(rule).__module__ for rule in load_configuration("house", root=games).rules]

    assert first == second
    assert [name.rsplit(".", 1)[-1] for name in first] == sorted(
        (name.rsplit(".", 1)[-1] for name in first),
        # `__init__.py` is composed first whatever it is called, and the rest sort by name.
        key=lambda name: (name != "__init__", name),
    )
    assert [name.rsplit(".", 1)[-1] for name in first][-1] == "zz_no_pawn_moves"


def test_a_rule_declared_in_the_sections_own_module_is_composed(tmp_path):
    """`__init__.py` is a real file in the section, not a special case that declares nothing.

    It is the file that composes the section, so a player putting a rule in it is being
    reasonable — and a composer that listed the files and imported each one under a name of
    its own would either load the package twice or skip its declarations altogether.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    package = pathlib.Path(variant.path) / "rules" / "__init__.py"
    package.write_text(
        package.read_text(encoding="utf-8")
        + "\n\n"
        + WRITTEN_RULE.split('"""No pawn moves, as a player wrote it."""', 1)[1],
        encoding="utf-8",
    )

    reloaded = load_configuration("house", root=games)

    assert type(reloaded.rules[0]).__name__ == "NoPawnMovesRule"
    assert type(reloaded.rules[0]).__module__.endswith("house.rules")
    assert len(reloaded.rules) == 14


def test_the_declared_sections_say_what_each_one_composes():
    """The declaration is the whole of what composition means, so it is held to itself.

    A section whose parent class is declared is composed out of its own files; a section with
    no parent class is composed by hand, because what belongs in it is a choice rather than an
    entry per file. `pieces/`, `clocks/` and `export/` are the second kind today, and saying so
    here is what stops them looking like an oversight.

    Returns:
        None
    """
    assert CONFIGURATION_SECTIONS["rules"] is Rule
    assert CONFIGURATION_SECTIONS["quests"] is Quest
    assert CONFIGURATION_SECTIONS["pieces"] is None
    assert CONFIGURATION_SECTIONS["clocks"] is None
    assert CONFIGURATION_SECTIONS["export"] is None


def test_composing_something_that_is_not_a_section_is_refused(tmp_path):
    """Nothing is composed by accident: the section name is checked against the declaration.

    A package called `widgets` is a perfectly good Python package and not a section of any
    configuration, so asking the composer to compose it is a mistake in the caller and is said
    to be one rather than returning nothing.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    section = tmp_path / "widgets"
    section.mkdir()
    (section / "__init__.py").write_text('"""Not a section."""\n', encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "not_a_section", section / "__init__.py", submodule_search_locations=[str(section)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["not_a_section"] = module
    spec.loader.exec_module(module)

    with pytest.raises(ConfigurationSourceError, match="not one of the declared sections"):
        compose_section(module)


# --- the two outcomes for a file that cannot be composed, neither of them silence


def test_a_file_that_cannot_be_imported_refuses_the_load_and_names_itself(tmp_path):
    """The policy: refuse, with the file in the message.

    The alternative is the defect this replaced with a warning attached: a game that plays
    without a file the player put there. The editor catches a broken file at save time, so this
    is the path for a file edited outside the product — where refusing, naming the file and
    saying what it raised is the only thing a player can act on.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    written = _write(
        variant.path,
        "rules",
        "zz_broken.py",
        '"""Raises on import."""\n\nraise ValueError("boom")\n',
    )

    with pytest.raises(ConfigurationSourceError) as failure:
        load_configuration("house", root=games)

    message = str(failure.value)
    assert os.path.basename(written) in message
    assert "boom" in message
    assert "ValueError" in message


def test_a_file_that_declares_nothing_is_left_out_and_is_named(tmp_path):
    """The other half of the policy: ignored, but named.

    A section legitimately holds modules that declare no entry — `games/chess/rules/attacks.py`
    is the ray and attack geometry three rule files share, and refusing the load over it would
    stop the game starting for a file that is doing its job. So it is left out. What it must
    not be is invisible: a file the player wrote and did not finish looks exactly like a
    helper, and only the name tells them apart. `Configuration.uncomposed` is that name, and
    the settings form puts it in its message.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    before = len(load_configuration("house", root=games).rules)
    _write(
        variant.path,
        "rules",
        "zz_notes.py",
        '"""Something a player started and did not finish."""\n\n\ndef helper():\n    return 1\n',
    )

    reloaded = load_configuration("house", root=games)
    reported = [note for note in reloaded.uncomposed if "zz_notes.py" in note]

    assert len(reloaded.rules) == before, "a file declaring nothing took the game down"
    assert len(reported) == 1
    assert "declares no Rule" in reported[0]
    assert os.path.join("rules", "zz_notes.py") in reported[0]


def test_a_class_that_cannot_be_built_refuses_the_load_and_names_the_file(tmp_path):
    """A section composes an entry by building it with no arguments, and says so when it cannot.

    A class needing an argument cannot be composed that way — the section has only the class to
    go on — so the load is refused with the file, the class and the exception rather than
    failing at game start where the player cannot act on it.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    _write(
        variant.path,
        "rules",
        "zz_needs_an_argument.py",
        '"""A rule that insists on being told something."""\n\n'
        "from model.game.rule import Rule\n\n\n"
        "class NeedsAnArgumentRule(Rule):\n"
        '    """Require a piece kind that no section can supply."""\n\n'
        "    def __init__(self, royal_kind, **values):\n"
        "        super().__init__(**values)\n"
        "        self.value['royal_kind'] = royal_kind\n",
    )

    with pytest.raises(ConfigurationSourceError) as failure:
        load_configuration("house", root=games)

    message = str(failure.value)
    assert "zz_needs_an_argument.py" in message
    assert "NeedsAnArgumentRule" in message
    assert "royal_kind" in message
