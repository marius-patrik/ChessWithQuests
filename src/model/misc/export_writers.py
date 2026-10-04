"""The export writer protocol: the whole of what the engine knows about writing a game.

`ExportWriter` names no game and no notation. Two methods are the protocol, and both are
duck-typed rather than inherited: a writer's `formats()` says which notations it writes, and
`export(format_type, **kwargs)` writes one of them. `GameManager.writer_for` and
`GameManager.transcript` match writers on exactly that and need nothing else, which is why
`tests/test_manager_exporters.py` can stand a writer of its own in front of the manager and
have the manager behave exactly as it does for a shipped game.

Which notations exist is a configuration's answer, so the writers live with the configuration
that uses them — `games/chess/export/` holds chess's, one file per notation. This module
therefore holds no writer and no notation name: a concrete writer here would be a game the
engine names, and `tests/test_engine_holds_no_chess.py` fails if one appears or if a module
under `model/` imports a configuration at all.

A piece's role in a written game is declared by the piece and nowhere else. A writer that
needs a piece to say how it is written asks the piece, and a piece that has declared nothing
has no place in the record — which is said out loud rather than guessed at.
"""

from typing import Any, Tuple


class ExportWriter:
    """Abstract base class for export writers.

    A writer is constructed by the configuration that offers it and is given nothing: no
    board, no moves, no header. Everything the game supplies arrives through `export`, which
    is what lets one protocol serve any number of notations.
    """

    def formats(self) -> Tuple[str, ...]:
        """Return the format names this writer writes.

        The engine holds no list of formats — which notations exist is the configuration's
        answer, and a writer is the only thing that knows what it can produce. Declaring them
        here is what lets `GameManager.transcript` tell "this configuration does not export
        that" from "this writer had nothing to write", which are different faults and used to
        be indistinguishable because both arrived as an empty string.

        Returns:
            Tuple[str, ...]: The format names, empty when this writer writes none.
        """
        return ()

    def _writes(self, format_type: str) -> bool:
        """Report whether this writer writes the notation asked for.

        The rule a writer obeys is that it writes the notations it declares and answers no
        others, and it compares them the way the manager does: without regard to case, and on
        the caller's own spelling. `GameManager.transcript` hands `export` whatever the caller
        typed and looks the writer up case-insensitively first, so a writer that compared
        exact strings would refuse a notation the manager had just agreed to write.

        Args:
            format_type: The notation asked for, in the caller's spelling.

        Returns:
            bool: True when the notation is one of this writer's declared names.
        """
        wanted = str(format_type).strip().lower()
        return any(wanted == str(name).strip().lower() for name in self.formats())

    def export(self, *args: Any, **kwargs: Any) -> str:
        """Export game data into the target serialization format.

        Args:
            *args: Variable positional arguments.
            **kwargs: Any: Variable keyword arguments.

        Returns:
            str: The serialized game in the format this writer produces.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError
