"""The move a capture chain makes: one move that visits several squares.

`notes/object_model.md` registers this as departure 11 — a `Move` carries one starting
square and one ending square, and the diagram's move-type field cannot say how many jumps a
move makes. The departure says a hop sequence is added alongside the start and the end.

**It is added here rather than in `model/game/move.py`, so departure 11 as written is not
what was built.** The departure says `Move` grows the sequence; this is a subclass of `Move`
that carries it, in the configuration whose game needs it. That is a deliberate divergence and
it is the one that keeps the engine unchanged, which is the harder requirement: nothing under
`model/`, `controller/` or `view/` grows a draughts-shaped member. Section 11 of the notes
  is amended and says so: "`HopMove(Move)` carries the hop sequence, and it is declared by the
  configuration whose game needs it", corrected 2026-10-04. This docstring said the section had not
  been amended and that it was the honest record until it was; both halves stopped being true on
  2026-10-04 and were left standing. **Corrected 2026-10-09** — the second half of the pair that
  section 24 of the notes records as still owed.

It is not a dodge. The engine's own `apply_to_board` / `unapply_from_board` pair is the
mechanism, and this class is that pair: it reuses the engine's `Applied` record and the
engine's undo verbatim, and overrides only the step that puts the chain on the board. The
validator's legality test, the game's move execution and every caller in between already go
through those two methods polymorphically, so a three-jump chain is put on and taken off the
board by exactly the same code that puts a castling move on and off it — no engine change, and
no second mechanism. The one thing that does not survive is a caller that rebuilds the board
from a snapshot instead of undoing: `Move` records the piece that moved and this class checks
it by identity, so a walk that puts an equal-looking piece back silently invalidates every
move it had already generated. `tests/test_draughts_perft.py` walks by undoing for that
reason, and says so.

What a chain carries is two ordered sequences, and both are data:

- `hops` is the landing square of each jump, in order. The last one is the move's
  `end_pos`, and the squares before it are the route the piece travelled, which is what the
  undo has to put back.
- `captures` is the square each taken piece stood on, one per hop, in the same order. A
  king's victim is not at a fixed offset from its own square — it is whatever piece stands
  first along the diagonal — so this cannot be derived and has to be carried.

A single jump is the degenerate case of both: one hop, one capture. There is no separate
path through the code for it.
"""

from typing import Any, List, Optional, Tuple

from model.game.move import Applied, Disturbed, Move

#: One jump: the square landed on, and the square the taken piece stood on.
Jump = Tuple[Tuple[int, int], Tuple[int, int]]


