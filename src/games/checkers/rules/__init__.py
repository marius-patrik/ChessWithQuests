"""The checkers rules: every rule the files in this directory declare.

The composition is the directory. `build_rules()` below hands this package to
`model.game.configuration.compose_section`, which composes the modules it holds, so a rule
written into `rules/` is in force the next time this configuration is loaded. What was here
instead was a hand-written tuple, and a file nobody named in it joined nothing without
saying so. Order is the order `compose_section` composes in: this package first, then the
other files by name.

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
  configured so that what this configuration plays by default is the rulebook's game. The cap
  is set to a side's full complement, so `LimitedKingsRule` forbids nothing at its shipped
  value and is only a limit once somebody lowers it.
  - **The three draws are the rulebook's three.** Article 1.32: agreement, the same position for
    the third time, and forty moves by each side without advancing a man or removing a piece. A
    fourth — a draw once neither side has a man left — was here and has been removed; no
    draughts rulebook has it and it was wrong about the two-kings-against-one endgame it was
    meant to describe. `notes/object_model.md` records the removal.
"""

import sys
from typing import List, Optional

from model.game.configuration import compose_section
from model.game.rule import Rule


def build_rules(notes: Optional[List[str]] = None) -> List[Rule]:
    """Build one instance of every rule this configuration's rules directory declares.

    Args:
        notes: A list to record one line in per file that declares no rule, so the settings
            form can name it. Defaults to None, which discards them.

    Returns:
        List[Rule]: The rules in force, in the order `compose_section` composes them. That
        order is also the tie-break when two propose an outcome at once.
    """
    return compose_section(sys.modules[__name__], notes)
