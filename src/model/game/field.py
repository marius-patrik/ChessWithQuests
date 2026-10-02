"""Declarative field descriptions.

Every configurable type declares what it can be configured with, and one renderer turns
that declaration into widgets. `Field` is that declaration: it is data, so a new setting
costs a field rather than a bespoke form.
"""

from typing import Any, List, Optional, Sequence

#: Field kinds the one renderer knows how to draw.
KINDS = (
    "text",
    "integer",
    "decimal",
    "boolean",
    "choice",
    "position",
    "multiline",
)


class Field:
    """One configurable value of one type.

    Attributes:
        name: The attribute name the value is read from and written to.
        kind: The field kind, one of `KINDS`, which decides the widget.
        label: Human-readable label.
        default: The value used when nothing has been configured.
        choices: Permitted values, for the `choice` kind.
        minimum: Lowest permitted value, for the numeric kinds.
        maximum: Highest permitted value, for the numeric kinds.
        help: One line of guidance shown beneath the widget.
    """

    def __init__(
        self,
        name: str,
        kind: str,
        label: str,
        default: Any = None,
        choices: Optional[Sequence[Any]] = None,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
        help: str = "",
    ):
        """Describe one configurable value.

        Args:
            name: Attribute name the value is read from and written to.
            kind: Field kind, one of `KINDS`, which decides the widget.
            label: Human-readable label.
            default: Value used when nothing has been configured.
            choices: Permitted values, for the `choice` kind.
            minimum: Lowest permitted value, for the numeric kinds.
            maximum: Highest permitted value, for the numeric kinds.
            help: One line of guidance shown beneath the widget.

        Raises:
            ValueError: If `kind` is not one this renderer knows.
        """
        if kind not in KINDS:
            raise ValueError(f"unknown field kind {kind!r}; expected one of {', '.join(KINDS)}")
        self.name = name
        self.kind = kind
        self.label = label
        self.default = default
        self.choices = list(choices) if choices is not None else None
        self.minimum = minimum
        self.maximum = maximum
        self.help = help

    def validate(self, value: Any) -> bool:
        """Report whether a value is permitted for this field.

        Args:
            value: The value to check.

        Returns:
            bool: True when the value satisfies the field's kind and bounds.
        """
        if self.kind == "boolean":
            return isinstance(value, bool)
        if self.kind in ("integer", "decimal"):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return False
            if self.kind == "integer" and not isinstance(value, int):
                return False
            if self.minimum is not None and value < self.minimum:
                return False
            return not (self.maximum is not None and value > self.maximum)
        if self.kind == "choice":
            return self.choices is not None and value in self.choices
        return isinstance(value, str)

    def __repr__(self) -> str:
        """Return a debugging representation naming the field.

        Returns:
            str: The field name, kind and default.
        """
        return f"Field(name={self.name!r}, kind={self.kind!r}, default={self.default!r})"


def field_values(spec: List[Field], source: Any) -> List[Any]:
    """Read every declared field's value off an object.

    Args:
        spec: The declared fields.
        source: The object carrying the values.

    Returns:
        List[Any]: One value per declared field, in declaration order, falling back to the
        field's default when the object has no such attribute.
    """
    return [getattr(source, field.name, field.default) for field in spec]
