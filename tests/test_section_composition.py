"""A file in a configuration's section is in force because it is a file in that section.

The defect this file exists for: `view/settings_dialog.py` wrote a player's rule into
`rules/<name>.py`, the editor checked it, reported "No problems found", and the game played on
without it. `games/chess/rules/__init__.py` held a literal tuple of the thirteen rules chess
ships, and its own docstring said there was no registry and nothing was discovered by name —
which was true, and was the problem. The editor worked, the file was written, and the product
said nothing at all about a rule it had just accepted.

The same defect stood one section over and stood there silently: `pieces/`, `clocks/` and
`export/` were declared `None` — "composed by hand" — while `games/chess/pieces/__init__.py`
held a literal `PIECES` tuple and `build_exporters()` a literal list of five writers. So the
composition is now the directory for *every* section, and `model/game/configuration.py` declares
what a module in each one must derive from. The tests here hold that to what it costs and what
it protects:

- a written rule, piece, clock or writer is in force, in the copy it was written into and not
  in the original;
- the order is the section's files, deterministically, because rule order is the tie-break
  when two rules propose an outcome at once; and a section may declare which of its entries
  lead, which orders and never removes;
- `__init__.py` is a file in the section like any other, so an entry declared there is composed;
- a file that cannot be imported refuses the load and names itself, and a file that declares
  nothing is left out and named — the two are the only outcomes, and neither is silence.

The bound that makes this safe is the one in `games/chess/__init__.py`: a configuration is
loaded as a package rooted at its own directory, and a section is composed as the package it
is rather than as a name looked up somewhere. `tests/test_configuration_copying.py` holds the
copy's-own property for the board, the pieces, the clocks and the rules; the tests here hold it
for an entry the copy's own player wrote.
"""

import importlib.util
import os
import pathlib
import shutil
import sys

import pytest

from model.game.clock import Clock
from model.game.configuration import (
    CLASS_ENTRY_SECTIONS,
    CONFIGURATION_SECTIONS,
    ConfigurationSourceError,
    compose_section,
    load_configuration,
)
from model.game.games import games_root
from model.game.quest import Quest
from model.game.rule import Rule
from model.game.validator import MoveValidator
from model.misc.export_writers import ExportWriter
from model.pieces.piece import Piece

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


def _section_package(tmp_path, name, source='"""A section of nothing in particular."""\n'):
    """Build a throwaway package whose directory name is a declared section.

    Args:
        tmp_path: Pytest's temporary directory.
        name: The section directory name, which is what the declaration is keyed on.
        source: What the package's own `__init__.py` says.

    Returns:
        ModuleType: The imported package, so it can be handed to `compose_section`.
    """
    section = tmp_path / name
    section.mkdir(exist_ok=True)
    (section / "__init__.py").write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        f"throwaway_{name}", section / "__init__.py", submodule_search_locations=[str(section)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"throwaway_{name}"] = module
    spec.loader.exec_module(module)
    return module


#: A piece as a player writes one: one file in a configuration's `pieces/`, no registration.
WRITTEN_PIECE = '''
"""The camel: a leaper that jumps further than a knight, as a player wrote it."""

from typing import Any, List, Tuple

from model.pieces.piece import Piece

#: The eight offsets the camel moves by: one square further along each of the knight's.
VECTORS: List[Tuple[int, int]] = [
    (2, 3), (3, 2), (3, -2), (2, -3), (-2, -3), (-3, -2), (-3, 2), (-2, 3)
]


class Camel(Piece):
    """Leaps in a longer L than a knight does."""

    def __init__(self, color: Any, piece_type: str = "camel"):
        """Initialize a Camel.

        Args:
            color: 1 for White, -1 for Black.
            piece_type: The configured kind. Defaults to `camel`.
        """
        super().__init__(
            color=color,
            piece_type=piece_type,
            vectors=VECTORS,
            attack_vectors=VECTORS,
            can_jump=True,
            symbols=("\\u265f", "\\u265e"),
            fen="C",
            name="Camel",
        )
'''


#: A clock as a player writes one: one file in a configuration's `clocks/`, no registration.
WRITTEN_CLOCK = '''
"""A two-minute clock, as a player wrote it."""

from typing import Optional

from model.game.clock import Clock
from model.game.timer import Timer

INITIAL_SECONDS: int = 120
INCREMENT_SECONDS: int = 0


class Blitz(Clock):
    """Two minutes a side and no increment."""

    def __init__(
        self,
        initial_seconds: int = INITIAL_SECONDS,
        increment_seconds: int = INCREMENT_SECONDS,
        timer: Optional[Timer] = None,
    ):
        """Initialize a Blitz clock.

        Args:
            initial_seconds: Time each side starts with, in seconds.
            increment_seconds: Time added after each move. This clock adds none.
            timer: The timer holding the running times.
        """
        super().__init__(
            initial_seconds=initial_seconds,
            increment_seconds=increment_seconds,
            timer=timer,
        )
'''


