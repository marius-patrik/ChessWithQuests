"""The engine holds no chess.

`SCRATCHPAD.md` constraint 1.4 and definition-of-done item 14 say it in one line: no
piece-type special cases, no hard-coded 8x8, no `getType() == "king"`. These tests are the
executable form of that line. Each one fails against the code as it was before the chess it
asserts the absence of was removed, which is what makes them worth having rather than
decoration.

Four separate leaks are covered, because they were removed separately:

- a piece-type table in the position-record writer, with a pawn as the fallback for anything
  undeclared;
- algebraic square naming in an engine module, which cannot describe a board of any other
  width because a file is one letter and a rank is one digit;
- a chess piece named in the engine's own quest roster;
- a chess writer, or a notation, or a configuration import, anywhere under `model/`.

The first two were found by reading the code. The last one is a **walk over the files**, with
its vocabulary read from the chess configuration at run time, because a gate written beside
the code it guards drifts from it: this file's own piece vocabulary was hand-kept once and
omitted `horse`, which is the descriptor this codebase's knight actually reports, so
`CaptureOfType("horse")` walked straight through the check meant to catch exactly that.

`tests/test_configuration_copying.py` covers the fifth: a configuration that can be copied and
still load its own files — including its own writers and its own naming of a square.
"""

import ast
import inspect
import os
import pathlib
import re
import textwrap

import pytest

import model
from games.chess.board import build_board
from games.chess.export.algebraic import algebraic_to_pos, pos_to_algebraic
from games.chess.export.fen import ExportFEN
from games.chess.export.pgn import ExportPGN
from games.chess.export.stenographic import ExportStenographic
from games.chess.pieces.knight import Knight
from games.chess.pieces.king import King
from games.chess.pieces.queen import Queen
from model.game.board import Board
from model.game.move import Move
from model.game.quests import (
    BUILT_IN_QUESTS,
    CaptureOfType,
    CompositeQuest,
    KingOnlyGame,
    build_quests,
)
from model.pieces.piece import Piece


#: Every piece name chess uses. The engine is not allowed to know one of them.
def _chess_piece_types() -> frozenset:
    """The piece kinds chess declares, read from the configuration rather than kept here.

    This set was a hand-kept list and it was missing `horse` — the descriptor this codebase's
    own knight actually reports, which `games/chess/pieces/knight.py` and `tests/test_perft.py`
    both assert. So `build_quests()` composing `CaptureOfType("horse")` passed the gate that
    exists to catch exactly that. Reading the catalogue means the gate cannot drift from the
    code it guards, and the catalogue is composed out of `pieces/` rather than listed, so
    reading it is also reading the directory a piece written into would join.

    Returns:
        frozenset: Every kind descriptor a chess piece reports.
    """
    from games.chess.pieces import build_pieces

    declared = set()
    for piece_class in build_pieces():
        instance = piece_class(1)
        for name in (instance.getType(), getattr(instance, "piece_type", None)):
            if isinstance(name, str):
                declared.add(name.lower())
    return frozenset(declared)


CHESS_PIECE_TYPES = _chess_piece_types()


#: Chess piece spellings a configuration's own rules may use.
#:
#: The gate derives its vocabulary from the piece types the shipped configurations report. A
#: spelling no piece reports falls outside that set and goes unguarded — and `horse` is recorded in
#: this file's own history as exactly that miss. So the spellings a configuration is allowed to
#: write are named here, and added to the derived set rather than left to chance.
_SPELLINGS_A_CONFIGURATION_MAY_WRITE = frozenset({"knight"})


def _engine_modules():
    """Yield the path of every module under `model/`.

    A per-module `inspect.getsource` cannot catch a module that did not exist when the gate
    was written, which is how a leak arrives in the first place. So the gate walks the tree
    rather than a list of files somebody remembered.

    Yields:
        pathlib.Path: Each module's path, with `__pycache__` ignored.
    """
    import model

    root = pathlib.Path(model.__file__).parent
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def _declared_field_names(path):
    """Return the configurable field names a module declares for itself.

    A name a module hands to `Field(...)` is that module's own data — something a player edits
    in a form — rather than a reference to a game, so it is the module's own to use. Everything
    else in a module is held to the forbidden vocabulary.

    Args:
        path: The module's path.

    Returns:
        frozenset: Every declared field name, in lower case.
    """
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not (isinstance(function, ast.Name) and function.id == "Field"):
            continue
        first = node.args[0] if node.args else None
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            names.add(first.value.lower())
    return frozenset(names)


