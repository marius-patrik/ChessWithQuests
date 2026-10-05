"""The chess game transcript, written as PGN text by a writer that belongs to chess.

PGN is chess's notation, so the writer that produces it lives here rather than in the engine.
The header comes from the `ExportMetadata` the manager hands down and the movetext from the
game's own moves, so the writer decides nothing about either: it is the format's arrangement
of what it is given, and `notes/object_model.md` section 7 places it beside the configuration
that uses it.

**The header is not built here.** A header is a format of its own — *Field - Field - Extra*,
which the diagram enumerates beside PGN — so this writer composes that writer rather than
holding a second copy of the roster. It passes on the fields it is given and adds no tag of
its own, which is what stops the two from drifting apart: a header written on its own and a
header inside a PGN are the same text produced by the same code.

There is no fallback header any more. The `'[Event "Casual Game"]\n[Result "*"]'` this replaces
was three facts invented at write time — an event nobody was playing, a site nobody was at —
and it was what a PGN was written as whenever the caller had no metadata to hand, which is
what `GameManager` did on every transcript. A writer handed a game and nothing else still
writes a header, and it is derived from that game.

## Why the movetext is a replay and not a list of squares

Standard Algebraic Notation asks a question about the *position*: `Nbxd5` and `Nfxd5` say which
knight moved, which is only knowable by looking at the board the move was made on; `+` and `#`
ask what the move did to the other side's royal piece and to their answers, which is only
knowable by looking at the position *after* it. A `Move` carries none of that. So this writer
replays the game — on a fresh board dealt by its own configuration, with its own rules, one
move at a time — and reads each move in the position it was actually played in. That is the
whole reason the file grew a replay: there is no other way to write the notation the format is.

**The replay composes its own rules and never touches the game's.** The rules in force hold the
history of the game being played: which colours have castled, whose two-square advance may be
taken in passing, which positions a repetition has seen. Replaying through them would wipe that
history and leave a finished game whose own rules had forgotten it. So the replay asks its own
copy, imported relatively from `..rules` — a copied configuration replays with the copy's rules,
which is what `games/chess/__init__.py` exists to guarantee.

**Which castle is which comes from the rook, not from the spelling.** `O-O` is the short castle
and `O-O-O` the long one, and what distinguishes them is which side the rook stands on. The
engine's move type for a castle is the single word `castling`, with no side in it, so the rook's
own square is read; the name of the move type is the fallback for a hand-built move that carries
no companion.

**A move that cannot be replayed is still written.** A caller may hand this writer a move list
that did not begin at the position it is given — a fragment quoted out of a game, or a test's
two squares. The token is written from what the move itself carries, the replay stops there,
and no suffix is claimed for anything after it, because a check that was never looked for must
not be written as one that was not found.

**The position the game began in is handed over, not inferred.** `GameManager.transcript` passes
`opening_position` to every writer, and `Replay` plays on that. What is left as a default is this
configuration's own starting position, which is a fact this configuration knows rather than
something the writer makes up: a caller that holds a different position passes it, and a caller
that passes nothing gets this game's opening and a replay that stops at the first move that
does not belong to it.
"""

from datetime import datetime
from typing import Any, List, Optional, Tuple

from model.game.manager import UnsupportedExportFormat
from model.game.move import Move
from model.game.validator import MoveValidator
from model.misc.export_writers import ExportWriter

from .algebraic import file_letter, pos_to_algebraic
from .metadata import ExportMetadata

#: The piece kind the algebraic notation names by its destination alone. A pawn is the one piece
#: SAN has no letter for, and chess's own pawn reports this descriptor — a variant that renamed
#: it renames this constant with it.
PAWN_KIND = "pawn"

#: What a capture is written as between the disambiguating hint and the destination.
CAPTURE_MARK = "x"

#: The two castles, as the notation spells them.
SHORT_CASTLE = "O-O"
LONG_CASTLE = "O-O-O"


