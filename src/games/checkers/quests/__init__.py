"""The checkers quests: one file per quest, composed out of the files that are here.

`build_quests()` below composes this package, so a quest written into `quests/` joins this
configuration the next time it is loaded, with no list here to add its name to. The quests it
returns are those files' own, and it is composed rather than written out because a file in a
section is in force for having been written.

The quests that ship are the engine's generic, fully parameterised ones — a configuration
instantiates them and a game needing something they do not cover writes one more subclass in
this directory. A quest class here is built with no arguments, which is what a file in a
section can be; one that needs a piece named belongs in `build_quests()` below, where the
answer is written down.

Note what is *not* here. There is no quest about check and none about castling, because this
game has neither: nothing can be put in check and a king moves like any other piece.
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
        List[Quest]: A small starter set, all of them switchable from the settings form, plus
        whatever the files in this directory declare.
    """
    from model.game.quests import CaptureN, FirstBlood, PromoteN, WonBy

    return [
        FirstBlood(reward=25),
        CaptureN(count=8, reward=60),
        PromoteN(count=2, reward=40),
        WonBy(color=1, reward=75),
        *compose_section(sys.modules[__name__], notes),
    ]
