"""What a game header owes its caller: derived from the game, and naming no game itself.

This file used to hold the header tests and imported `model.misc.metadata`. That module is
gone — the header is a format rather than an engine mechanism, so it is
`games/chess/export/metadata.py` now, and with it the seven-tag roster it hard-coded.

The last rule here is the one that moved with it. The old assertion was that one string was
absent from one file, which is the shape of a test that passes the moment the string moves.
The assertion now is that **no module under `model/` names a single field of the roster**, so
a header that drifts back into the engine is caught whatever it says in it.

The header used to announce `Player 1`, `Player 2` and this product's own name. Those were
three statements about nobody in particular, and they are what `SCRATCHPAD.md` §4.5 item 18's
last criterion — "derived from the players and result, with no placeholder strings" — means.
"""

import ast
import datetime
import importlib.util
import pathlib

import pytest

from games.chess.export.metadata import UNFINISHED, UNKNOWN, ExportMetadata
from model.game.rule import Result

#: The fields a PGN header is required to carry.
ROSTER = ("Event", "Site", "Date", "Round", "White", "Black", "Result")


class _Person:
    """A stand-in for the `User` a `Player` is linked to."""

    def __init__(self, name="", username=""):
        """Record the two attributes a name is read from.

        Args:
            name: The person's name.
            username: The person's handle.
        """
        self.name = name
        self.username = username


class _Side:
    """A stand-in for the `Player` that owns one side of a game."""

    def __init__(self, color, user=None):
        """Record which side this is and who played it.

        Args:
            color: The side, as 1 or -1.
            user: The person playing it, or None for nobody this program knows.
        """
        self.color = color
        self.user = user

    def getColor(self):
        """Return the side.

        Returns:
            int: The side this player holds.
        """
        return self.color

    def getUser(self):
        """Return the person playing this side.

        Returns:
            _Person: The linked person, or None.
        """
        return self.user


def _quoted_fields(path):
    """Return every string literal a module under `model/` spells as a header field.

    Read through the AST rather than by searching the text, for two reasons. Prose is allowed
    to *talk* about the roster in order to say the engine holds none, and an identifier is
    not a field: `model/game/rule.py` declares a `Result` class, which is the engine's
    outcome type and not a tag in a header. Only a literal is a claim about the text a game
    is written with.

    Args:
        path: The module's path.

    Returns:
        set: Every header field the module spells as a string literal.
    """
    declared = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in ROSTER:
            declared.add(node.value)
    return declared


def _engine_modules():
    """Yield the path of every module under `model/`.

    Yields:
        pathlib.Path: Each module's path, with `__pycache__` ignored.
    """
    import model

    root = pathlib.Path(model.__file__).parent
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


# --- the roster is guaranteed, and every field is writable


def test_every_required_field_is_present_before_anything_is_set():
    """A header with no fields is not a header, so the roster is the writer's to guarantee."""
    tags = ExportMetadata().header_values()

    for tag in ROSTER:
        assert tag in tags, f"{tag} is missing from a fresh header record"


def test_every_required_field_appears_in_a_written_header():
    """The written form is what a reader parses, so it is the written form that is checked."""
    written = ExportMetadata().export("Field-Field-Extra")

    for tag in ROSTER:
        assert f'[{tag} "' in written, f"{tag} is missing from a written header"


def test_a_field_that_is_declared_is_the_field_that_is_written():
    writer = ExportMetadata()
    writer.set_header("Result", "1-0")

    assert writer.get_header("Result") == "1-0"
    assert '[Result "1-0"]' in writer.to_field_field_extra()


def test_a_declared_field_wins_over_the_rosters_own_marker():
    """A configuration that knows the name of its game passes it in; the marker steps aside."""
    writer = ExportMetadata({"Event": "Club Championship", "White": "Ada", "Black": "Grace"})
    tags = writer.header_values()

    assert tags["Event"] == "Club Championship"
    assert tags["White"] == "Ada"
    assert tags["Black"] == "Grace"


def test_a_field_never_declared_reads_as_the_marker():
    writer = ExportMetadata()

    assert writer.get_header("Event") == ""
    assert writer.header_values()["Event"] == UNKNOWN


# --- nothing in it is invented


