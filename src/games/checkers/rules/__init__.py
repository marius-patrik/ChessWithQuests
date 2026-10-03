"""The checkers rules, composed explicitly.

There is no registry and nothing is discovered by name. `RULES` below is the whole list of
what English draughts is, written out, so the set of rules in force is closed and greppable
and a rule that is not named here is not in force.

Three things are worth reading off the list rather than assuming:

- **Nothing declares a royal piece.** There is no king in this game — a king is a man that
  has been crowned, and it is taken like any other piece — so nothing can be put in check and
  the engine's check machinery finds nothing to do. A configuration with no royal piece is
  the shape a game like this takes, not a gap.
- **Nothing removes a man.** English draughts has no removal rule: a man that reaches the far
  row is crowned and keeps playing, and the only ways out of the game are losing every piece,
  being unable to move, and the three draws.
- **Two of the eight rules are not English draughts at all.** `LimitedKingsRule` caps how many
  kings a side may hold, which no draughts rulebook does, and `CaptureRule` ships with its
  maximum-capture restriction *switched off*, because the World Checkers Draughts Federation
  rulebook says a player "may select any one that they wish, not necessarily that which gains
  the most pieces". Both are here because they are variants somebody plays, and both are
  configured so that what this configuration plays by default is the rulebook's game.
"""

from typing import List

from model.game.rule import Rule

from .capture import CaptureRule
from .crowning import CrowningRule
from .draws import FiftyMoveRule, InsufficientMaterialRule, MutualAgreementRule
from .immobilisation import ImmobilisationRule
from .landing import LandingRule
from .limited_kings import LimitedKingsRule

#: Every rule this configuration plays by, in the order they are declared.
RULES = (
    CaptureRule,
    LandingRule,
    CrowningRule,
    LimitedKingsRule,
    ImmobilisationRule,
    InsufficientMaterialRule,
    FiftyMoveRule,
    MutualAgreementRule,
)


def build_rules() -> List[Rule]:
    """Build one instance of every checkers rule, at its English-draughts value.

    Returns:
        List[Rule]: The rules in force, in declaration order. That order is also the tie
        break when two propose an outcome at once.
    """
    return [rule() for rule in RULES]
