"""Pawn promotion.

The far rank is derived from the piece's own declared forward vector rather than from the
number eight, so the rule works on a board of any size.

**What a pawn may become is this configuration's catalogue's answer.** The rule composes
`../pieces` once, when it is itself composed, and resolves every kind it is asked for there —
the same question `CrowningRule` asks in draughts, where `rules/geometric.py:crown` resolves what
a man becomes out of this configuration's own package rather than out of a list beside it. The
list that used to stand here, `PROMOTION_PIECES`, was a second hand-written catalogue: a piece
written into a copy's `pieces/` directory joined the catalogue and could not be promoted to,
because the rule never asked. Composition is relative, as everywhere else in a configuration, so
a copy promotes to the copy's own pieces.
"""

from typing import Any, Dict, List, Optional, Type

from model.game.field import Field
from model.game.move import Move
from model.game.rule import Rule


class PromotionRule(Rule):
    """Offer every choice of replacement piece, and insist on one.

    Attributes:
        catalogue: The piece kinds this configuration offers and the class behind each, composed
            out of `pieces/` when this rule is composed. A kind this configuration has no piece
            for cannot be promoted to, and saying so names the kinds it does offer.
    """

    default_name = "Promotion"

    def __init__(self, enabled: bool = True, **values: Any):
        """Assemble the rule, and take hold of the catalogue it promotes within.

        Args:
            enabled: Whether the rule is in force at all.
            **values: Configured values, one per declared field. Anything not supplied takes
                the field's default.

        Raises:
            ValueError: If a catalogue entry cannot be asked what kind it is. Every piece in
                this configuration's catalogue can be built with a colour — that is what a
                board does to place one — so one that refuses is a catalogue that cannot be
                used, and saying so beats silently promoting to a subset of it.
        """
        from ..pieces import build_pieces

        super().__init__(enabled=enabled, **values)
        self.catalogue: Dict[str, Type[Any]] = _catalogue_of(build_pieces())

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule is configured with.

        Returns:
            List[Field]: Which kinds promote, and which kinds a promotion may choose from. The
            second is text rather than a fixed set of choices on purpose: the kinds this
            configuration offers are composed out of `pieces/`, so a kind a player's own piece
            introduces has to be nameable here without a code edit — and blank means the
            catalogue's own answer rather than one choice of it.
        """
        return [
            Field(
                "promotable_kinds",
                "text",
                "Kinds that promote",
                "pawn",
            ),
            Field(
                "promotion_kinds",
                "text",
                "Promote to",
                "",
                help=(
                    "Comma separated. Blank means every kind this configuration's catalogue "
                    "offers that declares itself a promotion target."
                ),
            ),
        ]

    def promotion_row(self, position: Any, piece: Any) -> Optional[int]:
        """Return the row on which this piece promotes.

        Whether a piece promotes is declared, not inferred. A rook and a king both have a
        purely vertical step, so deriving the rank from geometry promoted every piece that
        could slide sideways on the far rank: no queen or rook could ever reach it, and a king
        walking its own back rank turned into a knight.

        Args:
            position: The board to read.
            piece: The piece asking.

        Returns:
            Optional[int]: The row a single-square forward step reaches, or None when this
            piece does not promote.
        """
        if not self._promotes(piece):
            return None
        origin = _origin(position, piece)
        if origin is None:
            return None
        for dr, dc in piece.getDirections() or []:
            if dc != 0 or dr == 0:
                continue
            return position.rows - 1 if dr > 0 else 0
        return None

    def _promotes(self, piece: Any) -> bool:
        """Report whether this piece is one that promotes.

        Args:
            piece: The piece asking.

        Returns:
            bool: True when the piece's kind is one of the declared promoting kinds.
        """
        configured = _split(self.value.get("promotable_kinds")) or ["pawn"]
        return piece is not None and piece.getType() in configured

    def available_moves(self, position: Any, piece: Any) -> List[Move]:
        """Offer one promoting move per choice of replacement piece.

        Args:
            position: The board to read.
            piece: The piece whose moves are being asked about.

        Returns:
            List[Move]: The promoting moves, or nothing when the piece is not promoting.
        """
        target_row = self.promotion_row(position, piece)
        if target_row is None:
            return []

        origin = _origin(position, piece)
        if origin is None:
            return []

        take_only = [
            vector
            for vector in (piece.getAttackDirections() or [])
            if vector not in (piece.getDirections() or [])
        ]
        destinations = []
        for dr, dc in piece.getDirections() or []:
            landing = (origin[0] + dr, origin[1] + dc)
            if position.is_within_bounds(*landing) and position.get_piece_at(landing) is None:
                destinations.append(landing)
        for dr, dc in take_only:
            landing = (origin[0] + dr, origin[1] + dc)
            if not position.is_within_bounds(*landing):
                continue
            target = position.get_piece_at(landing)
            if target is not None and target.getColor() != piece.getColor():
                destinations.append(landing)

        offered: List[Move] = []
        for destination in destinations:
            if destination[0] != target_row:
                continue
            for kind in self._kinds():
                offered.append(
                    Move(
                        start_pos=origin,
                        end_pos=destination,
                        piece=piece,
                        move_type="promotion",
                        promotion_piece=self._make_promotion(piece, kind),
                    )
                )
        return offered

    def permits_move(self, position: Any, move: Move) -> bool:
        """Refuse a move onto the far rank that has not chosen what it becomes.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            bool: False for an undecorated move onto the promotion rank, True otherwise.
        """
        if move.promotion_piece is not None:
            return True
        piece = move.piece or position.get_piece_at(move.start_pos)
        if piece is None:
            return True
        if self.promotion_row(position, piece) != move.end_pos[0]:
            return True
        return bool(self._kinds()) and move.move_type == "promotion"

    def _kinds(self) -> List[str]:
        """Return the kinds this rule may promote to, and where that answer comes from.

        **A declaration wins.** A configuration that names its choices gets exactly those, in
        the order it named them, and a name the catalogue has no piece for is refused by
        `promotion_piece` rather than quietly dropped — a declaration and a catalogue that
        disagree is a configuration whose author should hear about it.

        **A blank declaration asks the catalogue.** Every kind the catalogue offers that
        declares itself a promotion target is offered, which for this configuration is the four
        the rulebook allows and for a copy with a piece of its own is that piece as well. That
        is the whole of the difference from what this file used to hold: the kinds came from a
        dict written out here, so a piece written into `pieces/` joined the catalogue and could
        not be promoted to. **Whether a kind may be promoted to is declared by the piece** —
        `Piece.promotion_target`, False on the two kinds this configuration excludes, a pawn
        and a king — so the exclusion is a declaration rather than a name written into a rule.

        Returns:
            List[str]: The kinds offered, in the order they are offered. Empty only when the
            catalogue offers nothing that is a promotion target, which is a configuration with
            no promotion in it rather than a failure.
        """
        declared = _split(self.value.get("promotion_kinds"))
        if declared:
            return declared
        return [
            kind
            for kind, piece_class in self.catalogue.items()
            if getattr(piece_class, "promotion_target", True)
        ]

    def _make_promotion(self, piece: Any, kind: str) -> Any:
        """Build the replacement piece for a promotion, out of this configuration's catalogue.

        Args:
            piece: The piece promoting, whose colour the replacement takes.
            kind: The kind to promote to, as the declaration or the catalogue spells it.

        Returns:
            Any: A piece of that kind and colour, built from the catalogue so it belongs to the
            configuration being played.

        Raises:
            ValueError: If this configuration's catalogue has no piece of that kind. A
                promotion has to produce a piece, and guessing which would silently promote a
                pawn into something the configuration never offered.
        """
        piece_class = self.catalogue.get(kind)
        if piece_class is None:
            offered = ", ".join(sorted(self.catalogue)) or "nothing at all"
            raise ValueError(
                f"{kind!r} is not a piece kind this configuration offers; its catalogue "
                f"holds {offered}"
            )
        return piece_class(piece.getColor())


def _catalogue_of(catalogue: List[Type[Any]]) -> Dict[str, Type[Any]]:
    """Return the kinds a catalogue offers and the class behind each.

    A kind is read the way a board reads it — by building a piece and asking — because a piece
    declares its descriptor as data and a class attribute is not where it lives. Two classes
    reporting one kind is a configuration that cannot say which piece it means, so the first
    composed wins and the catalogue order is the order the section composed in.

    Args:
        catalogue: The piece classes a configuration offers.

    Returns:
        Dict[str, Type[Any]]: Kind descriptor to the class providing it, in catalogue order.

    Raises:
        ValueError: If a class cannot be built with a colour, so cannot be asked what kind it
            is.
    """
    kinds: Dict[str, Type[Any]] = {}
    for piece_class in catalogue:
        try:
            kind = piece_class(1).getType()
        except Exception as error:  # noqa: BLE001 - any failure here is the player's code
            raise ValueError(
                f"{piece_class.__name__} could not be asked what kind it is, so this "
                f"configuration cannot be promoted within: {type(error).__name__}: {error}"
            ) from error
        if kind is not None and str(kind) not in kinds:
            kinds[str(kind)] = piece_class
    return kinds


def _split(value: Any) -> List[str]:
    """Read a comma-separated configuration value as a list.

    Args:
        value: The configured value.

    Returns:
        List[str]: The entries, empty when nothing is configured.
    """
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if value:
        return [str(item) for item in value]
    return []


def _origin(position: Any, piece: Any) -> Optional[tuple]:
    """Find where a piece stands.

    Args:
        position: The board to read.
        piece: The piece to find.

    Returns:
        Optional[tuple]: Its square, or None when it is not on the board.
    """
    for r in range(position.rows):
        for c in range(position.cols):
            if position.get_piece_at((r, c)) is piece:
                return (r, c)
    return None
