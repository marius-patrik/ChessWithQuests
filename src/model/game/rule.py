"""The rule parent class, and the outcome a rule may propose.

A rule is code the configuration brings with it, and it is the same pattern a quest uses:
a parent class, subclasses, composed explicitly by the configuration, never a registry. The
validator asks and rules answer — a rule may permit or forbid a move, never cause one, and
may propose an outcome, never impose one.
"""

from typing import Any, Dict, Iterable, List, Optional, Sequence

from model.game.events import OUTCOME_DRAW, OUTCOME_LOSS, OUTCOME_WIN
from model.game.field import Field

#: Outcome kinds, re-exported so a rule and a quest cannot drift apart on what a win is.
KIND_WIN = OUTCOME_WIN
KIND_LOSS = OUTCOME_LOSS
KIND_DRAW = OUTCOME_DRAW

#: The name under which a rule declares which piece kinds are royal.
ROYAL_KIND = "royal_kind"

#: The kinds that end a game for somebody. A draw never outranks one of these.
DECISIVE_KINDS = (KIND_WIN, KIND_LOSS)

#: All three kinds, most decisive first. The order is the tie-break order.
KIND_ORDER = (KIND_WIN, KIND_LOSS, KIND_DRAW)


class Result:
    """An outcome a rule proposes, and how strongly it proposes it.

    Attributes:
        kind: One of `KIND_WIN`, `KIND_LOSS` or `KIND_DRAW`.
        precedence: How strongly the rule proposes this outcome. Higher wins.
        winner: Colour of the winner, or None for a draw and for a loss.
        reason: Why, for the status line and the log.
    """

    def __init__(
        self,
        kind: str,
        precedence: int = 0,
        winner: Optional[int] = None,
        reason: str = "",
    ):
        """Propose an outcome.

        Args:
            kind: One of `KIND_WIN`, `KIND_LOSS` or `KIND_DRAW`.
            precedence: How strongly the rule proposes this outcome. Higher wins.
            winner: Colour of the winner, or None for a draw and for a loss.
            reason: Why, for the status line and the log.

        Raises:
            ValueError: If `kind` is not one of the three.
        """
        if kind not in KIND_ORDER:
            raise ValueError(
                f"unknown outcome kind {kind!r}; expected one of {', '.join(KIND_ORDER)}"
            )
        self.kind = kind
        self.precedence = precedence
        self.winner = winner
        self.reason = reason

    @property
    def is_decisive(self) -> bool:
        """Whether this outcome names a winner.

        Returns:
            bool: True for a win or a loss, False for a draw.
        """
        return self.kind in DECISIVE_KINDS

    def __eq__(self, other: object) -> bool:
        """Compare two proposals field by field.

        Args:
            other: The object to compare against.

        Returns:
            bool: True when both describe the same outcome.
        """
        if not isinstance(other, Result):
            return NotImplemented
        return (self.kind, self.precedence, self.winner, self.reason) == (
            other.kind,
            other.precedence,
            other.winner,
            other.reason,
        )

    def __hash__(self) -> int:
        """Return a hash consistent with equality.

        Returns:
            int: The hash of the outcome's fields.
        """
        return hash((self.kind, self.precedence, self.winner, self.reason))

    def __repr__(self) -> str:
        """Return a debugging representation naming the outcome.

        Returns:
            str: The kind, precedence and winner.
        """
        return f"Result(kind={self.kind!r}, precedence={self.precedence!r}, winner={self.winner!r})"


def resolve_outcomes(proposals: Sequence[Result]) -> Optional[Result]:
    """Choose the outcome a set of rules proposes.

    A decisive proposal always outranks a draw, whatever its precedence, because a rule that
    says somebody has won is not overruled by one that says nobody has lost. Among proposals
    of the same decisiveness the highest precedence wins, and equal precedence resolves by
    the order the rules were declared in.

    Args:
        proposals: The proposals, in declaration order.

    Returns:
        Optional[Result]: The outcome that wins, or None when nothing was proposed.
    """
    if not proposals:
        return None
    decisive = [proposal for proposal in proposals if proposal.is_decisive]
    pool = decisive if decisive else list(proposals)
    return max(pool, key=lambda proposal: proposal.precedence)


