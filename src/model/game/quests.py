"""The built-in quests.

Twenty quest types, each a subclass of `Quest` carrying its own logic — the same shape as
the rules, and the same reason: a quest is behaviour, so a subclass is the honest way to
express it and a condition object would only have moved the behaviour somewhere else.

Fourteen watch the game a move at a time (`after_move`) and six judge the finished game
(`at_game_end`). None of them names a chess piece. Anything game-specific — which piece
type a capture must be, which kind of piece may be the only one that moves — arrives as a
parameter, so the same quest serves chess and a game that has never been heard of. The two
quests that cannot be built without such an answer are absent from the roster `build_quests()`
returns, for the same reason: the engine cannot answer them and must not pretend to.

They live here rather than in `games/<variant>/quests/` because they are generic and fully
parameterised; a configuration instantiates them, and a game needing something these do
not cover writes one more subclass.
"""

from typing import Any, List, Optional, Sequence, Tuple

from model.game.events import OUTCOME_DRAW, OUTCOME_LOSS, OUTCOME_WIN, MoveEvent, ResultEvent
from model.game.field import Field
from model.game.quest import WHEN_AFTER_MOVE, WHEN_AT_GAME_END, Quest

ANY_COLOR = 0


def _color_field(default: int = ANY_COLOR) -> Field:
    """Declare a colour parameter.

    Args:
        default: Colour the parameter starts at. `ANY_COLOR` means either side.

    Returns:
        Field: The declaration, a choice between either side, White and Black.
    """
    return Field(
        "color",
        "choice",
        "Colour",
        default,
        choices=[ANY_COLOR, 1, -1],
        help="0 means either side.",
    )


class _AfterMoveQuest(Quest):
    """Base for the quests that watch a game move by move."""

    when = WHEN_AFTER_MOVE

    def __init__(self, color: int = ANY_COLOR, **kwargs: Any):
        """Create a quest that watches moves.

        Args:
            color: Colour the quest is for. `ANY_COLOR` means either side.
            kwargs: Passed to `Quest`: `name`, `description`, `reward`, `enabled`.
        """
        super().__init__(**kwargs)
        self.color = color

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The colour parameter followed by the parent's own.
        """
        return [_color_field(self.color), *super().parameters()]

    def _is_mine(self, event: MoveEvent) -> bool:
        """Report whether a move belongs to the quest's colour.

        Args:
            event: The move that was played.

        Returns:
            bool: True when the quest's colour is `ANY_COLOR` or matches the mover.
        """
        return self.color == ANY_COLOR or event.color == self.color


class FirstBlood(_AfterMoveQuest):
    """Capture at least one piece."""

    default_name = "First blood"
    default_description = "Capture at least one piece."

    def observe_move(self, event: MoveEvent) -> None:
        """Record the move if it was a capture.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if event.is_capture and self._is_mine(event):
            self._advance(target=1)