#: A writer as a player writes one: one file in a configuration's `export/`, no registration.
WRITTEN_WRITER = '''
"""A ledger of the moves as coordinate pairs, as a player wrote it."""

from typing import Any, List, Tuple

from model.misc.export_writers import ExportWriter


class ExportLedger(ExportWriter):
    """Writes every move as its two squares, separated by a comma."""

    def formats(self) -> Tuple[str, ...]:
        """Return the notations this writer writes.

        Returns:
            Tuple[str, ...]: The one notation this writer writes.
        """
        return ("Ledger",)

    def export(self, format_type: str, **kwargs: Any) -> str:
        """Write the game's moves as coordinate pairs.

        Args:
            format_type: The notation asked for, in the caller's own spelling.
            **kwargs: Any: `moves`.

        Returns:
            str: The moves, one per line.

        Raises:
            UnsupportedExportFormat: If the notation asked for is not one this writer writes.
        """
        if not self._writes(format_type):
            raise ValueError(f"{format_type!r} is not a notation this writer writes")
        lines: List[str] = []
        for move in kwargs.get("moves", []) or []:
            lines.append(f"{move.start_pos}-{move.end_pos}")
        return "\\n".join(lines)
'''


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


# --- the same three sections over: a piece, a clock and a writer written into a copy


def test_a_piece_written_into_a_pieces_directory_is_in_the_catalogue_and_usable(tmp_path):
    """The defect one section over: a piece written into the copy is played by the copy.

    `Configuration.pieces` used to be a literal `PIECES` tuple in `games/chess/pieces/__init__.py`
    and then `[Man, King]` written out in the checkers configuration, so a piece file a player
    wrote joined nothing — no error, no warning, no piece. The proof is behavioural rather than a
    count: the camel is in the copy's catalogue, and the moves the copy's own rules allow it are
    the moves a camel moves, which nothing here had to be told about.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    before = len(variant.pieces)
    _write(variant.path, "pieces", "zz_camel.py", WRITTEN_PIECE)

    reloaded = load_configuration("house", root=games)
    written = next(cls for cls in reloaded.pieces if cls.__name__ == "Camel")

    assert len(reloaded.pieces) == before + 1
    assert written.__module__.endswith("house.pieces.zz_camel")
    assert not any(cls.__name__ == "Camel" for cls in load_configuration("chess").pieces)
    assert _legal_targets(reloaded, written(1), (4, 4)) == {
        (2, 7),
        (6, 7),
        (7, 6),
        (7, 2),
        (6, 1),
        (2, 1),
        (1, 2),
        (1, 6),
    }


def _legal_targets(configuration, piece, square):
    """Return the squares the configuration's own rules let a piece move to from a square.

    Args:
        configuration: The loaded configuration.
        piece: The piece to stand on the board.
        square: The square to stand it on.

    Returns:
        set: The destinations the rules in force allow, on an otherwise empty board.
    """
    board = configuration.new_board()
    for row in range(board.rows):
        for col in range(board.cols):
            board.set_piece_at((row, col), None)
    board.set_piece_at(square, piece)
    validator = MoveValidator(board, rules=configuration.rules)
    return set(validator.get_valid_moves(square, board))


def test_a_clock_written_into_a_clocks_directory_is_offered_by_the_copy(tmp_path):
    """A clock is composed out of `clocks/` now, against the parent the section declares.

    `clocks=[Fischer()]` was written out in both configurations, and a clock has no parent class
    to be composed against at all, so there was nothing for a file in `clocks/` to join. The
    clock a copy writes is offered beside the one it ships with, at the time control it declared.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    _write(variant.path, "clocks", "zz_blitz.py", WRITTEN_CLOCK)

    reloaded = load_configuration("house", root=games)
    written = next(clock for clock in reloaded.clocks if type(clock).__name__ == "Blitz")

    assert type(written).__module__.endswith("house.clocks.zz_blitz")
    assert all(type(clock).__module__.startswith("_configuration_") for clock in reloaded.clocks)
    assert written.get_time(1) == 120
    assert isinstance(written, Clock)
    assert not any(type(clock).__name__ == "Blitz" for clock in load_configuration("chess").clocks)