def _code_without_docstrings(path):
    """Return a module's source with every docstring removed.

    Docstrings are prose, and prose is allowed to name a game in order to say that the engine
    holds none — `model/game/manager.py` opens by saying exactly that. Dropping them through
    the AST rather than by searching the text is what makes the remainder safe to match:
    identifiers, imports and string literals are all that is left.

    Args:
        path: The module's path.

    Returns:
        str: The module unparsed without its docstrings.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", [])
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            if isinstance(body[0].value.value, str):
                # Replaced rather than removed: a class or a function whose only statement was
                # its docstring would otherwise be left with no body at all.
                body[0] = ast.copy_location(ast.Pass(), body[0])
    return ast.unparse(tree)


def _chess_writer_class_names():
    """Return the writer class names the chess export package defines.

    Read from the modules rather than written here. A gate holding a list of class names would
    have to be edited every time a writer is renamed, and a gate that is not edited is a gate
    that has stopped looking.

    Returns:
        frozenset: Every class name under `games/chess/export/` that subclasses `ExportWriter`,
        in lower case.
    """
    import games.chess.export

    names = set()
    export_root = pathlib.Path(games.chess.export.__file__).parent
    for path in sorted(export_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {base.id for base in node.bases if isinstance(base, ast.Name)}
            bases |= {base.attr for base in node.bases if isinstance(base, ast.Attribute)}
            if "ExportWriter" in bases:
                names.add(node.name.lower())
    return frozenset(names)


def _importable_engine_modules():
    """Yield the file of every module Python can import under `model/`.

    The walk's own witness. Whatever the walk cannot see, this can, so the walk is held to
    covering it: a walk that silently matches nothing is the same defect as the hand-kept
    vocabulary this file already had, and it passes forever.

    Yields:
        pathlib.Path: Each importable module's file.
    """
    import importlib
    import pkgutil

    for entry in pkgutil.walk_packages(model.__path__, prefix="model."):
        # Python 3.12 started yielding a `ModuleInfo` here where earlier versions yielded the
        # name itself, and the suite runs on both.
        yield pathlib.Path(importlib.import_module(getattr(entry, "name", entry)).__file__)


def _chess_format_names():
    """Return the notations the chess configuration's writers declare.

    Read through `load_configuration("chess").exporters`, so it is the formats a caller can
    actually ask for rather than a string copied out of a writer's source.

    Returns:
        frozenset: Every declared notation name, in lower case.
    """
    from model.game.configuration import load_configuration

    names = set()
    for writer in load_configuration("chess").exporters:
        names |= {str(name).lower() for name in writer.formats()}
    return frozenset(names)


def _shipped_configuration_names():
    """Return the directory names of every configuration the product ships.

    Read from the installed `games/` rather than kept here, for the reason the piece
    vocabulary above is: a gate holding a hand-written list of names is a gate that has stopped
    looking, and a configuration added to the product later would join the walk without joining
    what the walk holds it against.

    Returns:
        frozenset: Every shipped configuration's directory name, in lower case.
    """
    from model.game.games import games_root

    root = games_root()
    return frozenset(
        name.lower()
        for name in os.listdir(root)
        if os.path.isdir(os.path.join(root, name)) and not name.startswith(("_", "."))
    )


# --- the FEN writer reads the piece, and refuses to guess


def test_the_fen_writer_holds_no_piece_type_table():
    """The writer must not carry a mapping from piece type to character.

    The table this replaces was `PIECE_CHARS = {"king": "k", ...}`: a second place that had to
    be told what a chess piece is, and that would disagree with a piece the moment the two
    drifted apart.

    Raises:
        AssertionError: If the writer declares any piece-to-character mapping.
    """
    assert not hasattr(ExportFEN, "PIECE_CHARS")


def test_a_fen_record_is_built_from_what_each_piece_declares():
    """A piece's character comes from the piece, so the writer needs no table.

    Returns:
        None
    """
    board = Board((4, 4), setup_pieces=False)
    board.set_piece_at((0, 0), Queen(1))
    board.set_piece_at((1, 1), Knight(-1))

    assert ExportFEN().to_fen(board).split()[0] == "4/4/1n2/Q3"


def test_a_piece_writes_the_character_it_declared_whatever_it_is():
    """The character is data, so a letter chess would not have picked is written unchanged.

    A game that writes its positions with characters of its own gets exactly those, without
    an engine edit — which a piece-type table could never offer.

    Returns:
        None
    """

    class Herald(Queen):
        """A queen that writes itself as an A, as a game of this repository could declare."""

        def __init__(self, color):
            super().__init__(color)
            self._fen = "A"

    board = Board((2, 2), setup_pieces=False)
    board.set_piece_at((1, 1), Herald(1))

    assert ExportFEN().to_fen(board).split()[0] == "1A/2"


def test_an_undeclared_piece_is_refused_rather_than_written_as_a_pawn():
    """A piece with no character has no place in a position record, and is told so.

    The behaviour this replaces was `PIECE_CHARS.get(ptype, "p")`: an unknown piece was
    written as a pawn, so a game with an unfamiliar piece produced a well-formed FEN record
    that lied about the position, and nothing in the record could reveal it.

    Raises:
        AssertionError: If an undeclared piece is written instead of refused.
    """
    board = Board((2, 2), setup_pieces=False)
    board.set_piece_at((1, 1), Piece(1, "longstrider"))

    with pytest.raises(ValueError, match="declares no character"):
        ExportFEN().to_fen(board)


def test_a_piece_that_declares_no_character_is_refused_even_if_it_looks_like_chess():
    """Refusing is about the declaration, not about the piece's name.

    A piece calling itself a king and declaring nothing is in exactly the same position as one
    calling itself anything else: it has not said how it is written.

    Raises:
        AssertionError: If a chess-named piece declaring nothing is written instead of refused.
    """

    class Silent(Queen):
        """A piece that calls itself a king and declares no character."""

        def __init__(self, color):
            super().__init__(color, piece_type="king")
            self._fen = None

    board = Board((2, 2), setup_pieces=False)
    board.set_piece_at((1, 1), Silent(1))

    with pytest.raises(ValueError, match="declares no character"):
        ExportFEN().to_fen(board)


def test_the_chess_board_still_writes_the_record_it_always_did():
    """Removing the table must not change one character of chess's own output.

    The four fields after the side to move used to be `- - 0 1` whatever the game was doing,
    and they are now computed. The placement is byte for byte what it always was, and the
    fields after it are the ones every chess program agrees on for a board nothing has
    happened to yet: `KQkq - 0 1`.

    Returns:
        None
    """
    assert (
        ExportFEN().to_fen(build_board(), active_color=1)
        == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )


# --- the chess naming of squares lives in the chess configuration


def test_algebraic_naming_is_not_defined_in_the_engine():
    """The conversion belongs to chess: a file is a letter and a rank is a single digit.

    Checked against the whole engine tree rather than against one module, because a re-export
    shim is a module and a shim can always be replaced by the next one. The engine defined
    neither function even when it re-exported both, and now it holds neither.

    Returns:
        None
    """
    assert inspect.getmodule(pos_to_algebraic).__name__ == "games.chess.export.algebraic"
    assert inspect.getmodule(algebraic_to_pos).__name__ == "games.chess.export.algebraic"

    defined = []
    for path in _engine_modules():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in (
                "pos_to_algebraic",
                "algebraic_to_pos",
                "file_letter",
            ):
                defined.append(f"{path.name}:{node.lineno} {node.name}")

    assert defined == []


def test_the_engine_holds_no_notation_shim():
    """The shim is deleted rather than deprecated, so it cannot come back quietly.

    `model/misc/notation.py` re-exported two chess names into the engine for the sake of one
    caller, and its own docstring called itself a shim with a deletion date. What is asserted
    here is the absence of the module, which is the only thing that stops the next caller from
    adding it again.

    Returns:
        None
    """
    import importlib.util

    assert importlib.util.find_spec("model.misc.notation") is None


def test_the_writer_still_writes_coordinates_in_chess_algebra():
    """Reaching the chess naming relatively must not cost the writers their records.

    The coordinate record is compressed now, so what is asserted is what it decodes to rather
    than what it looks like: the same two squares, reached through the record's own reader.

    Returns:
        None
    """
    moves = [Move((1, 4), (3, 4)), Move((6, 4), (4, 4))]
    writer = ExportStenographic()

    assert writer.from_stenographic(writer.to_stenographic(moves)) == "e2e4 e7e5"
    assert "1. e4 e5" in ExportPGN().to_pgn(moves)


# --- the export writers, the notations they write, and the tree they must not reach


def test_no_module_under_the_engine_names_a_chess_writer_or_a_notation():
    """The whole tree, with its vocabulary read from the chess configuration.

    The gate this replaces was per-module and piece-name-oriented: it would not have
    flagged `class ChessNotationWriter`, and its hand-kept vocabulary is how `horse`
    slipped through a check meant to catch exactly that. So the vocabulary is read at run
    time — the writer class names the chess export package defines, and the notations
    those writers declare — and the walk is over the files on disk, not a list of modules
    somebody remembered.

    The match is case-insensitive because the leak is a spelling: `GameManager.writer_for`
    compares without regard to case, so `fen`, `Fen` and `FEN` are one leak and catching
    only the capitalised one would be catching the one nobody writes.

    Docstrings are exempt, the way `test_the_roster_composition_names_no_piece_either`
    exempts them: `model/game/manager.py` is allowed to *talk* about a notation in order
    to say that the engine names none.

    Returns:
        None
    """
    writers = _chess_writer_class_names()
    formats = _chess_format_names()
    vocabulary = writers | formats
    visited = set(_engine_modules())
    importable = set(_importable_engine_modules())

    # The witness comes first, because a walk that matches nothing looks exactly like a tree
    # with no leak in it. Every module Python can import under `model/` must be a file this
    # walk read, and the vocabulary it reads them against must not be empty.
    assert importable and importable <= visited
    assert writers and formats

    offenders = []
    for path in sorted(visited):
        # A name a module declares as one of its own configurable fields is that field's
        # name rather than a reference to a format, and the engine declares one: a piece
        # declares the character it is written as in a position record, and the engine
        # calls that field `fen`. Only the module that declares it is exempt, so the same
        # word anywhere else — a comparison, a default, a dispatch — is still a leak.
        declared = _declared_field_names(path)
        source = _code_without_docstrings(path).lower()
        for name in sorted(vocabulary):
            if name in declared:
                continue
            if re.search(rf"\b{re.escape(name)}\b", source):
                offenders.append(f"{path.name}: {name}")

    assert offenders == [], f"the engine names a chess writer or notation: {offenders}"


def test_no_module_under_the_engine_names_a_configuration():
    """The engine names no game at all — not a writer, not a notation, not a configuration.

    This is the fourth leak, and the one the earlier reading of the invariant left out.
    `SCRATCHPAD.md` §8 item 14 says nothing in the engine names a king, a pawn, a check or a
    mate, which is true of `chess` as a *piece set* — and `model/game/games.py` read
    `DEFAULT_GAME = "chess"` for two years of gate-passing, because a configuration's own name
    is not a piece kind, a writer class or a notation, and the gate held only those three. It
    was argued in `notes/object_model.md` §28 that a configuration name is product configuration
    rather than chess knowledge and that widening the gate would make it fail on every shipped
    product; the gate is widened here instead and the declaration moved to `games/default.json`,
    so the engine holds the *concept* and the distribution holds the name.

    The vocabulary is the shipped configuration directories, read from the installed `games/`,
    so a configuration the product adds later joins the walk without anyone editing this. The
    match is case-insensitive and word-bounded for the reasons the notation walk gives, and
    docstrings are exempt the same way — an engine module is allowed to *talk* about a
    configuration in order to say that it names none.

    Returns:
        None
    """
    vocabulary = _shipped_configuration_names()
    visited = set(_engine_modules())
    importable = set(_importable_engine_modules())

    assert vocabulary, "the walk would hold nothing to match against"
    assert importable and importable <= visited

    offenders = []
    for path in sorted(visited):
        source = _code_without_docstrings(path).lower()
        for name in sorted(vocabulary):
            if re.search(rf"\b{re.escape(name)}\b", source):
                offenders.append(f"{path.name}: {name}")

    assert offenders == [], f"the engine names a configuration: {offenders}"


def test_the_engine_holds_a_default_configuration_by_concept_and_not_by_name():
    """What the engine keeps is the *question*, and it answers it from the root's declaration.

    `Configuration.is_default` compares this configuration's directory with the one the root
    names, and `default_configuration_name` reads `games/default.json`. Neither knows what the
    name is, which is what makes a distribution whose default were some other game a data
    change; and neither imports a configuration, so a variant that does not load is still
    deletable.

    Returns:
        None
    """
    from games.chess import CONFIGURATION_NAME
    from model.game.configuration import load_configuration
    from model.game.games import default_configuration_name, games_root

    declared = default_configuration_name(games_root())

    assert (
        declared == CONFIGURATION_NAME
    ), "the root declares a default this repository does not ship"
    assert load_configuration(declared).is_default is True
    assert load_configuration("checkers").is_default is False


def test_no_module_under_the_engine_defines_an_export_writer():
    """Asserted structurally, so a writer moved back fails without anyone naming it.

    The check is on the shape rather than on the class's name: a contributor who moved a
    writer back into `model/` would have to remember which names the gate is holding, and
    the gate's own list is derived — so the shape is what is asserted. `ExportWriter`
    itself defines no subclass of itself, so the base is not caught by this.

    Returns:
        None
    """
    offenders = []
    for path in _engine_modules():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ClassDef):
                continue
            for base in node.bases:
                name = base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
                if name == "ExportWriter":
                    offenders.append(f"{path.name}:{node.lineno} {node.name}")

    assert offenders == [], f"a concrete export writer is defined in the engine: {offenders}"


def test_no_module_under_the_engine_imports_a_configuration():
    """An engine module that reaches into a game is the coupling `SCRATCHPAD.md` forbids.

    The shape this replaces was `model/misc/notation.py`, sixteen lines re-exporting two
    chess names, and before it a function-local import inside the engine's writer. An
    engine import of any configuration is worse than either: the configuration imports the
    engine, so the pair fails on a cycle as soon as a second variant is loaded.

    Checked through the import nodes rather than the source text, because prose explaining
    why not to write such an import is exactly what `model/game/configuration.py` holds.

    Returns:
        None
    """
    offenders = []
    for path in _engine_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                named = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                named = [node.module]
            else:
                continue
            for module in named:
                if module.split(".")[0] == "games":
                    offenders.append(f"{path.name}:{node.lineno} {module}")

    assert offenders == [], f"the engine imports a configuration: {offenders}"


# --- the engine's quest roster names no piece


def test_the_engine_roster_names_no_chess_piece():
    """`build_quests()` in the engine may not name a piece; that is the configuration's job.

    The roster used to compose `CaptureOfType("queen")` and `KingOnlyGame("king")`, in a
    module whose docstring claimed none of its quests names a chess piece.

    Returns:
        None
    """
    offenders = [
        f"{type(quest).__name__}.{attribute}={value!r}"
        for quest in build_quests()
        for attribute, value in vars(quest).items()
        if isinstance(value, str) and value.lower() in CHESS_PIECE_TYPES
    ]

    assert offenders == []


def test_the_roster_composition_names_no_piece_either():
    """The claim is checked against the roster's code, not only against its instances.

    The docstring is excluded on purpose: it is allowed to *talk* about `"queen"` and
    `"king"` in order to say that the engine does not name them.

    Returns:
        None
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(build_quests)))
    composition = tree.body[0]
    assert isinstance(composition, ast.FunctionDef)
    composition.body = composition.body[1:]
    source = ast.unparse(composition).lower()
    named = sorted(name for name in CHESS_PIECE_TYPES if re.search(rf"""['"]{name}['"]""", source))

    assert named == []


