"""The chess rules, composed explicitly.

There is no registry and nothing is discovered by name. `build_rules()` below is the whole
list of what chess is, written out, so the set of rules in force is closed and greppable
and a rule that is not named here is not in force.

Every import here is relative. This directory is part of a configuration that can be copied,
and an absolute `games.chess.rules.…` import meant a copy composed the *original's* rules —
while its board, pieces, clocks and quests were its own.
"""

from typing import Any, List

from model.game.rule import Rule
from .bishop_colour import BishopColourRule
from .castling import CastlingRule
from .check import CheckRule, CheckmateRule, StalemateRule
from .draws import (
    FiftyMoveRule,
    InsufficientMaterialRule,
    MutualAgreementRule,
    ThreefoldRepetitionRule,
)
from .en_passant import EnPassantRule
from .flag import FlagFallRule
from .promotion import PromotionRule
from .royal import RoyalPieceKind

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
