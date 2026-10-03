"""The checkers quests: one file per entry.

The quests themselves are the engine's generic, fully parameterised ones — a configuration
instantiates them and a game needing something they do not cover writes one more subclass.
`build_quests()` below is the set English draughts ships with.

Note what is *not* here. There is no quest about check and none about castling, because this
game has neither: nothing can be put in check and a king moves like any other piece.
"""

from typing import List

from model.game.quest import Quest


def build_quests() -> List[Quest]:
    """Build the quests checkers offers by default.

    Returns:
        List[Quest]: A small starter set, all of them switchable from the settings form.
    """
    from model.game.quests import CaptureN, FirstBlood, PromoteN, WonBy

    return [
        FirstBlood(reward=25),
        CaptureN(count=8, reward=60),
        PromoteN(count=2, reward=40),
        WonBy(color=1, reward=75),
    ]