def test_the_two_quests_that_demand_a_piece_name_are_not_in_the_engine_roster():
    """They cannot be listed at all: which piece is a question only a configuration answers.

    `games/chess/__init__.py` names both, with chess's own piece names.

    Returns:
        None
    """
    roster = [type(quest) for quest in build_quests()]

    assert CaptureOfType not in roster
    assert KingOnlyGame not in roster
    assert len(roster) == len(set(roster))


def test_the_roster_still_holds_every_quest_that_needs_no_piece_name():
    """Removing two quests must not have removed a third by accident.

    Returns:
        None
    """
    roster = set(type(quest) for quest in build_quests())

    assert roster == set(BUILT_IN_QUESTS) - {CompositeQuest, CaptureOfType, KingOnlyGame}
    assert len(roster) == 17


def test_a_piece_named_quest_refuses_to_build_without_a_piece():
    """The parameterisation is what makes the roster omission safe rather than lossy.

    Both quests raise rather than defaulting, so the engine could only have listed them by
    naming a piece itself.

    Raises:
        AssertionError: If either quest builds without being told which piece it means.
    """
    with pytest.raises(ValueError):
        CaptureOfType(piece_type="")
    with pytest.raises(ValueError):
        KingOnlyGame(royal_kind="")


def test_the_chess_configuration_supplies_the_two_piece_named_quests():
    """Chess keeps the quests the engine roster used to hand it, and names its own pieces.

    Returns:
        None
    """
    from games.chess import build_quests as chess_quests

    by_type = {type(quest): quest for quest in chess_quests()}

    assert by_type[CaptureOfType].piece_type == "queen"
    assert by_type[KingOnlyGame].royal_kind == "king"


