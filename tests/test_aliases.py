"""The fifteen Czech aliases `PRD.md` section 5 requires, checked against the code.

`notes/object_model.md` section 1 says the classes the diagram names in Czech additionally
expose a Czech alias bound to the same object, so the diagram-to-code mapping is discoverable
from the source and from the generated documentation. `PRD.md` section 5 holds the
authoritative table: fifteen diagram names, their canonical English names, and the ASCII
Czech spelling of each. English is canonical; Czech is an alias.

None of the fifteen existed when this file was written, and the two chess ones were the wrong
way round — `games/chess/pieces/horse.py` declared `class Horse(Piece)` with `Knight = Horse`
at the bottom, so English and Czech were swapped. `Tower = Rook` and `Controller =
GameController` were shipped as aliases for names the project does not use.

Six of the fifteen live in a chess piece module and are covered below. The other nine are
engine and view classes in modules this work did not own, so they are still missing and are
listed in `ALIASES_OUTSTANDING` rather than quietly claimed here. A test that asserted they
exist would fail; a test that asserts what is true, and says what is not, is worth more.
"""

import importlib

import pytest

#: Every alias `PRD.md` section 5 requires, as (diagram, canonical module, canonical name).
#: The Czech alias is the canonical name with the Czech spelling substituted, which is what
#: the third column below records.
REQUIRED_ALIASES = (
    ("Figurka", "model.pieces.piece", "Piece", "Figurka"),
    ("Pěšák", "games.chess.pieces.pawn", "Pawn", "Pesak"),
    ("Věž", "games.chess.pieces.rook", "Rook", "Vez"),
    ("Kůň", "games.chess.pieces.knight", "Knight", "Kun"),
    ("Střelec", "games.chess.pieces.bishop", "Bishop", "Strelec"),
    ("Dáma", "games.chess.pieces.queen", "Queen", "Dama"),
    ("Král", "games.chess.pieces.king", "King", "Kral"),
    ("HerníPlocha", "model.game.board", "Board", "HerniPlocha"),
    ("Tah", "model.game.move", "Move", "Tah"),
    ("Hrac", "model.game.player", "Player", "Hrac"),
    ("RevizorTahu", "model.game.validator", "MoveValidator", "RevizorTahu"),
    ("Uzivatel", "model.users.user", "User", "Uzivatel"),
    ("Kwest", "model.game.quest", "Quest", "Kwest"),
    ("HracView", "view.player_view", "PlayerView", "HracView"),
    ("HracGameView", "view.player_game_view", "PlayerGameView", "HracGameView"),
)

#: The nine aliases still missing, with the module each belongs in. They are absent because
#: that module was not in this work's file list, not because the decision was dropped: each is
#: a one-line binding in the module that defines the class, next to the English name.
ALIASES_OUTSTANDING = (
    ("Figurka", "model.pieces.piece"),
    ("HerniPlocha", "model.game.board"),
    ("Tah", "model.game.move"),
    ("Hrac", "model.game.player"),
    ("RevizorTahu", "model.game.validator"),
    ("Uzivatel", "model.users.user"),
    ("Kwest", "model.game.quest"),
    ("HracView", "view.player_view"),
    ("HracGameView", "view.player_game_view"),
)

#: The six chess pieces, whose aliases this work added.
CHESS_ALIASES = (
    ("games.chess.pieces.pawn", "Pawn", "Pesak"),
    ("games.chess.pieces.rook", "Rook", "Vez"),
    ("games.chess.pieces.knight", "Knight", "Kun"),
    ("games.chess.pieces.bishop", "Bishop", "Strelec"),
    ("games.chess.pieces.queen", "Queen", "Dama"),
    ("games.chess.pieces.king", "King", "Kral"),
)


@pytest.mark.parametrize("module_name, canonical, alias", CHESS_ALIASES)
def test_a_chess_piece_exposes_its_czech_alias(module_name, canonical, alias):
    """The alias is the same object, so `Kun` is a `Knight` and not a lookalike.

    Args:
        module_name: The module that defines the class.
        canonical: The canonical English class name.
        alias: The Czech ASCII spelling of it.

    Returns:
        None
    """
    module = importlib.import_module(module_name)

    assert getattr(module, alias) is getattr(module, canonical)
    assert getattr(module, alias).__name__ == canonical