class HopMove(Move):
    """A move that takes one or more pieces in a chain of jumps.

    Attributes:
        hops: The landing square of each jump, in order. The last is `end_pos`.
        captures: The square each taken piece stood on, one per hop, in the same order.
        captured_pieces: Every piece this move took, in the order it took them. The engine's
            `Move` records one captured piece because one is all it ever needed; a chain can
            take several, and the ones it recorded are read by the quests and by the board's
            capture lists.
        route: Every square the moving piece stands on during the move, the starting square
            first and each landing square after it.
    """

    def __init__(
        self,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
        hops: Tuple[Tuple[int, int], ...] = (),
        captures: Tuple[Tuple[int, int], ...] = (),
        piece: Optional[Any] = None,
        move_type: str = "capture",
        promotion_piece: Optional[Any] = None,
    ):
        """Initialize a HopMove.

        Args:
            start_pos: The (row, col) square the move begins on.
            end_pos: The (row, col) square the move ends on, which is the last hop.
            hops: The landing square of each jump, in order.
            captures: The square each taken piece stood on, one per hop, in the same order.
            piece: The piece making the move, once one has been established.
            move_type: What kind of move this is. A chain that takes something is a
                `"capture"`; the mandatory-capture rule reads that to know what is a capture
                and what is not.
            promotion_piece: The piece that replaces the mover, when it changes kind.

        Raises:
            ValueError: If the two sequences disagree in length. A hop that takes no piece or
                a victim that no hop passed over describes a move that cannot be put on the
                board at all, and saying so at construction is better than leaving the board
                half-way through it.
        """
        if len(hops) != len(captures):
            raise ValueError(
                f"a chain of {len(hops)} jumps cannot take {len(captures)} pieces; "
                "each jump takes exactly one piece"
            )
        if hops and tuple(hops[-1]) != (end_pos[0], end_pos[1]):
            raise ValueError(
                f"a chain ends on its last hop {tuple(hops[-1])}, not on {tuple(end_pos)}"
            )
        super().__init__(
            start_pos=start_pos,
            end_pos=end_pos,
            piece=piece,
            move_type=move_type,
            promotion_piece=promotion_piece,
        )
        self.hops: Tuple[Tuple[int, int], ...] = tuple((h[0], h[1]) for h in hops)
        self.captures: Tuple[Tuple[int, int], ...] = tuple((c[0], c[1]) for c in captures)
        self.captured_pieces: Tuple[Any, ...] = ()

    @property
    def route(self) -> Tuple[Tuple[int, int], ...]:
        """Every square the moving piece stands on during this move.

        Returns:
            Tuple[Tuple[int, int], ...]: The starting square first, then each landing
            square in order.
        """
        return (self.start_pos, *self.hops)

    @property
    def captured_count(self) -> int:
        """How many pieces this move takes.

        Returns:
            int: One per hop, so a chain of three jumps takes three pieces however short or
            long each individual jump was.
        """
        return len(self.captures)

    def apply_to_board(self, board: Any) -> Optional[Applied]:
        """Put the whole chain on the board and report what is needed to take it off again.

        The chain is checked before any of it is played: every landing square must be inside
        the board and empty, and every captured square must hold a piece of the other side.
        A chain that fails any of those is refused whole, so a legality test never leaves a
        board with half a capture on it, and a rejected move leaves nothing to undo.

        The piece is lifted from its starting square and set down on the last landing square
        only. The squares it passed over in between were empty when it passed over them and
        are written to nothing at all — writing the piece onto each of them in turn would
        leave it standing on every square it visited, and a chain of three jumps would
        finish with the piece in three places at once.

        Args:
            board: The board the move is played on.

        Returns:
            Optional[Applied]: What the move disturbed, in the engine's own record — the same
            record, and so the same undo, as any other move — or None when nothing stands on
            the starting square or some square of the chain is not as the move claims.
        """
        piece = self.piece if self.piece is not None else board.get_piece_at(self.start_pos)
        if piece is None:
            return None

        if not self._chain_is_playable(board, piece):
            return None
        self.piece = piece

        applied = Applied(
            squares=self._disturbed(board),
            captures=(len(board.captured_white), len(board.captured_black)),
        )

        taken: List[Any] = []
        for square in self.captures:
            victim = board.get_piece_at(square)
            taken.append(victim)
            board.set_piece_at(square, None)
            if victim.getColor() == 1 or victim.getColor() == "white":
                board.captured_white.append(victim)
            else:
                board.captured_black.append(victim)
        self.captured_piece = taken[0] if taken else None
        self.captured_pieces = tuple(taken)

        board.set_piece_at(self.start_pos, None)
        board.set_piece_at(self.end_pos, piece)
        piece.has_moved = True

        if self.promotion_piece is not None:
            board.replace_piece(self.end_pos, self.promotion_piece)
        return applied

    def _chain_is_playable(self, board: Any, piece: Any) -> bool:
        """Report whether this chain can be played on this board as it stands.

        Every square is tested against the position before the move, which is the only
        position in which a chain is legal: a piece captured earlier in the chain is gone
        from the board when the chain was built, so the later hops of the chain are tested
        against a board those victims are already lifted from.

        Args:
            board: The board the move would be played on.
            piece: The piece making the move.

        Returns:
            bool: True when the starting square holds this piece, every landing square is
            inside the board and empty, and every captured square holds a piece of the other
            side.
        """
        if board.get_piece_at(self.start_pos) is not piece:
            return False

        colour = piece.getColor()
        for landing in self.hops:
            if not board.is_within_bounds(landing[0], landing[1]):
                return False
            if board.get_piece_at(landing) is not None:
                return False

        for square in self.captures:
            if not board.is_within_bounds(square[0], square[1]):
                return False
            victim = board.get_piece_at(square)
            if victim is None or victim.getColor() == colour:
                return False
        return True

    def _disturbed(self, board: Any) -> List[Disturbed]:
        """List every square this chain is about to write to, and what stands on it now.

        The undo restores each of these from this list, so the intermediate landing squares
        and the captured squares have to be in it or the move cannot be taken off again.
        Their original occupants are almost always `None` — a landing square must be empty
        and a captured square holds the piece that is being removed — but recording what is
        there anyway costs nothing and means a chain whose geometry turns out to be wrong is
        still undone exactly.

        Args:
            board: The board the move would be played on.

        Returns:
            List[Disturbed]: One entry per square the chain touches, the starting square
            first and each landing square and captured square after it.
        """
        squares: List[Tuple[int, int]] = [self.start_pos]
        squares.extend(self.hops)
        squares.extend(self.captures)

        disturbed: List[Disturbed] = []
        for square in squares:
            if any(recorded[0] == square for recorded in disturbed):
                continue
            occupant = board.get_piece_at(square)
            disturbed.append((square, occupant, occupant.has_moved if occupant else False))
        return disturbed