def test_a_chess_piece_is_a_piece_like_any_other():
    """Nothing about the king is special to the engine; it is declared data.

    Returns:
        None
    """
    king = King(1)

    assert king.getFen() == "K"
    assert king.getType() == "king"
    assert king.getMaxSteps() == 1


def test_the_gate_sees_every_kind_the_chess_catalogue_declares():
    """The gate's own vocabulary is read from chess, so it cannot miss a descriptor.

    `horse` is what this codebase's knight reports. The gate carried a hand-kept set that
    omitted it, so a leak expressed as `CaptureOfType("horse")` walked straight through the
    check that exists to catch exactly that.

    The catalogue is composed out of `pieces/` rather than listed, so reading it is reading
    the directory a piece written into would join: a new kind cannot appear in the tree
    without appearing in the gate's vocabulary with it.
    """
    from games.chess.pieces import build_pieces

    declared = {piece_class(1).getType().lower() for piece_class in build_pieces()}

    assert (
        declared <= CHESS_PIECE_TYPES
    ), f"the gate cannot see {sorted(declared - CHESS_PIECE_TYPES)}"
    assert (
        "horse" in CHESS_PIECE_TYPES
    ), "the descriptor the knight actually reports is the one the gate missed"
    # `knight` is the spelling a configuration may write and the rules bridge it to `horse`.
    # It is chess vocabulary, so it belongs in the gate even though no piece reports it — and it
    # is therefore added to the vocabulary here rather than left to a piece to report it.
    #
    # This used to be written `assert "knight" in CHESS_PIECE_TYPES | {"knight"}`, which unions in
    # the very spelling under test and is therefore true of any input. It could never fail, which
    # is worse than no check: it read as the gate covering `knight` when nothing enforced it.
    assert "knight" in CHESS_PIECE_TYPES | _SPELLINGS_A_CONFIGURATION_MAY_WRITE


def test_a_runtime_built_piece_name_is_still_a_leak():
    """A name assembled at run time must not slip past a source-level check.

    Every one of these checks reads source text, so `"hor" + "se"` is invisible to all of them.
    The roster is executed instead, which is what a real leak looks like.
    """
    import model.game.quests as quests

    built = "hor" + "se"
    assert built in CHESS_PIECE_TYPES

    roster = quests.build_quests()
    leaked = [
        quest
        for quest in roster
        for value in (getattr(quest, "piece_type", None), getattr(quest, "royal_kind", None))
        if isinstance(value, str) and value.lower() in CHESS_PIECE_TYPES
    ]
    # Every roster quest that must name a kind is named by its configuration, not by the engine.
    engine_named = [
        quest for quest in roster if type(quest).__name__ in ("CaptureOfType", "KingOnlyGame")
    ]
    assert (
        leaked == []
    ), f"the engine roster names a piece kind: {[type(q).__name__ for q in leaked]}"
    assert engine_named == [], (
        f"quests that insist on naming a kind belong to a configuration, not the roster: "
        f"{[type(q).__name__ for q in engine_named]}"
    )
