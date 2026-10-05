"""The checkers export: what a draughts game is written as, and what it is not.

Two formats belong to this game and both ship here:

- **Letter notation** — the moves as the square numbers draughts actually uses, one to
  thirty-two, with the long form `18-22` and the short `18x25` when a move takes something.
  `letter.py`.
- **The metadata header** — who played, when, and how the game ended, as `[Name "Value"]`
  pairs derived from the game. `metadata.py`.

What this game deliberately has **no** format for is a position record. There is no FEN for
English draughts: the algebraic naming `e4` is chess's, the square numbers are a coordinate
system and not a position grammar, and a draughts position has no halfmove clock or castling
right to record. Writing one anyway would be inventing a notation in order to satisfy a
writer, which is the opposite of what the writers are for. `ExportLetter` therefore *refuses*
`FEN` by name rather than answering it: `GameManager.writer_for("FEN")` for this configuration
raises `UnsupportedExportFormat`, and a draughts game that has no position record is a
statement about the game rather than a gap in the writer list.

The numbering the letters write in is not declared here either. It is the board's, counted
from the squares the game is played on, and `letter.py` asks `games/checkers/board.py` for it
rather than keeping a second table that could disagree with the perft gate's.

Which notations a game can write is the configuration's answer, so the engine holds only the
`ExportWriter` protocol both of these answer and `notes/object_model.md` section 7 places the
writers beside the configuration that uses them. `build_exporters()` in
`games/checkers/__init__.py` declares them; adding a notation is one file in this directory
and one line there.
"""