class Rule:
    """One piece of game logic a configuration brings with it.

    Five hooks, each defaulting permissively, so a rule states only what it changes. Four
    are exhaustive for turn-based logic, which can only forbid a move or end a game;
    `status` is display, reporting something worth showing while the game continues.

    Attributes:
        enabled: Whether the rule is in force at all.
        value: The configured values. Persisted.
        state: The runtime values. Reset each game, and never persisted.
        rules: The set this rule belongs to, so a rule can consult its siblings.
        clock: The game's clock, when the game provides one. A rule about time needs it
            and a rule about the board does not.
        active_color: Whose turn it is, which a rule cannot work out from a board alone.
    """

    #: Name used in configuration errors and the settings form.
    default_name = "Rule"

    def __init__(self, enabled: bool = True, **values: Any):
        """Create a rule.

        Args:
            enabled: Whether the rule is in force at all.
            **values: Configured values, one per declared field. Anything not supplied takes
                the field's default.
        """
        self.enabled = enabled
        self.label = self.default_name
        self.value: Dict[str, Any] = {}
        self.state: Dict[str, Any] = {}
        self.rules: List["Rule"] = []
        self.clock: Any = None
        self.active_color = 1
        for field in self.value_fields():
            self.value[field.name] = values.get(field.name, field.default)

    def __getattr__(self, name: str) -> Any:
        """Read a configured value as though it were an attribute.

        `value` is the single source of truth for what a rule is configured with, so that
        persisting a configuration cannot disagree with what the rule does. Storing a
        second copy on the instance would let the two drift, which is a bug waiting for a
        settings screen to walk into.

        Args:
            name: The attribute being read.

        Returns:
            Any: The configured value.

        Raises:
            AttributeError: If the rule declares no such configured value.
        """
        value = self.__dict__.get("value")
        if isinstance(value, dict) and name in value:
            return value[name]
        raise AttributeError(name)

    def value_fields(self) -> List[Field]:
        """Declare the values this rule is configured with.

        Returns:
            List[Field]: One declaration per configured value. The parent declares none, so
            a rule that needs nothing configured overrides nothing.
        """
        return []

    def parameters(self) -> List[Field]:
        """Declare everything the player may configure about this rule.

        Returns:
            List[Field]: `enabled`, which the framework adds, followed by the rule's own.
        """
        return [
            Field("enabled", "boolean", "Enabled", self.enabled),
            *self.value_fields(),
        ]

    def permits_move(self, position: Any, move: Any) -> bool:
        """Report whether this rule allows a move.

        Args:
            position: The board the move would be played on.
            move: The move being considered.

        Returns:
            bool: True by default. A rule that forbids a move returns False and nothing
            else; it never alters the move.
        """
        return True

    def available_moves(self, position: Any, piece: Any) -> Iterable[Any]:
        """Report additional moves this rule offers for a piece.

        Args:
            position: The board the move would be played on.
            piece: The piece whose moves are being asked about.

        Returns:
            Iterable[Any]: Nothing by default. A rule offering a move the piece's own
            vectors cannot express returns it here.
        """
        return ()

    def outcome(self, position: Any) -> Optional[Result]:
        """Propose an outcome for the current position.

        Args:
            position: The board as it stands.

        Returns:
            Optional[Result]: None by default. A rule proposes; it never imposes.
        """
        return None

    def on_move_made(self, position: Any, move: Any) -> None:
        """Take note of a move that has been played.

        Args:
            position: The board as it stands after the move.
            move: The move that was played.

        Returns:
            None
        """
        return None

    def status(self, position: Any) -> Optional[str]:
        """Report something worth showing while the game continues.

        Args:
            position: The board as it stands.

        Returns:
            Optional[str]: None by default. A rule that has something to say returns it, for
            example `Check`.
        """
        return None

    def royal_kind(self) -> Optional[str]:
        """Return the piece kind this rule set declares royal.

        Exactly one rule declares it — a rule carrying a configured value called
        `royal_kind` — and every other rule asks the set rather than declaring it again. A
        set with no such declaration has no royal piece, which is a game nobody has heard
        of rather than an error.

        Returns:
            Optional[str]: The declared kind, or None when nothing is declared.
        """
        for rule in self.rules:
            kind = rule.value.get(ROYAL_KIND)
            if kind:
                return kind
        return None

    def attach(self) -> None:
        """Take hold of the game this rule has joined.

        Wiring, not behaviour: it is called once when a rule set enters a game, so a rule
        that needs the clock or its siblings can find them. The default does nothing.

        Returns:
            None
        """
        return None

    def reset(self) -> None:
        """Clear this rule's runtime state for a new game.

        Returns:
            None
        """
        self.state = {}
        self.attach()

    def persisted_values(self) -> Dict[str, Any]:
        """Return the values that may be written to disk.

        Returns:
            Dict[str, Any]: `enabled` and the configured values. The runtime state is
            deliberately absent, so saving a configuration cannot save a game's history.
        """
        return {"enabled": self.enabled, **self.value}

    def __repr__(self) -> str:
        """Return a debugging representation naming the rule.

        Returns:
            str: The rule name and whether it is in force.
        """
        return f"{type(self).__name__}(enabled={self.enabled})"