def test_the_alias_table_holds_exactly_fifteen_rows():
    """`PRD.md` section 5 lists fifteen diagram names, and the check covers fifteen.

    A table that has quietly grown or lost a row is not the table the requirement names, and
    a test that kept passing against a shorter one would not notice.

    Returns:
        None
    """
    assert len(REQUIRED_ALIASES) == 15
    assert len({alias for _, _, _, alias in REQUIRED_ALIASES}) == 15


def test_every_chess_alias_is_spelled_without_diacritics():
    """Aliases are ASCII, so `notes/object_model.md` section 1's rule is enforceable.

    Returns:
        None
    """
    for _, _, _, alias in REQUIRED_ALIASES:
        assert alias.isascii(), alias


def test_the_knight_is_canonical_and_its_czech_alias_is_kun():
    """`Horse` is the name this project does not use, so it must not exist to alias.

    The code had this the other way round: `games/chess/pieces/horse.py` declared
    `class Horse(Piece)` and ended with `Knight = Horse`, which made Czech the class and
    English the alias.

    Returns:
        None
    """
    knight = importlib.import_module("games.chess.pieces.knight")

    assert knight.Knight.__name__ == "Knight"
    assert knight.Kun is knight.Knight
    assert not hasattr(knight, "Horse")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("games.chess.pieces.horse")


def test_the_knights_configured_kind_is_not_its_class_name():
    """The descriptor a configuration persists stays `horse`, on purpose.

    `piece_type` is data a configuration chooses and writes into its saved values, so
    renaming it would silently repoint every stored configuration that says `horse`. The
    class name is the thing `PRD.md` section 5 decides; the descriptor is not.

    Returns:
        None
    """
    knight = importlib.import_module("games.chess.pieces.knight").Knight

    assert knight(1).getType() == "horse"
    assert knight(1).getName() == "Knight"
    assert knight(1).getFen() == "N"


def test_tower_is_not_a_name_this_project_uses():
    """`Tower` was dropped: no diagram box carries it, and `Věž` maps to `Rook`.

    `games/chess/pieces/tower.py` shipped `Tower = Rook` on the reasoning that `Tower` is
    Czech for the rook. It is not — `Věž` is, and its ASCII spelling is `Vez`, which is the
    alias that exists.

    Returns:
        None
    """
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("games.chess.pieces.tower")


def test_controller_is_not_a_name_this_project_uses():
    """`Controller` was dropped: the diagram's controller box is `GameManagerController`.

    `controller/controller.py` shipped `Controller = GameController`; the class kept the
    English name and the shorthand is gone.

    Returns:
        None
    """
    controller = importlib.import_module("controller.controller")

    assert controller.GameController.__name__ == "GameController"
    assert not hasattr(controller, "Controller")


def test_the_chess_catalogue_lists_the_canonical_names():
    """`Configuration.pieces` names classes, so it must not carry an alias or a dropped name.

    Returns:
        None
    """
    from games.chess.pieces import PIECES

    assert sorted(piece.__name__ for piece in PIECES) == [
        "Bishop",
        "King",
        "Knight",
        "Pawn",
        "Queen",
        "Rook",
    ]


def test_the_outstanding_aliases_are_recorded_rather_than_silently_absent():
    """`ALIASES_OUTSTANDING` must be the aliases that genuinely do not exist yet.

    That makes the record checkable rather than a claim, and it fails the moment an alias is
    added — at which point the alias has to leave the outstanding list, which is the point.

    Returns:
        None
    """
    still_missing = {
        (alias, module_name)
        for _, module_name, _, alias in REQUIRED_ALIASES
        if not hasattr(importlib.import_module(module_name), alias)
    }

    assert set(ALIASES_OUTSTANDING) == still_missing
    assert len(ALIASES_OUTSTANDING) == 9


def test_no_module_in_the_tree_still_names_the_dropped_horse_or_tower():
    """`Horse` and `Tower` are gone from the chess configuration's own source.

    An alias that survives in one module is an alias that survives: a caller that imports
    `games.chess.pieces.horse` keeps working for a while and then fails somewhere else.

    Returns:
        None
    """
    import pathlib

    import games.chess as chess

    root = pathlib.Path(chess.__file__).parent
    offenders = [
        str(path.relative_to(root.parent))
        for path in root.rglob("*.py")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if line.startswith(("import ", "from ")) and ("Horse" in line or "Tower" in line)
    ]

    assert offenders == []
