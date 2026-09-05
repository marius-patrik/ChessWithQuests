"""Base piece module defining the foundational Piece abstraction for chess."""

from typing import Any, List, Optional, Tuple


class Piece:
    """Base class for all chess pieces.

    Attributes:
        _type: The piece type descriptor (e.g. "pawn", "king", 1, -1).
        _vectors: List of relative coordinate move offsets (row_delta, col_delta).
        _attack_vectors: List of relative coordinate attack offsets.
        _can_jump: Boolean indicating whether piece can leap over other pieces.
        _name: Human-readable display name of the piece.
    """

    def __init__(
        self,
        color: Any,
        piece_type: Any,
        vectors: Optional[List[Tuple[int, int]]] = None,
        attack_vectors: Optional[List[Tuple[int, int]]] = None,
        can_jump: bool = False,
        name: Optional[str] = None,
    ):
        """Initialize a new chess piece.

        Args:
            color: Color identifier (1 for White, -1 for Black).
            piece_type: Piece identifier or type descriptor.
            vectors: Optional movement vectors.
            attack_vectors: Optional attack vectors (defaults to vectors if None).
            can_jump: Whether this piece can jump over other pieces.
            name: Optional display name for the piece.
        """
        self.__color = color
        self._type = piece_type
        self._vectors = vectors
        self._attack_vectors = attack_vectors
        self._can_jump = can_jump
        self._name = name or (str(piece_type) if piece_type is not None else "Piece")

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


if __name__ == "__main__":
    piece = Piece(1, False)
    print(piece.getDirections())
    print(piece.getColor())
