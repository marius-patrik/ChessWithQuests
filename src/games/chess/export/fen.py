"""The chess position record, written by a writer that belongs to chess.

FEN is chess's notation, so the writer that produces it lives here rather than in the engine.
Which notations a game can write is the configuration's answer — `notes/object_model.md`
section 7 places each format's writer beside the configuration that uses it, and the engine
keeps only the `ExportWriter` protocol every one of them answers. Adding a notation is a file
in this directory and one line in `games/chess/__init__.py`, and no engine change.

The writer holds no piece table at all. A piece declares the character it is written as, and a
piece that declares none has no place in a position record, which is said out loud rather than
guessed at: the table this replaced wrote an unrecognised piece as a pawn, so a game with an
unfamiliar piece produced a well-formed record that lied about the position and nothing in the
record could reveal it.

## The four fields that were constants

`return f"{board_fen} {turn} - - 0 1"` wrote the same four values whatever the game was doing.
Each is now read from what the game knows, and each says where it comes from:

- **Castling rights** are a property of the two pieces and their flags, exactly as
  `rules/castling.py` already reads them: a colour keeps a right while its royal piece stands on
  the file that rule castles from and has not moved, and the rook for that side stands on its
  own corner and has not moved either. The *names* of those two kinds are read out of this
  configuration's own castling rule rather than written here, so a variant whose rule declares a
  different royal kind is described by the same code and not by a second opinion of what a king
  is called.
- **The en passant target** is read off the last move, because that is what the field describes.
- **The halfmove clock** is counted over the moves themselves: it is the number of plies since a
  capture or a piece that counts as progress, which is `FiftyMoveRule`'s own definition. That
  rule keeps the same number in `state["plies"]`, and `tests/test_position_record.py` asserts
  the two are equal after the same game, so the engine grows no second counter and the fifty-move
  rule stays the only one there is. It is counted here from the move list rather than read from
  the rule so that a configuration with that rule switched off still writes a clock.
- **The fullmove number** follows from how many moves have been played, because the two are the
  same fact.

## The en passant convention, and why this one

**A target is recorded after every two-square advance, whether or not a capture is actually
available to anybody.** That is the convention this writer implements, deliberately, and the
alternative is the one it does not.

Three reasons, in order of weight:

1. It is what the engine already keeps. `EnPassantRule.on_move_made` records the square the
   advanced piece stands on for *any* declared first advance and clears it on the next move of
   any kind. Reading that is reading the game; the other convention is a second opinion about
   the game, taken at write time, by generating the other side's replies for every record.
2. It is what the field says. The FEN specification describes the square behind a pawn that has
   just advanced two squares, and every consumer of the format accepts it.
3. A record that says a capture *could* be made is a record whose truth depends on the rules in
   force, and rules are configuration. The same position written under two configurations would
   read differently, which is the property this whole repository is arranged against.

What it costs is recorded rather than hidden: after `1. e4` two positions that differ only in
whether the fifth rank pawn has moved are written with different en passant fields, so they are
not the same string. `rules/draws.py` keys a repetition on the same convention — a position's
identity asks the rule set what it is offering, which is what `EnPassantRule.target_square`
answers — and is conservative for the same reason and in the same direction.
"""

from typing import Any, List, Optional, Tuple

from model.game.manager import UnsupportedExportFormat
from model.misc.export_writers import ExportWriter

#: The kinds whose movement a piece's having moved governs, and the file offsets the castle rule
#: walks. A colour's rook for the short castle stands three files beyond the file its royal
#: piece castles from, and the long castle's rook four files short of it — the same arithmetic
#: `rules/castling.py` does when it offers the two moves. The letter each is written as is the
#: second half of each pair, in the order the format prescribes.
ROOK_OFFSETS: Tuple[Tuple[int, str], ...] = ((3, "K"), (-4, "Q"))

#: What the four fields between the placement and the side to move say when there is nothing to
#: say. The format's own markers.
NO_RIGHTS = "-"
NO_TARGET = "-"
NO_CLOCK = "0"
FIRST_FULLMOVE = "1"

#: A two-square advance, as the difference of two squares.
DOUBLE_ADVANCE = 2