def test_a_writer_written_into_an_export_directory_is_offered_by_the_copy(tmp_path):
    """A notation is composed out of `export/` now, and every one is offered whatever the order.

    `build_exporters()` listed five writers by hand in both configurations, so a sixth file in
    `export/` would have joined nothing. It is offered here, it writes, and it leads with nothing:
    the preference in the section's own module orders the writers and removes none, so the
    transcript still leads and a chess game is still saved as a `.pgn`.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    _write(variant.path, "export", "zz_ledger.py", WRITTEN_WRITER)

    reloaded = load_configuration("house", root=games)
    written = next(w for w in reloaded.exporters if type(w).__name__ == "ExportLedger")

    assert type(written).__module__.endswith("house.export.zz_ledger")
    assert written.formats() == ("Ledger",)
    assert written.export("Ledger", moves=[]) == ""
    assert reloaded.exporters[-1] is written, "an unpreferred writer must follow, not vanish"
    assert [writer.formats()[0] for writer in reloaded.exporters][:5] == [
        "PGN",
        "Algebraic",
        "Field-Field-Extra",
        "FEN",
        "Stenographic",
    ]
    original = load_configuration("chess").exporters
    assert not any(type(writer).__name__ == "ExportLedger" for writer in original)


def test_the_declared_preference_is_an_order_and_never_a_roster():
    """The section's own module says which writers lead, and the directory says which exist.

    Two questions, deliberately separate. Which notations a game can write is what the directory
    holds, and only that; which of them is the default is a preference, because
    `GameManager.default_format` takes the first and `save_log` names the file from it. Reading
    the preference as a roster is what made the explicit lists necessary and what let a writer
    nobody listed silently not exist.

    Returns:
        None
    """
    configuration = load_configuration("chess")
    offered = [writer.formats()[0] for writer in configuration.exporters]

    assert offered == ["PGN", "Algebraic", "Field-Field-Extra", "FEN", "Stenographic"]
    assert configuration.metadata in configuration.exporters


class UnheldWriter(ExportWriter):
    """A writer that lives outside any configuration's `export/`.

    Declared here rather than in the throwaway section, because the point is a preference
    naming a class the section's own files do not declare — and a class declared in the
    section's own module is composed, as the rules section's own module test holds.
    """

    def formats(self):
        """Return the notations this writer writes.

        Returns:
            tuple: The one notation this writer writes.
        """
        return ("Unheld",)


def test_a_preference_for_a_writer_the_directory_does_not_hold_refuses_the_load(tmp_path):
    """The other direction is loud: a preference and a directory that disagree is a refusal.

    Without this, deleting a writer from `export/` and leaving its name in the preference would
    quietly leave the game without that notation and without saying so — which is the failure
    this change exists to end, arrived at from the other side.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    directory = tmp_path / "export"
    directory.mkdir()
    (directory / "held.py").write_text(
        '"""The writer this section holds."""\n\n'
        "from typing import Any, Tuple\n\n"
        "from model.misc.export_writers import ExportWriter\n\n\n"
        "class Held(ExportWriter):\n"
        '    """The one writer this section holds."""\n\n'
        "    def formats(self) -> Tuple[str, ...]:\n"
        '        """Return the notations this writer writes.\n\n'
        "        Returns:\n"
        "            Tuple[str, ...]: One notation.\n"
        '        """\n'
        '        return ("Held",)\n\n'
        "    def export(self, format_type: str, **kwargs: Any) -> str:\n"
        '        """Write nothing.\n\n'
        "        Args:\n"
        "            format_type: The notation asked for.\n"
        "            **kwargs: Anything else.\n\n"
        "        Returns:\n"
        "            str: An empty record.\n"
        '        """\n'
        '        return ""\n',
        encoding="utf-8",
    )
    module = _section_package(
        tmp_path,
        "export",
        '"""An export section that prefers a writer it does not hold."""\n\n'
        "from .held import Held\n\n"
        "PREFERRED = (Held,)\n",
    )
    held = importlib.import_module(".held", module.__name__).Held

    assert compose_section(module, preferred=(held,))[0].formats() == ("Held",)
    with pytest.raises(ConfigurationSourceError) as failure:
        compose_section(module, preferred=(held, UnheldWriter))

    assert "UnheldWriter" in str(failure.value)
    assert "export" in str(failure.value)


