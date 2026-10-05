"""A clock's declared fields, so a clock is configurable through one form like everything else.

A clock declares its own fields through `value_fields()` when it has any, and this module is what
the Clocks section asks first: the parent pattern is the rule, the parent class is where a hook
like this belongs, and a clock must not be the exception that makes the settings surface bespoke
in one place. `model/game/clock.py` is that parent — a clock is an initial time, an increment and
the countdown they run on, and `clocks/` is composed out of the files that declare one.

`Clock` itself declares no fields, and this module is still what describes both shipped clocks.
A clock does not have to be a `Clock` subclass to be configurable: it is enough that it holds an
initial time and an increment, which is exactly what `PRD.md` FR-6 says a clock declares, and
asking what the object holds is what keeps that true of a clock written in a variant.
"""

from typing import Any, List

from model.game.field import Field

#: How long a clock may be configured to run, in seconds, either way. A clock set to nothing
#: is not a slow game, it is a game nobody has finished.
MIN_SECONDS = 0

#: The longest a clock may be configured to run. Long enough for any game anyone plays and
#: short enough that a mistyped number is caught in the form rather than played through.
MAX_SECONDS = 86_400


def clock_fields(clock: Any) -> List[Field]:
    """Return what a clock is configured with.

    A clock that declares its own fields declares them; the parent pattern is the rule, the
    parent class is where a hook like this belongs, and a clock must not be the exception that
    makes the settings surface bespoke in one place.

    Args:
        clock: The clock to describe.

    Returns:
        List[Field]: One declaration per configurable value: the initial time and the
        increment, in seconds. Empty for a clock that holds neither, which is a clock whose
        time control is decided elsewhere.
    """
    declared = getattr(clock, "value_fields", None)
    if callable(declared):
        try:
            fields = declared()
        except Exception:  # noqa: BLE001 - a clock that cannot describe itself declares none
            fields = None
        if isinstance(fields, list):
            return fields

    fields = []
    if hasattr(clock, "initial_seconds"):
        fields.append(
            Field(
                "initial_seconds",
                "integer",
                "Initial time (s)",
                int(getattr(clock, "initial_seconds", 0)),
                minimum=MIN_SECONDS,
                maximum=MAX_SECONDS,
            )
        )
    if hasattr(clock, "increment_seconds"):
        fields.append(
            Field(
                "increment_seconds",
                "integer",
                "Increment (s)",
                int(getattr(clock, "increment_seconds", 0)),
                minimum=MIN_SECONDS,
                maximum=MAX_SECONDS,
            )
        )
    return fields


def apply_clock_values(clock: Any, values: dict) -> None:
    """Write configured values onto a clock, and rebuild what depends on them.

    A clock's initial time is held twice: on the clock, and on the `Timer` it holds. Setting
    only the clock's own attribute leaves the countdown running from the old value, so both
    are written and the countdown is reset — otherwise the form would appear to save and the
    next game would start at the time the player rejected.

    Args:
        clock: The clock to configure.
        values: The declared field names and what the player chose.

    Returns:
        None
    """
    for name, value in values.items():
        if not hasattr(clock, name):
            continue
        setattr(clock, name, int(value))
    timer = getattr(clock, "timer", None)
    if timer is None:
        return
    initial = getattr(clock, "initial_seconds", None)
    if initial is not None and hasattr(timer, "initial_time"):
        timer.initial_time = int(initial)
    reset = getattr(clock, "reset", None)
    if callable(reset):
        reset()
