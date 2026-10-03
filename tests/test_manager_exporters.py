"""The game loop reads its writers and its quests from the configuration, or has none.

`model/game/manager.py` named chess three times: it imported `ChessNotationWriter`, built one
unconditionally, and handed every format to it. It also fell back to the engine's own quest
roster whenever a configuration declared no quests, so a variant was handed challenges it had
not asked for — drawn from a roster that cannot even be built without naming a piece type the
engine has no way to know.

Which notations exist is the configuration's answer. A writer is the only thing that knows
what it can write, so it declares that, and a request for a notation no writer offers is a
question nothing can answer: it raises `UnsupportedExportFormat` rather than returning an
empty transcript that reads like a game with nothing to say.
"""

import inspect

import pytest

from model.game.board import Board
from model.game.configuration import Configuration
from model.game.manager import GameManager, UnsupportedExportFormat


class OnlyOneNotation:
    """A writer that declares one format, standing in for a configuration's own writer."""

    def __init__(self, name, formats):
        """Record what this writer calls itself and what it writes.

        Args:
            name: The label the transcript carries back, so the caller can prove which writer
                answered.
            formats: The format names this writer declares.
        """
        self.name = name
        self._formats = tuple(formats)

    def formats(self):
        """Return the format names this writer writes.

        Returns:
            tuple: The declared names.
        """
        return self._formats

    def export(self, format_type, **kwargs):
        """Write the game in the one format this writer declared.

        Args:
            format_type: The format asked for.
            **kwargs: The game data. Unused, and named so the caller's signature is honoured.

        Returns:
            str: The writer's name and the format, which identifies the answering writer.
        """
        return f"{self.name}:{format_type}"


def _configuration(exporters=None, quests=None):
    """Build a configuration that declares whatever the test needs it to.

    Args:
        exporters: The writers the configuration offers.
        quests: The quests the configuration declares.

    Returns:
        Configuration: A four by four configuration with no rules, so nothing here is
        chess-shaped.
    """
    return Configuration(
        name="probe",
        path="",
        board=Board((4, 4), setup_pieces=False),
        rules=[],
        quests=quests or [],
        clocks=[],
        exporters=exporters or [],
    )


def test_the_manager_takes_its_writers_from_the_configuration():
    """A configuration that declares a writer gets that writer, not a hard-coded one.

    Returns:
        None
    """
    writer = OnlyOneNotation("probe", ("Ledger",))
    game = GameManager(configuration=_configuration(exporters=[writer]))

    assert game.exporters == [writer]
    assert game.notation is writer


def test_a_configuration_with_no_writer_has_none():
    """No writer is not a licence to invent one.

    Returns:
        None
    """
    game = GameManager(configuration=_configuration())

    assert game.exporters == []
    assert game.notation is None


def test_a_format_nobody_writes_raises_a_named_error():
    """The empty string is a lie about a game that had plenty to say.

    Returns:
        None
    """
    game = GameManager(configuration=_configuration())

    with pytest.raises(UnsupportedExportFormat):
        game.transcript("PGN")


def test_the_named_error_says_what_the_configuration_offers():
    """The message names the format asked for and the ones available, so it is actionable.

    Returns:
        None
    """
    game = GameManager(configuration=_configuration(exporters=[OnlyOneNotation("a", ("Ledger",))]))

    with pytest.raises(UnsupportedExportFormat, match="Ledger"):
        game.transcript("Ledger2")


def test_the_writer_is_looked_up_by_format_rather_than_assumed():
    """A format only the second writer offers reaches the second writer.

    The behaviour this replaces handed every format to the first writer and expected it to
    cope, so a configuration whose second writer could write something its first could not had
    no way to say so.

    Returns:
        None
    """
    first = OnlyOneNotation("first", ("Ledger",))
    second = OnlyOneNotation("second", ("Ledger", "Roll"))
    game = GameManager(configuration=_configuration(exporters=[first, second]))

    assert game.transcript("Roll") == "second:Roll"
    assert game.transcript("Ledger") == "first:Ledger"


def test_a_format_is_matched_without_regard_to_case():
    """The writer compares case-insensitively, so the manager must as well.

    Returns:
        None
    """
    game = GameManager(configuration=_configuration(exporters=[OnlyOneNotation("a", ("Ledger",))]))

    assert game.transcript("ledger") == "a:ledger"


def test_the_default_notation_is_the_first_the_configuration_offers():
    """Asking for no notation means the configuration's first, not chess's PGN.

    Returns:
        None
    """
    game = GameManager(
        configuration=_configuration(exporters=[OnlyOneNotation("a", ("Ledger", "Roll"))])
    )

    assert game.default_format() == "Ledger"
    assert game.offered_formats() == ["Ledger", "Roll"]
    assert game.transcript() == "a:Ledger"


def test_a_configuration_that_declares_no_quests_gets_none():
    """The engine roster is not a substitute for a configuration's decision.

    The behaviour this replaces built `model/game/quests.py`'s roster — seventeen quests the
    engine volunteers, two of which cannot even be built without a piece type — for any
    configuration that declared none.

    Returns:
        None
    """
    game = GameManager(configuration=_configuration())

    assert game.quest_manager.get_quests() == []


def test_a_configuration_that_declares_quests_keeps_its_own():
    """The quests in play are the configuration's, and nothing is added to them.

    Returns:
        None
    """
    from model.game.quests import FirstBlood

    declared = [FirstBlood(reward=5)]
    game = GameManager(configuration=_configuration(quests=declared))

    assert game.quest_manager.get_quests() == declared


def test_the_manager_module_names_no_notation_and_no_piece():
    """`SCRATCHPAD.md` constraint 1.4, checked against the module's own source.

    The three chess names the manager used to carry were an import, an instantiation and a
    default argument; a reader has to see none of them to believe the engine is chess-free.

    Returns:
        None
    """
    import model.game.manager as manager

    source = inspect.getsource(manager)

    assert "ChessNotationWriter" not in source
    assert "build_quests" not in source
    assert "PGN" not in source
    assert "games.chess" not in source