def test_the_header_names_the_players_who_played():
    """White and Black come from the users behind the two sides, not from a roster of names."""
    sides = [_Side(1, _Person(name="Ada Lovelace")), _Side(-1, _Person(name="Grace Hopper"))]
    tags = ExportMetadata().header_values(players=sides)

    assert tags["White"] == "Ada Lovelace"
    assert tags["Black"] == "Grace Hopper"


def test_a_handle_is_used_when_a_player_has_no_name():
    """A user is a person whether or not anybody filled in their name."""
    sides = [_Side(1, _Person(username="ada")), _Side(-1, _Person(name="  ", username="grace"))]

    assert ExportMetadata().header_values(players=sides)["Black"] == "grace"


def test_the_header_carries_no_placeholder_string():
    """`SCRATCHPAD.md` §4.5 item 18: derived from the players and result, no placeholders.

    The defaults used to be `Player 1`, `Player 2` and `"ChessWithQuests"` for `Site`, so a
    draughts transcript announced itself as a game of chess.

    Returns:
        None
    """
    sides = [_Side(1, _Person(name="Ada")), _Side(-1, _Person(name="Grace"))]
    won = Result(kind="win", winner=1, reason="resignation")

    for tags in (
        ExportMetadata().header_values(players=sides, result=won),
        ExportMetadata().header_values(),
    ):
        for tag, value in tags.items():
            assert "Player 1" not in value
            assert "Player 2" not in value
            assert "ChessWithQuests" not in value


def test_a_field_nobody_supplied_says_so_rather_than_naming_somebody():
    """`?` is how the seven-tag roster itself says *not supplied* — a claim, not an invention."""
    sides = [_Side(1, _Person(name="Ada")), _Side(-1, None)]

    assert ExportMetadata().header_values(players=sides)["Black"] == UNKNOWN


def test_the_site_is_not_the_product_that_ships_it():
    """Nothing in the program knows where a game is played, so nothing may claim to."""
    assert ExportMetadata().header_values()["Site"] == UNKNOWN


def test_the_date_is_the_day_the_game_began():
    began = datetime.datetime(2026, 3, 4, 17, 30)

    assert ExportMetadata().header_values(date=began)["Date"] == "2026.03.04"


def test_the_result_is_the_outcome_the_rules_reached():
    """A reason written for the status line is not a roster token; the outcome is."""
    won = Result(kind="win", winner=-1, reason="checkmate")
    lost = Result(kind="loss", winner=-1, reason="resignation")
    drawn = Result(kind="draw", reason="agreement")

    assert ExportMetadata().header_values(result=won)["Result"] == "0-1"
    assert ExportMetadata().header_values(result=lost)["Result"] == "0-1"
    assert ExportMetadata().header_values(result=drawn)["Result"] == "1/2-1/2"


def test_a_game_still_being_played_says_so():
    assert ExportMetadata().header_values()["Result"] == UNFINISHED


def test_an_outcome_naming_no_winner_is_not_written_as_a_decision():
    """A decisive kind with nobody winning it is a fact the roster has no spelling for."""
    stranded = Result(kind="win", winner=None, reason="immobilised")

    assert ExportMetadata().header_values(result=stranded)["Result"] == UNFINISHED


# --- it is a writer, and writers answer the notations they declare


def test_the_header_writer_declares_the_notation_the_diagram_draws():
    """*Field - Field - Extra* is the diagram's name for a header, and the declared spelling."""
    writer = ExportMetadata()
    sides = [_Side(1, _Person(name="Ada")), _Side(-1, _Person(name="Grace"))]

    assert writer.formats() == ("Field-Field-Extra",)
    assert writer._writes("field-field-extra") is True
    assert '[White "Ada"]' in writer.export("field-field-extra", players=sides)
    assert '[White "Ada"]' in writer.export(" Field-Field-Extra ", players=sides)


def test_the_header_writer_refuses_a_notation_it_does_not_write():
    """It is one format among five now, and refusing the rest is what makes it one format."""
    from model.game.manager import UnsupportedExportFormat

    with pytest.raises(UnsupportedExportFormat, match="Field-Field-Extra"):
        ExportMetadata().export("PGN")


