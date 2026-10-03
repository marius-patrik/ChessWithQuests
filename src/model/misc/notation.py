"""Re-export of the chess algebraic coordinate conversion.

`pos_to_algebraic` and `algebraic_to_pos` name chess squares, so they live in the chess
configuration at `games/chess/export/algebraic.py`. They are re-exported here only so the two
callers outside this repository's configuration layer — `view/player_game_view.py` and
`model/game/manager.py` — keep importing the name they have always imported.

This module is a shim, not a home. Once those two callers import from
`games.chess.export.algebraic` directly, delete it: an engine module that re-exports a chess
naming is exactly the coupling `SCRATCHPAD.md` constraint 1.4 forbids, even when the logic
behind it has already moved.
"""

from games.chess.export.algebraic import algebraic_to_pos, pos_to_algebraic

__all__ = ["algebraic_to_pos", "pos_to_algebraic"]
