"""Immobilisation: a side that cannot move has lost, and so has one with nothing left.

English draughts has no royal piece and nothing can be put in check, so there is no mate to
detect. What ends a game is a side with no move at all: either it has no pieces left to move,
or every piece it has is walled in behind its own. Both are the same question — can this side
move? — and one rule asks it.

Which makes this rule the one that says a game of draughts is not a chess game underneath.
The engine's own state constants call a side with no legal move a stalemate, and the view
labels that state "the game is drawn". Here it is a loss, and the outcome this rule proposes
is the one the quests and the finished game are judged by. Which is exactly why it is a rule
and not a branch in the engine.
"""

from typing import Any, List, Optional

from model.game.field import Field
from model.game.rule import KIND_WIN, Result, Rule
from .geometric import opponent

#: Precedence of this proposal, so two rules firing at once is deterministic.
IMMOBILE_PRECEDENCE = 100


class ImmobilisationRule(Rule):
    """End the game in a win for the other side when this side cannot move at all."""

    default_name = "Immobilisation"

    def value_fields(self) -> List[Field]:
        """Declare the configured values this rule plays by.

        Returns:
            List[Field]: None. The rule needs no configuration; it asks the rules in force
            whether anybody can move.
        """
        return []

    def outcome(self, position: Any) -> Optional[Result]:
        """Propose a win for the other side when the player to move is stuck.

        The rules in force are the ones that decide the answer, not this rule's own reading
        of the board: a side is stuck when no legal move exists, and what a legal move is
        depends on every other rule, including whether a capture is compulsory.

        Args:
            position: The board as it stands.

        Returns:
            Optional[Result]: A win for the other side, or None when the player to move can
            still move.
        """
        colour = self.active_color
        if has_legal_move(position, colour, self.rules):
            return None
        return Result(
            KIND_WIN,
            precedence=IMMOBILE_PRECEDENCE,
            winner=opponent(colour),
            reason="immobilised",
        )


def has_legal_move(position: Any, color: int, rules: Any) -> bool:
    """Report whether a colour has any legal move at all.

    Args:
        position: The board to read.
        color: The colour whose turn it is.
        rules: The rules in force.

    Returns:
        bool: True when at least one legal move exists for that colour.
    """
    from model.game.validator import MoveValidator

    # Composed without being attached. Attaching is what a game does when it starts, and
    # attaching again here would wipe the history those rules built in the game being asked
    # about — how many plies the fifty-move rule has counted, for one.
    validator = MoveValidator(position)
    validator.set_rules(rules, attach=False)
    return bool(validator.get_all_valid_moves(color, position))
