"""The checkers export: what a draughts game is written as, and what it is not.

Two formats belong to this game and neither has been written yet:

- **Letter notation** — the moves as the square numbers draughts actually uses, one to
  thirty-two, with the long form `18-22` and the short `18x25` when a move takes something.
- **The metadata header** — who played, when, and how the game ended.

What this game deliberately has **no** format for is a position record. There is no FEN for
English draughts: the algebraic naming `e4` is chess's, the square numbers are a coordinate
system and not a position grammar, and a draughts position has no halfmove clock or castling
right to record. Writing one anyway would be inventing a notation in order to satisfy a
writer, which is the opposite of what the writers are for.

The configuration therefore declares no exporters yet rather than declaring a chess one. This
directory is a placeholder in the same way `games/chess/export/` is, and the formats above
land with the export work.
"""