def test_every_sections_order_is_its_files_and_the_same_on_two_loads(tmp_path):
    """Deterministic order in the three sections that had none to be deterministic about.

    Rule order settles two equal outcomes, and writer order decides which notation is the
    default, so neither may depend on what the filesystem hands back. The order everywhere is
    the section's own module first and then the remaining files by name, and it is the same on
    two loads of the same directory.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    _write(variant.path, "pieces", "zz_camel.py", WRITTEN_PIECE)
    _write(variant.path, "clocks", "zz_blitz.py", WRITTEN_CLOCK)

    def composed(configuration):
        return (
            [cls.__module__.rsplit(".", 1)[-1] for cls in configuration.pieces],
            [type(clock).__module__.rsplit(".", 1)[-1] for clock in configuration.clocks],
        )

    first = composed(load_configuration("house", root=games))
    second = composed(load_configuration("house", root=games))

    assert first == second
    for names in first:
        assert names == sorted(names, key=lambda name: (name != "__init__", name))
    assert first[0][-1] == "zz_camel"
    assert first[1][-1] == "zz_blitz"


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


def test_every_declared_section_names_the_parent_class_it_composes():
    """The declaration is the whole of what composition means, so it is held to itself.

    Every section names a class, and `None` is gone: a section declared as composed by hand
    while a file a player writes into it joins nothing is exactly the defect this file exists
    for, one section over, and saying so in the declaration is what stopped nobody.

    Returns:
        None
    """
    assert CONFIGURATION_SECTIONS == {
        "pieces": Piece,
        "rules": Rule,
        "quests": Quest,
        "clocks": Clock,
        "export": ExportWriter,
    }
    assert all(base is not None for base in CONFIGURATION_SECTIONS.values())


def test_the_only_class_entry_section_is_pieces():
    """One section composes the class rather than an instance, and it says which.

    A piece is placed by a board with a colour and a square, and `Piece(color, piece_type)`
    cannot be built with no arguments at all — so a catalogue of instances would refuse every
    piece in the tree. Everything else in a section is one object the game holds for the whole
    of it, and those are instances.

    Returns:
        None
    """
    assert CLASS_ENTRY_SECTIONS == frozenset({"pieces"})
    assert CONFIGURATION_SECTIONS["pieces"].__name__ == "Piece"


def test_a_section_declared_with_no_parent_class_is_refused(tmp_path, monkeypatch):
    """`None` cannot come back quietly as a way of saying "composed by hand".

    Nothing declares a section `None` today, and this holds it that way: a section name mapped
    to no class refuses the composition by name rather than composing whatever its files happen
    to declare, which is what hand-composition always ended up meaning.

    Args:
        tmp_path: Pytest's temporary directory.
        monkeypatch: Pytest's patcher, used to map a declared section to no class.

    Returns:
        None
    """
    monkeypatch.setitem(CONFIGURATION_SECTIONS, "pieces", None)
    module = _section_package(tmp_path, "pieces")

    with pytest.raises(ConfigurationSourceError) as failure:
        compose_section(module)

    assert "pieces" in str(failure.value)
    assert "names one" in str(failure.value)


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


@pytest.mark.parametrize("section", ["pieces", "rules", "quests", "clocks", "export"])
def test_a_file_that_cannot_be_imported_refuses_the_load_in_every_section(tmp_path, section):
    """The policy is the same policy in all five sections, and the section says which.

    `rules/` proved it first; `pieces/`, `clocks/` and `export/` are composed now, so a file
    that raises on import in any of them must refuse the load with the file named rather than
    leave a configuration playing without it. The parent class is in the message too, because
    what a player needs is *why* their file joined nothing.

    Args:
        tmp_path: Pytest's temporary directory.
        section: The section to write the broken file into.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    written = _write(
        variant.path,
        section,
        "zz_broken.py",
        '"""Raises on import."""\n\nraise ValueError("boom")\n',
    )

    with pytest.raises(ConfigurationSourceError) as failure:
        load_configuration("house", root=games)

    message = str(failure.value)
    assert os.path.basename(written) in message
    assert "boom" in message and "ValueError" in message


