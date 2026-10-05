"""The chess clocks: one file per clock.

The clock chess is played under is a file in this directory, because `clocks/` is a composed
section: `build_clocks()` below hands this package to `model.game.configuration.compose_section`,
which builds one instance of every `Clock` subclass the files here declare. `Fischer` is in force
because it is a file in `clocks/`, and there is no list to add its name to.
"""

import sys
from typing import List, Optional

from model.game.clock import Clock
from model.game.configuration import compose_section


def build_clocks(notes: Optional[List[str]] = None) -> List[Clock]:
    """Build one instance of every clock this configuration's clocks directory declares.

    Args:
        notes: A list to record one line in per file that declares no clock, so the settings
            form can name it. Defaults to None, which discards them.

    Returns:
        List[Clock]: The clocks this configuration offers, in the order `compose_section`
        composes them: this package first, then the remaining files by name.
    """
    return compose_section(sys.modules[__name__], notes)