class CaptureN(_AfterMoveQuest):
    """Capture at least `count` pieces."""

    default_name = "Capture"
    default_description = "Capture at least the required number of pieces."

    def __init__(self, count: int = 1, **kwargs: Any):
        """Create a capture-count quest.

        Args:
            count: How many pieces must be captured.
            kwargs: Passed to `_AfterMoveQuest`.

        Raises:
            ValueError: If `count` is below one.
        """
        if count < 1:
            raise ValueError("a capture count cannot be below one")
        super().__init__(**kwargs)
        self.count = count
        self._target = count

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The colour, then the count, then the parent's own.
        """
        return [
            _color_field(self.color),
            Field("count", "integer", "Captures required", self.count, minimum=1),
            *super().parameters()[1:],
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Record the move if it was a capture.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if event.is_capture and self._is_mine(event):
            self._advance()


class CaptureOfType(_AfterMoveQuest):
    """Capture at least `count` pieces of one named piece type."""

    default_name = "Hunting a kind"
    default_description = "Capture pieces of one particular kind."

    def __init__(self, piece_type: str, count: int = 1, **kwargs: Any):
        """Create a capture-a-kind quest.

        Args:
            piece_type: The piece type descriptor that must be captured. The configuration
                supplies it; the engine never assumes one.
            count: How many of that piece must be captured.
            kwargs: Passed to `_AfterMoveQuest`.

        Raises:
            ValueError: If `piece_type` is empty or `count` is below one.
        """
        if not piece_type:
            raise ValueError("a capture-of-type quest must name the piece type to capture")
        if count < 1:
            raise ValueError("a capture count cannot be below one")
        super().__init__(**kwargs)
        self.piece_type = piece_type
        self.count = count
        self._target = count

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The piece type, the colour, the count, then the parent's own.
        """
        return [
            Field("piece_type", "text", "Piece type", self.piece_type),
            _color_field(self.color),
            Field("count", "integer", "Captures required", self.count, minimum=1),
            *super().parameters()[1:],
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Record the move if it captured the named kind.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if event.captured_piece_type == self.piece_type and self._is_mine(event):
            self._advance()


class MovePieceNTimes(_AfterMoveQuest):
    """Move one named piece type at least `count` times."""

    default_name = "On the move"
    default_description = "Move one kind of piece the required number of times."

    def __init__(self, count: int = 1, piece_type: Optional[str] = None, **kwargs: Any):
        """Create a move-count quest.

        Args:
            count: How many times the piece must move.
            piece_type: The piece type that must move, or None for any piece.
            kwargs: Passed to `_AfterMoveQuest`.

        Raises:
            ValueError: If `count` is below one.
        """
        if count < 1:
            raise ValueError("a move count cannot be below one")
        super().__init__(**kwargs)
        self.count = count
        self.piece_type = piece_type
        self._target = count

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The count, the piece type, then the parent's own.
        """
        return [
            Field("count", "integer", "Moves required", self.count, minimum=1),
            Field(
                "piece_type", "text", "Piece type", self.piece_type or "", help="Empty means any."
            ),
            _color_field(self.color),
            *super().parameters()[1:],
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Record the move when the right kind of piece moved.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if not self._is_mine(event):
            return
        if self.piece_type is None or event.piece_type == self.piece_type:
            self._advance()


class ReachedSquare(_AfterMoveQuest):
    """Land a piece on one named square."""

    default_name = "Destination"
    default_description = "Get a piece to the required square."

    def __init__(self, square: Tuple[int, int], **kwargs: Any):
        """Create a destination quest.

        Args:
            square: The (row, col) coordinates that must be reached.
            kwargs: Passed to `_AfterMoveQuest`.

        Raises:
            ValueError: If `square` is not a pair of integers.
        """
        if len(tuple(square)) != 2:
            raise ValueError("a square must be given as (row, col)")
        super().__init__(**kwargs)
        self.square = (int(square[0]), int(square[1]))
        self._target = 1

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The two coordinates, then the parent's own.
        """
        return [
            Field("square_row", "integer", "Row", self.square[0], minimum=0),
            Field("square_col", "integer", "File", self.square[1], minimum=0),
            _color_field(self.color),
            *super().parameters()[1:],
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Record the move when it ended on the named square.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if self._is_mine(event) and event.end == self.square:
            self._advance(target=1)


class VisitNSquares(_AfterMoveQuest):
    """Occupy at least `count` different squares over the game."""

    default_name = "Explore"
    default_description = "Visit the required number of different squares."

    def __init__(self, count: int = 1, **kwargs: Any):
        """Create an exploration quest.

        Args:
            count: How many distinct squares must be occupied.
            kwargs: Passed to `_AfterMoveQuest`.

        Raises:
            ValueError: If `count` is below one.
        """
        if count < 1:
            raise ValueError("a square count cannot be below one")
        super().__init__(**kwargs)
        self.count = count
        self._target = count
        self._visited = set()

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The count, then the colour, then the parent's own.
        """
        return [
            Field("count", "integer", "Squares required", self.count, minimum=1),
            _color_field(self.color),
            *super().parameters()[1:],
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Record the square the piece landed on.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if not self._is_mine(event):
            return
        self._visited.add(event.end)
        self._current = len(self._visited)

    def reset(self) -> None:
        """Clear this quest's progress so it can be played again in a new game.

        Returns:
            None
        """
        super().reset()
        self._visited = set()


class SurvivePlies(_AfterMoveQuest):
    """Make at least `count` of your own moves."""

    default_name = "Hold out"
    default_description = "Keep playing for the required number of your own moves."

    def __init__(self, count: int = 1, **kwargs: Any):
        """Create a survival quest.

        Args:
            count: How many of the quest's own moves must be made.
            kwargs: Passed to `_AfterMoveQuest`.

        Raises:
            ValueError: If `count` is below one.
        """
        if count < 1:
            raise ValueError("a ply count cannot be below one")
        super().__init__(**kwargs)
        self.count = count
        self._target = count

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The count, then the colour, then the parent's own.
        """
        return [
            Field("count", "integer", "Moves required", self.count, minimum=1),
            _color_field(self.color),
            *super().parameters()[1:],
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Record the move if it was the quest's colour.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if self._is_mine(event):
            self._advance(target=self.count)


class SurviveWithoutCapture(_AfterMoveQuest):
    """Make at least `count` of your own moves without capturing anything."""

    default_name = "Untouchable"
    default_description = "Play the required number of your moves without capturing anything."

    def __init__(self, count: int = 1, **kwargs: Any):
        """Create a quiet-move quest.

        Args:
            count: How many of the quest's own moves must be made without a capture.
            kwargs: Passed to `_AfterMoveQuest`.

        Raises:
            ValueError: If `count` is below one.
        """
        if count < 1:
            raise ValueError("a ply count cannot be below one")
        super().__init__(**kwargs)
        self.count = count
        self._target = count

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The count, then the colour, then the parent's own.
        """
        return [
            Field("count", "integer", "Moves required", self.count, minimum=1),
            _color_field(self.color),
            *super().parameters()[1:],
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Record the move when nothing was taken on it.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if self._is_mine(event) and not event.is_capture:
            self._advance(target=self.count)


class CastleN(_AfterMoveQuest):
    """Castle at least `count` times."""

    default_name = "Castling"
    default_description = "Castle the required number of times."

    def __init__(self, count: int = 1, **kwargs: Any):
        """Create a castling quest.

        Args:
            count: How many times castling must be played.
            kwargs: Passed to `_AfterMoveQuest`.

        Raises:
            ValueError: If `count` is below one.
        """
        if count < 1:
            raise ValueError("a castling count cannot be below one")
        super().__init__(**kwargs)
        self.count = count
        self._target = count

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The count, then the colour, then the parent's own.
        """
        return [
            Field("count", "integer", "Castles required", self.count, minimum=1),
            _color_field(self.color),
            *super().parameters()[1:],
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Record the move if it was a castle.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if event.is_castling and self._is_mine(event):
            self._advance()


class PromoteN(_AfterMoveQuest):
    """Promote at least `count` pieces."""

    default_name = "Promotion"
    default_description = "Promote the required number of pieces."

    def __init__(self, count: int = 1, **kwargs: Any):
        """Create a promotion quest.

        Args:
            count: How many promotions must be made.
            kwargs: Passed to `_AfterMoveQuest`.

        Raises:
            ValueError: If `count` is below one.
        """
        if count < 1:
            raise ValueError("a promotion count cannot be below one")
        super().__init__(**kwargs)
        self.count = count
        self._target = count

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The count, then the colour, then the parent's own.
        """
        return [
            Field("count", "integer", "Promotions required", self.count, minimum=1),
            _color_field(self.color),
            *super().parameters()[1:],
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Record the move if it promoted a piece.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if event.is_promotion and self._is_mine(event):
            self._advance()


class EnPassantN(_AfterMoveQuest):
    """Capture en passant at least `count` times."""

    default_name = "En passant"
    default_description = "Capture en passant the required number of times."

    def __init__(self, count: int = 1, **kwargs: Any):
        """Create an en passant quest.

        Args:
            count: How many en passant captures must be made.
            kwargs: Passed to `_AfterMoveQuest`.

        Raises:
            ValueError: If `count` is below one.
        """
        if count < 1:
            raise ValueError("an en passant count cannot be below one")
        super().__init__(**kwargs)
        self.count = count
        self._target = count

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The count, then the colour, then the parent's own.
        """
        return [
            Field("count", "integer", "En passant captures required", self.count, minimum=1),
            _color_field(self.color),
            *super().parameters()[1:],
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Record the move if it captured en passant.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if event.is_en_passant and self._is_mine(event):
            self._advance()


class MakeCheckN(_AfterMoveQuest):
    """Give check at least `count` times."""

    default_name = "Pressure"
    default_description = "Give check the required number of times."

    def __init__(self, count: int = 1, **kwargs: Any):
        """Create a check quest.

        Args:
            count: How many times check must be given.
            kwargs: Passed to `_AfterMoveQuest`.

        Raises:
            ValueError: If `count` is below one.
        """
        if count < 1:
            raise ValueError("a check count cannot be below one")
        super().__init__(**kwargs)
        self.count = count
        self._target = count

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The count, then the colour, then the parent's own.
        """
        return [
            Field("count", "integer", "Checks required", self.count, minimum=1),
            _color_field(self.color),
            *super().parameters()[1:],
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Record the move if it gave check.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if event.is_check and self._is_mine(event):
            self._advance()


class _AtGameEndQuest(Quest):
    """Base for the quests that judge a finished game."""

    when = WHEN_AT_GAME_END

    def __init__(self, **kwargs: Any):
        """Create a quest that judges the finished game.

        Args:
            kwargs: Passed to `Quest`.
        """
        super().__init__(**kwargs)
        self.event: Optional[ResultEvent] = None

    def observe_move(self, event: MoveEvent) -> None:
        """Take note of a move while the game is still running.

        The parent records nothing. A quest that watches a game and judges it at the end
        overrides this.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        return None

    def observe_result(self, event: ResultEvent) -> None:
        """Judge the finished game.

        Args:
            event: The finished game.

        Returns:
            None
        """
        self.event = event
        self._judge(event)

    def _judge(self, event: ResultEvent) -> None:
        """Decide whether the finished game satisfies this quest.

        Args:
            event: The finished game.

        Returns:
            None
        """
        raise NotImplementedError


class NeverInCheck(_AtGameEndQuest):
    """Finish the game having never had one of your pieces in check.

    Judged when the game ends, not after each move: nothing before the last move can
    establish that check never happened, so a quest judged after a move would complete on
    the opening move and mean nothing.
    """

    default_name = "Untouched"
    default_description = "Never leave yourself in check."

    def __init__(self, color: int = ANY_COLOR, **kwargs: Any):
        """Create a never-in-check quest.

        Args:
            color: The colour that must stay out of check, or `ANY_COLOR` for both.
            kwargs: Passed to `_AtGameEndQuest`.
        """
        super().__init__(**kwargs)
        self.color = color
        self.breached = False

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The colour, then the parent's own.
        """
        return [_color_field(self.color), *super().parameters()]

    def observe_move(self, event: MoveEvent) -> None:
        """Record that the mover was in check.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        mine = self.color == ANY_COLOR or event.color == self.color
        if mine and event.in_check:
            self.breached = True

    def _judge(self, event: ResultEvent) -> None:
        """Complete the quest when check was never suffered.

        Args:
            event: The finished game.

        Returns:
            None
        """
        if not self.breached:
            self._complete()


class KingOnlyGame(_AtGameEndQuest):
    """Finish a game in which every piece that moved is of one named kind.

    Judged when the game ends, not after each move: nothing before the last move can
    establish that nothing else will move, so a quest judged after a move would complete on
    the opening move and mean nothing.
    """

    default_name = "Bare game"
    default_description = "Play a game using only one kind of piece."

    def __init__(self, royal_kind: str, **kwargs: Any):
        """Create a single-kind quest.

        Args:
            royal_kind: The piece type that is the only one allowed to move. The
                configuration supplies it; the engine never assumes one.
            kwargs: Passed to `_AtGameEndQuest`.

        Raises:
            ValueError: If `royal_kind` is empty.
        """
        if not royal_kind:
            raise ValueError("a single-kind quest must name the kind that may move")
        super().__init__(**kwargs)
        self.royal_kind = royal_kind
        self.used = set()

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The named kind, then the parent's own.
        """
        return [
            Field("royal_kind", "text", "Piece kind allowed to move", self.royal_kind),
            *super().parameters(),
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Record which kinds of piece have moved.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        if event.piece_type:
            self.used.add(event.piece_type)

    def _judge(self, event: ResultEvent) -> None:
        """Complete the quest when only the named kind ever moved.

        Args:
            event: The finished game.

        Returns:
            None
        """
        if self.used <= {self.royal_kind}:
            self._complete()


class GameResult(_AtGameEndQuest):
    """Finish with one named outcome."""

    default_name = "The right ending"
    default_description = "Finish the game with the required outcome."

    def __init__(self, outcome: str = OUTCOME_DRAW, **kwargs: Any):
        """Create an outcome quest.

        Args:
            outcome: One of `OUTCOME_WIN`, `OUTCOME_LOSS` or `OUTCOME_DRAW`.
            kwargs: Passed to `_AtGameEndQuest`.

        Raises:
            ValueError: If `outcome` is not one of the three kinds.
        """
        if outcome not in (OUTCOME_WIN, OUTCOME_LOSS, OUTCOME_DRAW):
            raise ValueError(f"unknown outcome {outcome!r}")
        super().__init__(**kwargs)
        self.outcome = outcome

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The outcome, then the parent's own.
        """
        return [
            Field(
                "outcome",
                "choice",
                "Outcome",
                self.outcome,
                choices=[OUTCOME_WIN, OUTCOME_LOSS, OUTCOME_DRAW],
            ),
            *super().parameters(),
        ]

    def _judge(self, event: ResultEvent) -> None:
        """Complete the quest when the outcome matches.

        Args:
            event: The finished game.

        Returns:
            None
        """
        if event.outcome == self.outcome:
            self._complete()


class WonBy(_AtGameEndQuest):
    """Be the winner."""

    default_name = "Victory"
    default_description = "Win the game."

    def __init__(self, color: int = 1, **kwargs: Any):
        """Create a victory quest.

        Args:
            color: The colour that must win.
            kwargs: Passed to `_AtGameEndQuest`.

        Raises:
            ValueError: If `color` is not a side.
        """
        if color not in (1, -1):
            raise ValueError("a winner must be one of the two sides")
        super().__init__(**kwargs)
        self.color = color

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The winning colour, then the parent's own.
        """
        return [
            Field("color", "choice", "Winning colour", self.color, choices=[1, -1]),
            *super().parameters(),
        ]

    def _judge(self, event: ResultEvent) -> None:
        """Complete the quest when the named colour won.

        Args:
            event: The finished game.

        Returns:
            None
        """
        if event.winner == self.color:
            self._complete()


class GameAtLeast(_AtGameEndQuest):
    """Play at least `count` moves."""

    default_name = "Long game"
    default_description = "Play at least the required number of moves."

    def __init__(self, count: int = 1, **kwargs: Any):
        """Create a length quest.

        Args:
            count: The shortest acceptable game, in moves.
            kwargs: Passed to `_AtGameEndQuest`.

        Raises:
            ValueError: If `count` is below one.
        """
        if count < 1:
            raise ValueError("a move count cannot be below one")
        super().__init__(**kwargs)
        self.count = count
        self._target = count

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The count, then the parent's own.
        """
        return [
            Field("count", "integer", "Moves required", self.count, minimum=1),
            *super().parameters(),
        ]

    def _judge(self, event: ResultEvent) -> None:
        """Complete the quest when the game was long enough.

        Args:
            event: The finished game.

        Returns:
            None
        """
        self._advance(amount=len(event.history), target=self.count)


class MaterialAhead(_AtGameEndQuest):
    """Finish ahead on pieces taken by the required margin."""

    default_name = "Material"
    default_description = "Finish ahead on pieces captured."

    def __init__(self, color: int = 1, margin: int = 1, **kwargs: Any):
        """Create a material quest.

        Args:
            color: The colour whose material is judged.
            margin: How many more pieces that colour must have taken.
            kwargs: Passed to `_AtGameEndQuest`.

        Raises:
            ValueError: If `color` is not a side or `margin` is below one.
        """
        if color not in (1, -1):
            raise ValueError("a material quest must name one of the two sides")
        if margin < 1:
            raise ValueError("a material margin cannot be below one")
        super().__init__(**kwargs)
        self.color = color
        self.margin = margin
        self._target = margin

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The colour, the margin, then the parent's own.
        """
        return [
            Field("color", "choice", "Colour", self.color, choices=[1, -1]),
            Field("margin", "integer", "Captures ahead", self.margin, minimum=1),
            *super().parameters(),
        ]

    def _judge(self, event: ResultEvent) -> None:
        """Complete the quest when the colour finished ahead by the margin.

        Args:
            event: The finished game.

        Returns:
            None
        """
        taken = event.captures_by(self.color)
        lost = event.captures_against(self.color)
        # Ahead, not merely unequal. `abs(taken - lost)` completed this quest for a player
        # three pieces *down*, which is the opposite of what it asks for.
        self._advance(amount=taken - lost, target=self.margin)


class Pacifist(_AtGameEndQuest):
    """Finish the game without a single capture."""

    default_name = "Pacifist"
    default_description = "Finish the game without capturing anything."

    def __init__(self, color: int = ANY_COLOR, **kwargs: Any):
        """Create a no-capture quest.

        Args:
            color: The colour that must not capture, or `ANY_COLOR` for nobody.
            kwargs: Passed to `_AtGameEndQuest`.
        """
        super().__init__(**kwargs)
        self.color = color

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The colour, then the parent's own.
        """
        return [_color_field(self.color), *super().parameters()]

    def _judge(self, event: ResultEvent) -> None:
        """Complete the quest when nobody captured anything.

        Args:
            event: The finished game.

        Returns:
            None
        """
        if self.color == ANY_COLOR:
            quiet = not any(item.is_capture for item in event.history)
        else:
            quiet = event.captures_by(self.color) == 0
        if quiet:
            self._complete()


class CompositeQuest(_AtGameEndQuest):
    """Complete when a set of other quests is satisfied."""

    default_name = "Combined"
    default_description = "Complete when the combined quests are satisfied."

    def __init__(self, quests: Sequence[Quest], mode: str = "all", **kwargs: Any):
        """Create a composite quest.

        Args:
            quests: The quests to combine.
            mode: `all` to require every quest, `any` to require one.
            kwargs: Passed to `_AtGameEndQuest`.

        Raises:
            ValueError: If `quests` is empty or `mode` is neither `all` nor `any`.
        """
        if not quests:
            raise ValueError("a composite quest needs at least one quest to combine")
        if mode not in ("all", "any"):
            raise ValueError("a composite mode must be 'all' or 'any'")
        super().__init__(**kwargs)
        self.quests = list(quests)
        self.mode = mode

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: The combination mode, then the parent's own.
        """
        return [
            Field("mode", "choice", "Require", self.mode, choices=["all", "any"]),
            *super().parameters(),
        ]

    def observe_move(self, event: MoveEvent) -> None:
        """Pass the move on to every combined quest.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        for quest in self.quests:
            quest.observe_move(event)

    def _judge(self, event: ResultEvent) -> None:
        """Complete the quest when the combined quests are satisfied.

        A member that watches moves a move at a time is given the whole history first, so a
        composite can combine an `after_move` quest with an `at_game_end` one without the
        caller having to replay anything.

        Args:
            event: The finished game.

        Returns:
            None
        """
        # A member that watches moves a move at a time was already given every move as it was
        # played, by `observe_move` above. Replaying the history here counted each of them a
        # second time, so three captures reached a member's target of three and doubled every
        # count besides. Only the end-of-game members are told now.
        for quest in self.quests:
            if getattr(quest, "when", None) != WHEN_AFTER_MOVE:
                quest.observe_result(event)

        satisfied = [quest.validate() for quest in self.quests]
        self._current = sum(1 for value in satisfied if value)
        self._target = len(self.quests) if self.mode == "all" else 1
        if (self.mode == "all" and all(satisfied)) or (self.mode == "any" and any(satisfied)):
            self._complete()


#: Every built-in quest, so a configuration can offer them all without naming them.
BUILT_IN_QUESTS = (
    FirstBlood,
    CaptureN,
    CaptureOfType,
    MovePieceNTimes,
    ReachedSquare,
    VisitNSquares,
    SurvivePlies,
    SurviveWithoutCapture,
    CastleN,
    PromoteN,
    EnPassantN,
    MakeCheckN,
    NeverInCheck,
    KingOnlyGame,
    GameResult,
    WonBy,
    GameAtLeast,
    MaterialAhead,
    Pacifist,
    CompositeQuest,
)


def build_quests() -> List[Quest]:
    """Build one instance of every built-in quest that needs no game-specific answer.

    The roster is written out here rather than discovered, for the same reason the chess
    rules are: the set of quests in play is a decision someone made, and a decision that can
    be read in one place is one that can be argued with. A quest class not named here is
    available to a configuration but is not in play.

    Three classes are deliberately absent, and each for its own reason.

    - `CompositeQuest` is the mechanism for building a quest out of other quests rather than
      a quest in its own right.
    - `CaptureOfType` and `KingOnlyGame` cannot be listed at all: both insist on naming a
      piece type, and which piece type is a question only a configuration can answer. The
      engine naming `"queen"` or `"king"` here is the engine holding chess, which is what
      this module's docstring says it does not do. A configuration that wants them supplies
      them: `games/chess/__init__.py` names both, with its own piece names.

    Returns:
        List[Quest]: The seventeen built-in quests, in roster order. The seventeen are every
        roster member that a configuration can play without first answering a question about
        its own pieces.
    """
    return [
        FirstBlood(),
        CaptureN(),
        MovePieceNTimes(),
        ReachedSquare((0, 0)),
        VisitNSquares(),
        SurvivePlies(),
        SurviveWithoutCapture(),
        CastleN(),
        PromoteN(),
        EnPassantN(),
        MakeCheckN(),
        NeverInCheck(),
        Pacifist(),
        MaterialAhead(),
        GameAtLeast(),
        GameResult(),
        WonBy(),
    ]