def test_a_file_that_declares_nothing_is_named_in_every_section(tmp_path):
    """`Configuration.uncomposed` names a file that joined nothing wherever it was written.

    A section legitimately holds helpers beside its entries, so a file that declares none is
    left out rather than refused. That is only safe if it is never silent: a piece a player
    started and did not finish looks exactly like a helper, and only the name tells them apart.
    All five sections are written into here at once, because `uncomposed` is one list every
    composition is handed and a section that forgot to be handed it would drop its report.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    variant = load_configuration("house", root=games)
    for section in ("pieces", "rules", "quests", "clocks", "export"):
        _write(
            variant.path,
            section,
            "zz_notes.py",
            '"""Something a player started and did not finish."""\n\n\ndef helper():\n    return 1\n',
        )

    reloaded = load_configuration("house", root=games)
    reported = [note for note in reloaded.uncomposed if "zz_notes.py" in note]

    assert len(reported) == 5, f"a section dropped its report: {reloaded.uncomposed}"
    for section in ("pieces", "rules", "quests", "clocks", "export"):
        assert any(os.path.join(section, "zz_notes.py") in note for note in reported), section
    assert any("declares no Piece" in note for note in reported)
    assert any("declares no Rule" in note for note in reported)
    assert any("declares no Quest" in note for note in reported)
    assert any("declares no Clock" in note for note in reported)
    assert any("declares no ExportWriter" in note for note in reported)
    assert len(reloaded.rules) == 13, "a file declaring nothing took the game down"
    assert len(reloaded.pieces) == 6
    assert len(reloaded.clocks) == 1


def test_a_piece_section_composes_classes_and_the_rest_compose_instances(tmp_path):
    """One section composes the class, and the difference is declared rather than inferred.

    `Configuration.pieces` is a catalogue of what a board may hold, so a piece entry is the
    class: the board builds one with a colour and a square when it places it, and
    `Piece(color, piece_type)` cannot be built with no arguments at all. Everything else in a
    section is one object the game holds for the whole of it, so those entries are instances —
    and the difference is in `CLASS_ENTRY_SECTIONS` where a reader can see it rather than in a
    branch that guesses from a constructor's signature.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    configuration = load_configuration("house", root=games)

    assert all(isinstance(cls, type) for cls in configuration.pieces)
    assert all(not isinstance(cls, (str, int, float)) for cls in configuration.clocks)
    assert all(
        type(clock).__module__.endswith("clocks.fischer") for clock in configuration.clocks
    ), "a clock is composed as an instance, not as the class"


def test_the_header_record_is_the_one_the_writers_offer(tmp_path):
    """`metadata` is read back out of the composed writers rather than built a second time.

    `build_exporters()` used to take the record as an argument and put the caller's object in
    the list, which is how the two stayed the same. Composition hands over no argument, so the
    record the manager gets is found *among* the composed writers and declared on — one object
    in both places, which is the property `tests/test_notation_and_writers.py` asserts and the
    reason a header written by the PGN writer is the header the configuration offered.

    Args:
        tmp_path: Pytest's temporary directory.

    Returns:
        None
    """
    games = _variant(tmp_path)
    configuration = load_configuration("house", root=games)

    assert configuration.metadata is not None
    assert configuration.metadata in configuration.exporters
    assert configuration.metadata.get_header("Event") == "chess"
    assert type(configuration.metadata).__module__.startswith("_configuration_")


def test_a_configuration_whose_writers_hold_no_header_declares_no_metadata():
    """The other end of the same question, and a configuration that is allowed to take it.

    A game can be written without a header at all, and `Configuration.metadata` is optional for
    exactly that reason. Composing the writers does not change it: the record is looked for, and
    a section holding no header writer yields `None` rather than a fresh record the
    configuration would then hand to writers that were offered none. Chess cannot reach that
    state — `pgn.py` composes the header writer — so this asks the composition question directly
    rather than contriving a configuration that cannot be written.

    Returns:
        None
    """
    from games.chess import build_metadata

    assert build_metadata([]) is None
    assert build_metadata([UnheldWriter()]) is None


def test_a_clock_is_a_Clock_and_both_shipped_clocks_are_one():
    """The base class `clocks/` composes against is built, not looked for.

    §13 registered a configurable parent `Clock` as the intention and §20 recorded that it was
    unbuilt, so `CONFIGURATION_SECTIONS` had nothing to name for `clocks/` and the section could
    not be composed at all. It exists now, and both shipped clocks derive from it — which is what
    makes "what belongs in `clocks/`" the same question a reader answers from `rules/`: does this
    file declare something of the kind the section composes.

    Returns:
        None
    """
    from games.checkers.clocks.fischer import Fischer as DraughtsFischer
    from games.chess.clocks.fischer import Fischer as ChessFischer

    assert issubclass(ChessFischer, Clock)
    assert issubclass(DraughtsFischer, Clock)
    assert ChessFischer().initial_seconds == 600
    assert ChessFischer().increment_seconds == 5
    assert DraughtsFischer().initial_seconds == 720
    assert DraughtsFischer().increment_seconds == 3
    for name in ("chess", "checkers"):
        loaded = load_configuration(name)
        assert all(isinstance(clock, Clock) for clock in loaded.clocks), name