class ExportFEN(ExportWriter):
    """Writes a board as a Forsyth-Edwards position record."""

    def formats(self) -> Tuple[str, ...]:
        """Return the notations this writer writes.

        Returns:
            Tuple[str, ...]: The one notation this writer writes. A writer declares exactly
            what it can produce, which is how the manager tells a game that cannot write this
            notation from one that had nothing to write.
        """
        return ("FEN",)

    @staticmethod
    def _fen_letter(piece: Any) -> str:
        """Return the character a piece declares for a position record.

        Args:
            piece: The piece being written.

        Returns:
            str: The piece's declared letter, in lower case.

        Raises:
            ValueError: If the piece declares no character. A piece with nothing to say about
                a position record has no position record, and writing it as something else
                would be a lie about the position.
        """
        get_fen = getattr(piece, "getFen", None)
        letter = get_fen() if callable(get_fen) else None
        if not letter:
            get_type = getattr(piece, "getType", None)
            name = get_type() if callable(get_type) else None
            raise ValueError(
                f"a piece of type {name!r} declares no character for a position record, "
                "so this position cannot be written"
            )
        return str(letter).lower()

    def to_fen(
        self,
        board: Any,
        active_color: int = 1,
        moves: Optional[List[Any]] = None,
    ) -> str:
        """Convert a game state to a Forsyth-Edwards position record.

        Args:
            board: Board instance. Its rows and cols decide how many ranks and files the
                record carries, so a board of any size serialises.
            active_color: Active side color (1 for White, -1 for Black).
            moves: The `Move` objects played so far, in order. The last one is what the en
                passant field describes, and the whole list is what the halfmove clock counts.
                Defaults to None, which is a game that has not moved: no target, no plies.

        Returns:
            str: The position record: placement, side to move, castling rights, en passant
            target, halfmove clock and fullmove number.

        Raises:
            ValueError: If a piece on the board declares no character for a position record.
                Nothing is guessed: an undeclared piece has no place in a position record,
                and a record that quietly called it a pawn would be wrong in a way no reader
                could see.
        """
        played = list(moves or [])
        ranks = []
        for r in range(board.rows - 1, -1, -1):
            empty = 0
            rank_str = ""
            for c in range(board.cols):
                piece = board.get_piece_at((r, c))
                if piece is None:
                    empty += 1
                else:
                    if empty > 0:
                        rank_str += str(empty)
                        empty = 0
                    char = self._fen_letter(piece)
                    rank_str += (
                        char.upper()
                        if (piece.getColor() == 1 or piece.getColor() == "white")
                        else char.lower()
                    )
            if empty > 0:
                rank_str += str(empty)
            ranks.append(rank_str)

        board_fen = "/".join(ranks)
        turn = "w" if active_color == 1 else "b"
        fields = (
            board_fen,
            turn,
            self.castling_rights(board),
            self.en_passant_target(board, played),
            str(self.halfmove_clock(played)),
            str(self.fullmove_number(played)),
        )
        return " ".join(fields)

    # --- the four fields the position carries beyond the placement

    def castling_rights(self, board: Any) -> str:
        """Return the castling rights this position still allows.

        A colour keeps a right while the two pieces that right is about are where they started.
        That is the whole of it, and it is the same question `rules/castling.py` asks: the royal
        piece on the file it castles from and unmoved, and the rook for that side on its own
        corner and unmoved. A rook that has travelled and come home has still moved, so the
        right is gone, which is what the flag records and what nothing else on the board does.

        Args:
            board: The position as it stands.

        Returns:
            str: The rights in the order the format prescribes — the first colour's short
            castle, its long castle, the second's, and an empty string when none are left.
        """
        royal_kind, rook_kind = self._rights_kinds()
        letters: List[str] = []
        for color in (1, -1):
            row = 0 if color == 1 else board.rows - 1
            royal = self._of_kind(board, row, board.cols // 2, royal_kind, color)
            if royal is None:
                continue
            for offset, letter in ROOK_OFFSETS:
                file = board.cols // 2 + offset
                rook = self._of_kind(board, row, file, rook_kind, color)
                if rook is not None:
                    # The format writes the second colour's rights in lower case, which is how a
                    # reader tells whose they are without reading the rest of the field.
                    letters.append(letter if color == 1 else letter.lower())
        return "".join(letters) or NO_RIGHTS

    def en_passant_target(self, board: Any, moves: List[Any]) -> str:
        """Return the square a two-square advance asks to be recorded on.

        The target is the square *behind* the pawn that advanced — the square a capturing pawn
        would land on — which is one rank back along the direction that pawn travels, on its own
        file. A move that is not a two-square advance leaves nothing to record, which is the
        format's own marker.

        Args:
            board: The position as it stands, used only to read the advancing pawn's colour
                when the move itself does not carry one.
            moves: The `Move` objects played so far, in order.

        Returns:
            str: The target square in chess's naming, or `-` when the last move was not a
            two-square advance.
        """
        from .algebraic import pos_to_algebraic

        if not moves:
            return NO_TARGET
        move = moves[-1]
        piece = move.piece
        advance = move.end_pos[0] - move.start_pos[0]
        if abs(advance) != DOUBLE_ADVANCE or move.start_pos[1] != move.end_pos[1]:
            return NO_TARGET
        if piece is None:
            piece = board.get_piece_at(move.start_pos)
        if piece is None:
            return NO_TARGET
        # A pawn that advanced two squares took nothing: it could only have done so forward,
        # and a square with a piece on it is not advanced into. Recorded as a test rather than
        # assumed, because the record claims the move was a plain advance.
        if move.captured_piece is not None or move.capture_from is not None:
            return NO_TARGET
        if piece.getColor() not in (1, "white") and piece.getColor() not in (-1, "black"):
            return NO_TARGET
        step = -1 if piece.getColor() in (1, "white") else 1
        return pos_to_algebraic((move.end_pos[0] + step, move.end_pos[1]))

    def halfmove_clock(self, moves: List[Any]) -> int:
        """Return how many plies have been played with no capture and no progress.

        A capture resets it, and so does a move by one of the kinds the fifty-move rule declares
        as progress. Those are the only two things that reset it, which is why this is the same
        number and not a second opinion about it.

        Args:
            moves: The `Move` objects played so far, in order.

        Returns:
            int: The plies since the last capture or advance, zero when the last move was one.
        """
        progress = self._progress_kinds()
        clock = 0
        for move in moves:
            piece = move.piece
            kind = piece.getType() if piece is not None else None
            captured = move.captured_piece is not None or move.capture_from is not None
            clock = 0 if captured or (kind is not None and kind in progress) else clock + 1
        return clock

    def fullmove_number(self, moves: List[Any]) -> int:
        """Return which full move the game is on.

        The two sides' moves are numbered together and the number rises when the second side has
        answered, so a game that has just seen its first move is still on move one.

        Args:
            moves: The `Move` objects played so far, in order.

        Returns:
            int: The full move number, one for a game that has not moved.
        """
        return (len(moves) // 2) + 1

    # --- what the kinds are called, read from this configuration's own rules

    @staticmethod
    def _declared(rule: Any, field: str, fallback: str) -> str:
        """Return one configured value of one of this configuration's own rules.

        The import is inside the method because `..rules` is a section composed out of its own
        directory: reading it at module level would load the configuration's rules before the
        configuration itself, and reading it relatively is what stops a copy of this directory
        from describing its own games with the original's rule names.

        Args:
            rule: An instance of one of this configuration's rules.
            field: The configured value to read.
            fallback: What to answer when the rule declares no such value.

        Returns:
            str: The declared value, or `fallback`.
        """
        value = rule.value.get(field)
        return str(value) if value else fallback

    def _rights_kinds(self) -> Tuple[str, str]:
        """Return the kinds castling is about, as this configuration's own rule declares them.

        Returns:
            Tuple[str, str]: The royal kind and the rook kind, in that order. A board of a size
            that cannot hold a castle has none, and the castling rule's declared file names are
            the fallback for a rule that declares neither.
        """
        from ..rules.castling import CastlingRule

        rule = CastlingRule()
        return (
            self._declared(rule, "royal_kind", "king"),
            self._declared(rule, "rook_kind", "rook"),
        )

    def _progress_kinds(self) -> frozenset:
        """Return the kinds that reset the halfmove clock.

        Returns:
            frozenset: Whatever the fifty-move rule declares resets the clock — its configured
            value rather than a name written here, so a variant that says progress is something
            else is counted that way too.
        """
        from ..rules.draws import FiftyMoveRule

        rule = FiftyMoveRule()
        raw = self._declared(rule, "progress_kinds", "")
        return frozenset(item.strip() for item in raw.split(",") if item.strip())

    @staticmethod
    def _of_kind(board: Any, row: int, col: int, kind: str, color: int) -> Optional[Any]:
        """Return the piece of one kind standing on one square, or None.

        Args:
            board: The position to read.
            row: The rank, counted from the first colour's side.
            col: The file.
            kind: The piece kind wanted.
            color: The colour wanted.

        Returns:
            Optional[Any]: The piece, or None when nothing of that kind of that colour stands
            there. A square off the edge of a board that is not wide enough holds nothing.
        """
        if not 0 <= col < board.cols or not 0 <= row < board.rows:
            return None
        piece = board.get_piece_at((row, col))
        if piece is None or piece.getType() != kind or piece.getColor() != color:
            return None
        return piece if not piece.hasMoved() else None

    def export(self, format_type: str, **kwargs: Any) -> str:
        """Write the board as a position record.

        Args:
            format_type: The notation asked for, in the caller's own spelling. The manager
                looks a writer up without regard to case, so this writer compares the same
                way rather than expecting one exact string.
            **kwargs: Any: `board`, and optionally `active_color` and `moves`.

        Returns:
            str: The board as a position record.

        Raises:
            UnsupportedExportFormat: If the notation asked for is not one this writer writes.
                A writer writes the notations it declares and answers no others: the empty
                string this replaces was indistinguishable from a board with nothing on it.
        """
        if not self._writes(format_type):
            raise UnsupportedExportFormat(
                f"{format_type!r} is not a notation this writer writes; it writes "
                f"{', '.join(self.formats())}"
            )
        return self.to_fen(
            kwargs["board"],
            kwargs.get("active_color", 1),
            kwargs.get("moves"),
        )