def test_the_written_header_is_a_field_a_value_field_and_an_extra():
    """The grammar, asserted rather than described: the two named sides, then the extras."""
    sides = [_Side(1, _Person(name="Ada")), _Side(-1, _Person(name="Grace"))]
    writer = ExportMetadata({"Event": "Club Championship", "WhiteElo": "1800"})
    won = Result(kind="win", winner=1, reason="resignation")

    lines = writer.to_field_field_extra(players=sides, result=won).splitlines()

    assert [line.split(" ")[0] for line in lines] == [
        "[Event",
        "[Site",
        "[Date",
        "[Round",
        "[White",
        "[Black",
        "[Result",
        "[WhiteElo",
    ]
    assert lines[4] == '[White "Ada"]'
    assert lines[7] == '[WhiteElo "1800"]', "an extra field follows the roster"


def test_the_transcript_and_the_header_write_the_same_tags():
    """One roster, written twice, is two that drift. The PGN writer composes this writer."""
    from games.chess.export.pgn import ExportPGN

    sides = [_Side(1, _Person(name="Ada")), _Side(-1, _Person(name="Grace"))]
    metadata = ExportMetadata({"Event": "Club Championship"})

    header = metadata.to_field_field_extra(players=sides)
    transcript = ExportPGN().export("PGN", moves=[], metadata=metadata, players=sides)

    assert transcript.startswith(header + "\n\n")
    assert '[Event "Casual Game"]' not in transcript


def test_the_header_follows_the_game_rather_than_accumulating_what_it_said_before():
    """The manager used to write the outcome into a header it kept between transcripts.

    It held one header object, set `Result` on it and handed the same object down every time,
    so a header carried whatever the last transcript had said about it. Derivation reads the
    game each time, so a game that has finished says so and a new game does not inherit it.

    Returns:
        None
    """
    from games.chess import build_configuration
    from model.game.manager import GameManager
    from model.game.move import Move

    configuration = build_configuration()
    unfinished = GameManager(configuration=configuration).transcript("Field-Field-Extra")

    game = GameManager(configuration=configuration)
    assert game.make_move(Move((1, 5), (2, 5)))
    assert game.make_move(Move((6, 4), (4, 4)))
    assert game.make_move(Move((1, 6), (3, 6)))
    assert game.make_move(Move((7, 3), (3, 7)))
    assert game.finish_game() is not None
    finished = game.transcript("Field-Field-Extra")

    assert f'[Result "{UNFINISHED}"]' in unfinished
    assert '[Result "0-1"]' in finished
    assert (
        game.metadata.header_values()["Result"] == UNFINISHED
    ), "the header is derived per transcript, so the record itself is not written into"


# --- and it no longer lives in the engine


def test_the_engine_no_longer_holds_a_header_writer():
    """Asserted as the module's absence, which is the only thing that stops it coming back.

    `model/misc/notation.py` was deleted for the same reason and
    `tests/test_engine_holds_no_chess.py` asserts its absence the same way.

    Returns:
        None
    """
    assert importlib.util.find_spec("model.misc.metadata") is None


def test_no_module_under_the_engine_names_a_field_of_the_header():
    """The rule the old test could not express: the roster is a format, and formats are not the
    engine's.

    The assertion used to be that one string was absent from one file. A walk over the tree
    with the roster as the vocabulary catches the roster arriving anywhere, in any spelling,
    and catches a header that comes back carrying different fields.

    Returns:
        None
    """
    offenders = []
    for path in _engine_modules():
        for field in sorted(_quoted_fields(path)):
            offenders.append(f"{path.name}: {field}")

    assert offenders == [], f"the engine holds header fields: {offenders}"


def test_the_manager_takes_the_header_from_the_configuration_and_invents_none():
    """`GameManager` used to build a header with no arguments; it now reads the configuration's.

    A configuration that declares no header has none, and a writer that needs one is told so
    rather than handed a substitute — which is the same rule the writers and the quests follow.

    Returns:
        None
    """
    from model.game.board import Board
    from model.game.configuration import Configuration
    from model.game.manager import GameManager

    declared = ExportMetadata({"Event": "House Championship"})
    offered = Configuration(
        name="house",
        path="",
        board=Board((4, 4), setup_pieces=False),
        metadata=declared,
    )
    silent = Configuration(name="silent", path="", board=Board((4, 4), setup_pieces=False))

    assert GameManager(configuration=offered).metadata is declared
    assert GameManager(configuration=silent).metadata is None
