"""The chess quests: the files in this directory, plus the engine's own quests.

`build_quests()` below composes this package, so a quest written into `quests/` joins this
configuration the next time it is loaded — with no list here to add its name to. It returns
fewer quests than the section holds whenever the section holds none, which is how this
directory has shipped: the quests chess offers by default are the engine's own, built with
chess's answers in `games/chess/__init__.py`, because both of the ones that insist on naming
a piece can only be told which piece by the configuration that plays it.

A quest class here is built with no arguments, which is what a file in a section can be. One
that needs a piece named — `CaptureOfType("queen")` — belongs in the configuration's
`build_quests()`, where the answer is written down.
"""

import sys
from typing import List, Optional

from model.game.configuration import compose_section
from model.game.quest import Quest


def build_quests(notes: Optional[List[str]] = None) -> List[Quest]:
    """Build one instance of every quest this configuration's quests directory declares.

    Args:
        notes: A list to record one line in per file that declares no quest, so the settings
            form can name it. Defaults to None, which discards them.

    Returns:
        List[Quest]: The quests these files declare, in the order `compose_section` composes
        them. Empty for this directory as it ships.
    """
    return compose_section(sys.modules[__name__], notes)
