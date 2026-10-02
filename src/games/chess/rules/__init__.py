"""The chess rules, composed explicitly.

There is no registry and nothing is discovered by name. `build_rules()` below is the whole
list of what chess is, written out, so the set of rules in force is closed and greppable
and a rule that is not named here is not in force.
"""

from typing import Any, List

from model.game.rule import Rule
from games.chess.rules.bishop_colour import BishopColourRule
from games.chess.rules.castling import CastlingRule
from games.chess.rules.check import CheckRule, CheckmateRule, StalemateRule
from games.chess.rules.draws import (
    FiftyMoveRule,
    InsufficientMaterialRule,
    MutualAgreementRule,
    ThreefoldRepetitionRule,
)
from games.chess.rules.en_passant import EnPassantRule
from games.chess.rules.flag import FlagFallRule
from games.chess.rules.promotion import PromotionRule
from games.chess.rules.royal import RoyalPieceKind

#: Every rule orthodox chess plays by, in the order they are declared.
RULES = (
    RoyalPieceKind,
    CastlingRule,
    EnPassantRule,
    PromotionRule,
    BishopColourRule,
    CheckRule,
    CheckmateRule,
    StalemateRule,
    InsufficientMaterialRule,
    FiftyMoveRule,
    ThreefoldRepetitionRule,
    MutualAgreementRule,
    FlagFallRule,
)


def build_rules() -> List[Rule]:
    """Build one instance of every chess rule, at its orthodox value.

    Returns:
        List[Rule]: The rules in force, in declaration order. That order is also the tie
        break when two propose an outcome at once.
    """
    return [rule() for rule in RULES]