def _replay_of(move: Any) -> Move:
    """Build the move to play on the replay board.

    A fresh `Move` rather than the one that was played, because the one that was played holds
    the *live* pieces: replaying it would lift this game's pawn onto the replay board and leave
    the replay's own pawn standing where it came from. Everything a move carries about itself is
    carried over — the kind, the square a taken piece stands on, the rook a castle carries, and
    the piece a promotion produces — and nothing that identifies an object is.

    Args:
        move: The `Move` as it was played.

    Returns:
        Move: The same move, resolved against whichever board it is played on.
    """
    return Move(
        start_pos=move.start_pos,
        end_pos=move.end_pos,
        move_type=move.move_type,
        capture_from=move.capture_from,
        companion_start=move.companion_start,
        companion_end=move.companion_end,
        promotion_piece=move.promotion_piece,
    )


class Replay:
    """One game played again from its configuration's own starting position.

    The notation is read off this and not off the `Move` objects, because a move says where it
    went and what it took and nothing about the position it was made in, and the position is
    what Standard Algebraic Notation is written from.

    Attributes:
        board: The position as it stands, dealt from the configuration's own starting placement.
        rules: This replay's own copy of the rules in force, notified of every move exactly as
            the game notifies them.
        validator: The engine's validator over that board and those rules, asked the two
            questions a suffix depends on: is this side's royal piece attacked, and does it have
            any legal move at all.
        active: Whose turn it is in the position as it stands.
        broken: Whether the replay could no longer follow the game, so no position after the
            point it stopped is known and no suffix may be claimed.
    """

    def __init__(
        self, moves: List[Any], position: Optional[Any] = None, rules: Optional[List[Any]] = None
    ):
        """Deal the starting position and take hold of a rule set to read the game through.

        The imports are inside the constructor because `..board` imports the naming out of this
        same package: a module-level import would ask for `games.chess.board` while that module
        is still being loaded, because it is what started this one.

        Args:
            moves: The `Move` objects as they were played, in order.
            position: The position the moves were played from — where the game began. The
                manager hands this to every writer, so a game is written against the position
                it started in rather than against whatever a configuration deals by default.
                Defaults to None, which deals this configuration's own starting position: what
                a game in this configuration always starts from, and a fact this configuration
                knows. A caller holding a different position hands it in, and a caller who
                hands nothing gets this one and a replay that stops at the first move that
                does not belong to it — which is a record of what it was given, not a guess.
            rules: A rule set to read the game through. Defaults to None, which composes this
                configuration's own rules — what a caller who stands a `Replay` up on its own
                gets. A rule set handed in is *borrowed*: it is reset to its starting state
                before the first move and belongs to whoever composed it, so two replays through
                one writer are sequential by construction, which is how a writer uses them.
        """
        from ..board import build_board

        self.moves: List[Any] = list(moves or [])
        self.board: Any = position if position is not None else build_board()
        if rules is None:
            from ..rules import build_rules

            rules = build_rules()
        # `reset`, not `attach`: a borrowed rule set carries the last replay's history — which
        # colours have castled, whose advance may be taken, which positions a repetition has
        # seen — and `reset` is the one call that clears it first. This is the same call
        # `GameManager.new_game` makes and the reason it exists.
        self.rules: List[Any] = [rule for rule in rules]
        for rule in self.rules:
            rule.reset()
        self.validator: MoveValidator = MoveValidator(self.board)
        self.validator.set_rules(self.rules, attach=False)
        self.active: int = 1
        self.broken: bool = False

    def token(self, move: Any) -> str:
        """Write one move as the notation writes it, and play it on.

        Args:
            move: The `Move` as it was played.

        Returns:
            str: The move in Standard Algebraic Notation, including any check or mate suffix
            the position after it earned. A replay that could no longer follow the game writes
            what the move itself carries and claims no hint and no suffix, because neither can
            be read from a position nobody has.
        """
        castle = _castle_of(move)
        if castle:
            written = castle
        else:
            piece = None if self.broken else self.board.get_piece_at(move.start_pos)
            piece = piece if piece is not None else move.piece
            # A move with no piece behind it at all — a fragment quoted out of a game, where the
            # replay could not follow it — is written as its destination alone. There is nothing
            # to say a letter with, and inventing one would put a piece in the record that the
            # position does not hold.
            letter = "" if piece is None or _is_pawn(piece) else _letter_of(piece)
            capture = self._takes(move)
            if letter:
                hint = "" if self.broken else self._disambiguation(piece, move)
                written = f"{letter}{hint}"
            elif capture:
                written = file_letter(move.start_pos[1])
            else:
                written = ""
            written = f"{written}{CAPTURE_MARK if capture else ''}{pos_to_algebraic(move.end_pos)}"
            if move.promotion_piece is not None:
                written = f"{written}={_letter_of(move.promotion_piece)}"

        if self.broken:
            return written
        self._play(move)
        return f"{written}{self._suffix()}"

    def tokens(self) -> List[str]:
        """Write every move, playing each one as it is read.

        Returns:
            List[str]: One token per move, in the order they were played.
        """
        return [self.token(move) for move in self.moves]

    # --- reading the position the move was played in

    def _legal_destinations(self, square: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Return the squares a piece may legally reach from where it stands.

        Legality and not geometry, because that is what the notation asks about: a knight that
        is pinned cannot be told apart from one that is not, because it may not move, so the
        knight beside it is written without a hint.

        Args:
            square: The (row, col) square the piece stands on.

        Returns:
            List[Tuple[int, int]]: Every square a legal move from there ends on.
        """
        self.validator.set_rules(self.rules, active_color=self.active, attach=False)
        return list(self.validator.get_valid_moves(square, self.board))

    def _disambiguation(self, piece: Any, move: Any) -> str:
        """Return the letter or rank that says which piece moved, or nothing.

        SAN prefers the file, then the rank, and only names both when neither alone says it. A
        hint is written only when some other piece of the same kind and colour can *legally*
        reach the same square; a piece that merely could have, but is pinned or is the king,
        does not make the mover ambiguous.

        Args:
            piece: The piece that moved.
            move: The `Move` being written.

        Returns:
            str: The file letter, the rank digit, both, or an empty string when the piece is
            the only one that could have gone there.
        """
        kind = piece.getType() if piece is not None else None
        colour = piece.getColor() if piece is not None else None
        destination = tuple(move.end_pos)
        rivals = [
            square
            for square, occupant in self._occupants()
            if occupant is not piece
            and occupant.getType() == kind
            and occupant.getColor() == colour
            and destination in self._legal_destinations(square)
        ]
        if not rivals:
            return ""
        if all(rival[1] != move.start_pos[1] for rival in rivals):
            return file_letter(move.start_pos[1])
        if all(rival[0] != move.start_pos[0] for rival in rivals):
            return str(move.start_pos[0] + 1)
        return f"{file_letter(move.start_pos[1])}{move.start_pos[0] + 1}"

    def _occupants(self) -> List[Tuple[Tuple[int, int], Any]]:
        """Return every piece standing on the board and where it stands.

        Returns:
            List[Tuple[Tuple[int, int], Any]]: (square, piece) pairs in board order.
        """
        found: List[Tuple[Tuple[int, int], Any]] = []
        for row in range(self.board.rows):
            for col in range(self.board.cols):
                piece = self.board.get_piece_at((row, col))
                if piece is not None:
                    found.append(((row, col), piece))
        return found

    def _takes(self, move: Any) -> bool:
        """Report whether this move takes something.

        Three sources, because three different kinds of move take something and no one of them
        is enough: the piece the move recorded, the square a taken piece stood on when it was not
        the destination, and whatever is on the destination in the position being read.

        Args:
            move: The `Move` being written.

        Returns:
            bool: True when the move takes a piece.
        """
        if move.captured_piece is not None or move.capture_from is not None:
            return True
        return self.board.get_piece_at(move.end_pos) is not None

    # --- reading the position the move produced

    def _play(self, move: Any) -> None:
        """Play one move on the replay board and tell this replay's rules about it.

        The rules are notified with the mover still to move, and the turn is handed on
        afterwards, which is the order `GameManager.make_move` uses and the order the castling
        rule and the two-square-advance rule both expect.

        Args:
            move: The `Move` as it was played.

        Returns:
            None
        """
        replayed = _replay_of(move)
        if replayed.apply_to_board(self.board) is None:
            # Nothing stands on the square the move claims to leave, so this is not a move of
            # this game's opening and nothing after it can be read either.
            self.broken = True
            return
        for rule in self.rules:
            rule.active_color = self.active
            rule.on_move_made(self.board, replayed)
        self.active = -self.active

    def _suffix(self) -> str:
        """Return `+` for a check and `#` for a mate, or nothing at all.

        A side that is not attacked has neither, whatever else is true of the position: a side
        with no legal move and no royal piece to attack is a stalemate, and the notation says
        nothing about one.

        Returns:
            str: `+`, `#`, or an empty string.
        """
        if self.broken or not self.validator.is_check(self.active, self.board):
            return ""
        return "+" if self.validator.get_all_valid_moves(self.active, self.board) else "#"


class ExportPGN(ExportWriter):
    """Writes a game's moves and its header as PGN text.

    Attributes:
        rules: This writer's own copy of the rules in force, composed once and borrowed by
            every replay it reads a game through. See `__init__` for why once is enough.
    """

    def __init__(self) -> None:
        """Compose this writer's own rule set, once.

        **Why once, and what makes that safe.** A rule set holds the history of the game it has
        watched — which colours have castled, whose two-square advance may be taken, which
        positions a repetition has seen — so a replay cannot be given the rules in force and
        must have its own. Composing them per call is what it used to do, and every game written
        paid for thirteen rules to answer questions about castling rights and check that a
        freshly composed set answers identically. What actually has to be fresh is the *state*,
        not the objects, and `Rule.reset` is the call that makes a rule set indistinguishable
        from a newly composed one: it clears the state dict before seeding it, which is what
        `GameManager.new_game` relies on for exactly the same reason.

        **The invalidation is the writer itself.** A writer is composed by the configuration
        that offers it, so it is built once per configuration load and thrown away with it.
        Saving a rule file loads the configuration again, which purges its modules and builds
        new writers with new rules — so this set cannot outlive the files it was composed from,
        and no cache of its own is needed to know that.

        The imports are inside the constructor for the same reason `Replay`'s are: this module
        is what started the composition of `export/`, and `export/` is composed before `rules/`
        is.
        """
        from ..rules import build_rules

        self.rules: List[Any] = build_rules()

    def formats(self) -> Tuple[str, ...]:
        """Return the notations this writer writes.

        Returns:
            Tuple[str, ...]: The one notation this writer writes. A writer declares exactly
            what it can produce, which is how the manager tells a game that cannot write this
            notation from one that had nothing to write.
        """
        return ("PGN",)

    def to_pgn(
        self,
        moves: List[Any],
        metadata: Optional[ExportMetadata] = None,
        players: Optional[List[Any]] = None,
        result: Any = None,
        date: Optional[datetime] = None,
        position: Optional[Any] = None,
    ) -> str:
        """Export game moves and metadata to Portable Game Notation (PGN) text.

        The movetext is Standard Algebraic Notation, which means it is read off a replay of the
        game rather than off the moves: a hint that says which knight moved, and a suffix that
        says what the move did to check, are both questions about a position.

        Args:
            moves: List of played Move instances. Replayed from `position`, which is where the
                game began — handed over by the manager, and this configuration's own starting
                position when no caller supplies one.
            metadata: The header writer the configuration declared. Optional, so the writer
                can be handed a game and nothing else — in which case a header is derived from
                that game rather than being left out.
            players: The players the game was played by, which is where the header's two names
                come from.
            result: The game's outcome, which is where the header's result comes from.
            date: When the game began, which is where the header's date comes from.
            position: The position the moves were played from, for a game that began somewhere
                other than this configuration's starting position. Defaults to None, which
                deals that starting position.

        Returns:
            str: The PGN text: the header, a blank line, and the moves.
        """
        header = metadata if metadata is not None else ExportMetadata()
        tags = header.header_values(players=players, result=result, date=date)
        headers = header.format_tags(tags)
        tokens = Replay(list(moves or []), position, self.rules).tokens()
        move_pairs = []
        for i in range(0, len(tokens), 2):
            move_num = (i // 2) + 1
            if i + 1 < len(tokens):
                move_pairs.append(f"{move_num}. {tokens[i]} {tokens[i + 1]}")
            else:
                move_pairs.append(f"{move_num}. {tokens[i]}")

        moves_text = " ".join(move_pairs)
        return f"{headers}\n\n{moves_text} {tags['Result']}".strip()

    def export(self, format_type: str, **kwargs: Any) -> str:
        """Write the game as PGN text.

        Args:
            format_type: The notation asked for, in the caller's own spelling. The manager
                looks a writer up without regard to case, so this writer compares the same
                way rather than expecting one exact string.
            **kwargs: Any: `moves`, and optionally `metadata`, `players`, `result`, `date` and
                `opening_position` — the position the game began in, which the manager hands
                every writer because a notation cannot work it out from the board.

        Returns:
            str: The game as PGN text.

        Raises:
            UnsupportedExportFormat: If the notation asked for is not one this writer writes.
                A writer writes the notations it declares and answers no others: the empty
                string this replaces was indistinguishable from a game with nothing to say.
        """
        if not self._writes(format_type):
            raise UnsupportedExportFormat(
                f"{format_type!r} is not a notation this writer writes; it writes "
                f"{', '.join(self.formats())}"
            )
        return self.to_pgn(
            kwargs.get("moves", []),
            kwargs.get("metadata"),
            kwargs.get("players"),
            kwargs.get("result"),
            kwargs.get("date"),
            kwargs.get("opening_position"),
        )


def _is_pawn(piece: Any) -> bool:
    """Report whether this piece is the one the notation names by its destination alone.

    Args:
        piece: The piece that moved.

    Returns:
        bool: True when the piece declares the pawn kind.
    """
    return piece is not None and piece.getType() == PAWN_KIND


def _letter_of(piece: Any) -> str:
    """Return the letter this piece is written as in a position record, in upper case.

    The letter is the piece's own, read from the character it declares, so a piece that
    declares one this repository has never heard of is written as itself and a writer with no
    piece table cannot fall out of step with one.

    Args:
        piece: The piece being written.

    Returns:
        str: Its letter in upper case.

    Raises:
        ValueError: If the piece declares no character. A piece that has not said how it is
            written cannot be written, and writing it as something else would put a false name
            into the record where nothing could reveal it.
    """
    get_fen = getattr(piece, "getFen", None)
    letter = get_fen() if callable(get_fen) else None
    if not letter:
        raise ValueError(
            f"a piece of type {getattr(piece, 'getType', lambda: None)()!r} declares no "
            "character for a position record, so it cannot be written in a transcript"
        )
    return str(letter).upper()


def _castle_of(move: Any) -> str:
    """Return what this move is written as if it is a castle, or an empty string.

    The rook's own square decides which castle it is, because the engine's move type for a
    castle names the move and not the side. The name of the move type is the fallback, for a
    hand-built move that carries no companion rook, and the king's own direction is the last
    resort for a move that carries neither.

    Args:
        move: The `Move` being written.

    Returns:
        str: `O-O`, `O-O-O`, or an empty string when the move is not a castle.
    """
    if not str(move.move_type).startswith("castling"):
        return ""
    rook_from = move.companion_start
    if rook_from is not None:
        return SHORT_CASTLE if rook_from[1] > move.end_pos[1] else LONG_CASTLE
    if "queen" in move.move_type:
        return LONG_CASTLE
    if "king" in move.move_type:
        return SHORT_CASTLE
    return SHORT_CASTLE if move.end_pos[1] > move.start_pos[1] else LONG_CASTLE
