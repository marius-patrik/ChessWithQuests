"""Base piece module defining the foundational Piece abstraction for chess."""

from typing import Any, List, Optional, Tuple


class Piece:
    """Base class for all chess pieces.

    Every piece is described by data: where it may go, where it may take, how far one step
    travels, and whether it may leap. Nothing about a piece is special-cased by the engine,
    which is what lets a configuration declare a piece the engine has never heard of.

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
