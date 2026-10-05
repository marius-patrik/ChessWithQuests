"""Base piece module defining the foundational Piece abstraction for chess."""

import re
from typing import Any, Dict, List, Optional, Tuple

from model.game.field import Field


def _vectors_from_text(text: str) -> Optional[List[Tuple[int, int]]]:
    """Return movement vectors parsed from the text a form shows them as.

    Empty means "as the piece already moves", which is how a blank field says the player wants
    nothing changed rather than nothing at all.

    Args:
        text: The field's text, for example `"(1, 2), (2, 1)"`.

    Returns:
        Optional[List[Tuple[int, int]]]: The pairs, or None for blank text.

    Raises:
        ValueError: If the text is not a list of `(row, col)` pairs.
    """
    stripped = str(text).strip()
    if not stripped:
        return None
    if "(" not in stripped and "," not in stripped:
        raise ValueError(f"{stripped} is not a list of (row, col) pairs")
    vectors: List[Tuple[int, int]] = []
    for part in re.findall(r"\(([^)]*)\)", stripped):
        pair = part.split(",")
        if len(pair) != 2:
            raise ValueError(f"({part}) is not a (row, col) pair")
        try:
            vectors.append((int(pair[0].strip()), int(pair[1].strip())))
        except ValueError:
            raise ValueError(f"({part}) is not a (row, col) pair") from None
    if not vectors:
        raise ValueError(f"{stripped} is not a list of (row, col) pairs")
    return vectors


def _vectors_as_text(vectors: Optional[List[Tuple[int, int]]]) -> str:
    """Return movement vectors as the text a form shows them as.

    Args:
        vectors: The offsets the piece may move by, or None for a piece that may move any
            distance along its own vectors.

    Returns:
        str: `"(1, 0), (-1, 0)"`, or "" for None.
    """
    if vectors is None:
        return ""
    return ", ".join(f"({row}, {col})" for row, col in vectors)


