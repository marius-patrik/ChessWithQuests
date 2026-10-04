"""What a PGN header record has to do, rather than what it happens to say.

These tests used to assert that the writer's defaults were the strings `"Chess Match"` and
`"*"`. That is the shape of a test that breaks when a default is renamed and passes when a
header is dropped, and it is why they were on the list to be reworked: the assertions described
the implementation rather than the behaviour. What a header record owes its caller is that a
value can be set, that a caller-supplied value wins over the default, that the seven-tag roster
is complete enough to write a PGN with, and that nothing it says is chess.

The last one is a real rule, not a style preference: `model/misc/metadata.py` is the engine's,
and an engine that called a draughts game a chess match would be a configuration's fact living
in the wrong place.
"""

from model.misc.metadata import MetadataWriter

#: The seven tags a PGN header is required to carry.
ROSTER = ("Event", "Site", "Date", "Round", "White", "Black", "Result")


def test_every_required_tag_is_present_before_anything_is_set():
    """A PGN with no tags is not a PGN, so the roster is the writer's to guarantee."""
    headers = MetadataWriter().format_pgn_headers()

    for tag in ROSTER:
        assert f'[{tag} "' in headers, f"{tag} is missing from a fresh header record"


def test_a_value_that_is_set_is_the_value_written():
    writer = MetadataWriter()
    writer.set_header("Result", "1-0")

    assert writer.get_header("Result") == "1-0"
    assert '[Result "1-0"]' in writer.format_pgn_headers()


def test_a_caller_supplied_header_wins_over_the_default():
    """A configuration that knows the name of its game passes it in; the default steps aside."""
    writer = MetadataWriter({"Event": "Club Championship", "White": "Ada", "Black": "Grace"})

    assert writer.get_header("Event") == "Club Championship"
    assert writer.export()["White"] == "Ada"
    assert writer.export()["Result"] == "*", "an untagged result stays untagged"


def test_the_writers_defaults_name_no_game():
    """`model/` is the engine, and the engine does not know what game is being played."""
    import pathlib

    assert MetadataWriter().get_header("Event") == "Game"

    engine_source = (
        pathlib.Path(__file__).parent.parent / "src" / "model" / "misc" / "metadata.py"
    ).read_text(encoding="utf-8")
    assert "Chess Match" not in engine_source, "the engine named a specific game again"
