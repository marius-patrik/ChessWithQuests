"""The chess rules: every rule the files in this directory declare.

The composition is the directory. `build_rules()` below hands this package to
`model.game.configuration.compose_section`, which composes the modules it holds, so a rule
written into `rules/` is in force the next time this configuration is loaded and there is no
list here to add its name to. What was here instead was a hand-written tuple: the code editor
validated a written rule, wrote the file, reported no problems — and the game played on
without it, saying nothing at all.

What the thirteen rules are has not changed, and neither has the set: castling, en passant,
promotion, bishop colour confinement, check, checkmate, stalemate, insufficient material, the
fifty-move rule, threefold repetition, mutual agreement, flag fall, and which piece kind is
royal. `attacks.py` declares none of them and is composed as a helper, which is what a section
holding shared code beside its entries looks like.

Order is the order `compose_section` composes in, and it is a tie-break rather than a
preference: this package first, then the other files by name. Two rules proposing an outcome
at once are settled by precedence, and by this order when their precedence is equal.

Composition is over this package rather than over a name, because this directory can be
copied. `cp -r games/chess games/house` must compose the copy's rules, not these.
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