class Piece:
    """Base class for all chess pieces.

    Every piece is described by data: where it may go, where it may take, how far one step
    travels, and whether it may leap. Nothing about a piece is special-cased by the engine,
    which is what lets a configuration declare a piece the engine has never heard of.

    A piece also declares where it takes part in a game that is not about moving it: the
    character it is written as in a position record (`getFen`), and whether another piece may
    become this one (`promotion_target`). Both are read by a configuration's own rules and
    writers, and neither is read by the engine — the engine moves pieces and knows nothing
    about promotion.

    Attributes:
        _type: The piece type descriptor the configuration chose.
        _vectors: Offsets along which the piece may move (and, when they are not also
            attack vectors, may only move to an empty square).
        _attack_vectors: Offsets along which the piece may take. A vector that appears only
            here is a capture and nothing else.
        _can_jump: Whether the piece may leap over other pieces.
        _name: Human-readable display name of the piece.
        _max_steps: How far one step travels. None means the piece slides as far as the
            board allows, which is what a ray mover does.
        _initial_vectors: Extra offsets available only before the piece has moved, which is
            how a piece gets a one-off first advance.
        has_moved: Whether the piece has ever moved. Cleared on placement, set by the board
            on the first move.
    """

    #: Whether another piece may become this one. Declared on the piece rather than listed in
    #: a rule, so a piece written into a configuration's `pieces/` is a promotion target the
    #: moment it is in that configuration's catalogue — which is the whole of what it takes to
    #: promote to a piece of your own. A piece that is what promotes rather than what a
    #: promoting piece becomes declares this False, and so does a piece whose kind ends a game.
    promotion_target: bool = True

    def __init__(
        self,
        color: Any,
        piece_type: Any,
        vectors: Optional[List[Tuple[int, int]]] = None,
        attack_vectors: Optional[List[Tuple[int, int]]] = None,
        can_jump: bool = False,
        name: Optional[str] = None,
        max_steps: Optional[int] = None,
        initial_vectors: Optional[List[Tuple[int, int]]] = None,
        has_moved: bool = False,
        symbols: Optional[Tuple[str, str]] = None,
        fen: Optional[str] = None,
    ):
        """Initialize a piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece identifier or type descriptor.
            vectors: Offsets along which the piece may move.
            attack_vectors: Offsets along which the piece may take. Defaults to `vectors`,
                which means the piece takes wherever it moves.
            can_jump: Whether this piece can jump over other pieces.
            name: Optional display name for the piece.
            max_steps: How far one step travels. None means the piece slides as far as the
                board allows.
            initial_vectors: Extra offsets available only before the piece has moved.
            has_moved: Whether the piece has already moved. A newly placed piece has not,
                which is what makes a first-only advance available.
        """
        self.__color = color
        self._type = piece_type
        self._vectors = vectors
        self._attack_vectors = attack_vectors
        self._can_jump = can_jump
        self._name = name or (str(piece_type) if piece_type is not None else "Piece")
        self._max_steps = max_steps
        self._initial_vectors = initial_vectors or []
        self.has_moved = has_moved
        self._symbols = tuple(symbols) if symbols else None
        self._fen = fen

    def value_fields(self) -> List[Field]:
        """Declare what this piece is configured with.

        FR-3 lists what a piece declares and FR-32 makes each of those form-exposed from one
        declaration. A piece is data all the way down — the engine holds no table of piece
        types, so this declaration is the whole of what the form needs to know about it.

        Returns:
            List[Field]: The name, the two symbols, the movement and attack vectors, the jump
            flag, the kind and the optional FEN character. Movement vectors are declared as
            text because they are a list of pairs, and the form reads them as the player
            writes them; `Field` has no list kind and inventing one is a decision FR-32 does
            not need yet.
        """
        return [
            Field("name", "text", "Name", self._name),
            Field("white_symbol", "text", "White symbol", self._symbol_for(1)),
            Field("black_symbol", "text", "Black symbol", self._symbol_for(-1)),
            Field(
                "vectors",
                "text",
                "Movement vectors",
                _vectors_as_text(self._vectors),
                help="(row, col) pairs, comma separated; blank means any distance.",
            ),
            Field(
                "attack_vectors",
                "text",
                "Attack vectors",
                _vectors_as_text(self._attack_vectors),
                help="Blank means it takes wherever it moves.",
            ),
            Field("can_jump", "boolean", "May jump over pieces", self._can_jump),
            Field("kind", "text", "Kind", "" if self._type is None else str(self._type)),
            Field("fen", "text", "FEN character", self._fen or ""),
        ]

    def apply_values(self, values: Dict[str, Any]) -> None:
        """Write configured values onto this piece, parsing the ones declared as text.

        The form reads and writes a piece through `value_fields`, so this is the other half of
        that declaration. Two of the declared values are not single attributes — the two
        symbols are one pair, and the vectors are a list of pairs shown as text — so they are
        parsed here rather than in the view, which is what keeps the form a renderer and not a
        place where the meaning of a piece lives.

        Args:
            values: The declared field names and what the player chose. A name this piece does
                not declare is ignored, so an older form cannot set something newer.

        Returns:
            None

        Raises:
            ValueError: If a vector list is not a list of `(row, col)` pairs. A piece that
                cannot move is not a piece the player meant to write, and the alternative is a
                piece that silently cannot move at all.
        """
        if "name" in values:
            self._name = str(values["name"])
        if "white_symbol" in values or "black_symbol" in values:
            white = str(values.get("white_symbol", self._symbol_for(1)))
            black = str(values.get("black_symbol", self._symbol_for(-1)))
            self._symbols = (white, black)
        if "vectors" in values:
            self._vectors = _vectors_from_text(values["vectors"])
        if "attack_vectors" in values:
            self._attack_vectors = _vectors_from_text(values["attack_vectors"])
        if "can_jump" in values:
            self._can_jump = bool(values["can_jump"])
        if "kind" in values:
            self._type = str(values["kind"]) or None
        if "fen" in values:
            self._fen = str(values["fen"]) or None

    def _symbol_for(self, color: Any) -> str:
        """Return this piece's declared symbol for one side.

        Args:
            color: 1 for White, -1 for Black.

        Returns:
            str: The glyph, or "" when the piece declares none. The renderer falls back to the
            name, so a piece with no glyph is still playable and still visible.
        """
        if not self._symbols:
            return ""
        return self._symbols[0] if color == 1 else self._symbols[1]

    def getDirections(self) -> Optional[List[Tuple[int, int]]]:
        """Return the standard movement vectors for this piece.

        Returns:
            Optional[List[Tuple[int, int]]]: List of (row_offset, col_offset) tuples, or None.
        """
        return self._vectors

    def getAttackDirections(self) -> Optional[List[Tuple[int, int]]]:
        """Return the attack vectors for this piece.

        Returns:
            Optional[List[Tuple[int, int]]]: Attack movement vectors, defaulting to standard vectors.
        """
        if self._attack_vectors is not None:
            return self._attack_vectors
        return self._vectors

    def getMaxSteps(self) -> Optional[int]:
        """Return how far one step of this piece travels.

        Returns:
            Optional[int]: The step length, or None when the piece slides as far as the
            board allows.
        """
        return self._max_steps

    def getInitialVectors(self) -> List[Tuple[int, int]]:
        """Return the offsets available only before this piece has moved.

        Returns:
            List[Tuple[int, int]]: The one-off first-move offsets, empty when the piece has
            no first-move advance.
        """
        return list(self._initial_vectors)

    def getSymbol(self) -> Optional[str]:
        """Return the glyph this piece is drawn as.

        Returns:
            Optional[str]: The glyph for this piece's colour, or None when the configuration
            declared no symbol.
        """
        if not self._symbols:
            return None
        return self._symbols[0] if self.__color == 1 else self._symbols[1]

    def getFen(self) -> Optional[str]:
        """Return the character this piece is written as in a position record.

        Returns:
            Optional[str]: The character's letter, unsided and in lower case, or None when
            the piece takes no part in that notation. The colour is a matter of case, so
            the letter alone is what a piece needs to know.
        """
        return self._fen

    def hasMoved(self) -> bool:
        """Return whether this piece has already moved.

        Returns:
            bool: True once the piece has moved, False while it has not.
        """
        return self.has_moved

    def setMoved(self, moved: bool = True) -> None:
        """Record whether this piece has moved.

        Args:
            moved: The new state. Defaults to True.

        Returns:
            None
        """
        self.has_moved = moved

    def canJump(self) -> bool:
        """Check whether the piece can jump over other pieces.

        Returns:
            bool: True if jumping is enabled, False otherwise.
        """
        return self._can_jump

    def getColor(self) -> Any:
        """Return the piece's player color code.

        Returns:
            Any: Color representation (1 for White, -1 for Black).
        """
        return self.__color

    def getType(self) -> Any:
        """Return the piece's type descriptor.

        Returns:
            Any: Piece type identifier.
        """
        return self._type

    def getName(self) -> str:
        """Return the piece's human-readable name.

        Returns:
            str: Piece name.
        """
        return self._name


#: Czech alias for `Piece`, as `PRD.md` section 5 and `Figurka` in the diagram require.
Figurka = Piece
