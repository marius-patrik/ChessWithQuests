"""The application entry point.

`python -m chesswithquests` starts the application. This module owns the process: it
parses the command line, opens the window and runs the event loop. Everything it shows is
built by `view/`, and the rules it plays are the ones the selected configuration declares.
"""

import argparse
import sys
from typing import Any, List, Optional

from model.game.games import DEFAULT_GAME, available_games, configuration_path, games_root

__all__ = ["main", "build_window", "offered_formats", "report_installation"]

APPLICATION_TITLE = "ChessWithQuests"


def build_arguments(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse the command line.

    `--check` is what makes the entry point verifiable without a display: it reports what
    the installation can find and exits, so continuous integration can exercise the whole
    startup path on a machine with no window server.

    Args:
        argv: Argument list to parse. Defaults to `sys.argv[1:]`.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        prog="chesswithquests",
        description="Play a board game from a configuration.",
    )
    parser.add_argument(
        "--game",
        default=DEFAULT_GAME,
        help="name of the configuration to play (default: %(default)s)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "report what this installation can find, including the notations each "
            "configuration offers, then exit without opening a window"
        ),
    )
    return parser.parse_args(argv)


def offered_formats(name: str) -> str:
    """Describe the notations one shipped configuration can write.

    Which notations a game has is the configuration's own answer, so a report that named the
    directories but not their notations would say nothing about the part of the installation a
    player notices when a game refuses an export. Each configuration is asked what it offers,
    and a configuration that cannot be loaded says so here rather than taking the whole report
    down with it — this is a diagnostic, and its value is largest exactly when something is
    broken.

    Args:
        name: The configuration's directory name.

    Returns:
        str: The declared format names in the order the configuration declares them, or a
        message saying why they could not be asked for.
    """
    from model.game.configuration import load_configuration

    try:
        configuration = load_configuration(name)
    except Exception as error:
        return f"could not be loaded ({error})"
    offered: List[str] = []
    for writer in configuration.exporters:
        for declared in writer.formats():
            if declared not in offered:
                offered.append(str(declared))
    return ", ".join(offered) if offered else "(exports nothing)"


def report_installation() -> str:
    """Describe what this installation can find.

    Returns:
        str: A report naming the located `games/` directory, every shipped configuration, and
        the notations each of them offers.
    """
    games = available_games()
    lines = [
        f"{APPLICATION_TITLE} {_version()}",
        f"games directory: {games_root()}",
        f"configurations: {', '.join(games) if games else '(none found)'}",
    ]
    lines.extend(f"  {name} exports: {offered_formats(name)}" for name in games)
    return "\n".join(lines)


def _version() -> str:
    """Return the installed distribution version, or `unknown` when running uninstalled.

    Returns:
        str: The distribution version string.
    """
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover - Python 3.7 and older
        return "unknown"
    try:
        return version("chesswithquests")
    except PackageNotFoundError:
        return "unknown"


def build_window(root: Any, game: str = DEFAULT_GAME):
    """Populate a Tk root with the application window.

    Args:
        root: The `tkinter.Tk` instance to build into.
        game: Name of the configuration to start.

    Returns:
        tkinter.Toplevel or the root: The window the game is shown in.
    """
    from view.app import build_application

    return build_application(root, game)


def main(argv: Optional[List[str]] = None) -> int:
    """Start the application.

    Args:
        argv: Argument list to parse. Defaults to `sys.argv[1:]`.

    Returns:
        int: The process exit code. Zero on a clean exit, non-zero on failure.

    Raises:
        SystemExit: Never raised by this function; the exit code is returned instead so a
            caller can drive it from a test.
    """
    args = build_arguments(argv)

    if args.check:
        print(report_installation())
        return 0

    try:
        configuration_path(args.game)
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 4

    try:
        import tkinter as tk
    except ImportError as error:  # pragma: no cover - depends on the interpreter build
        print(f"tkinter is unavailable: {error}", file=sys.stderr)
        return 2

    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(f"cannot open a window: {error}", file=sys.stderr)
        return 3

    try:
        window = build_window(root, args.game)
    except Exception as error:
        root.destroy()
        print(f"cannot start {args.game!r}: {error}", file=sys.stderr)
        return 4

    window.mainloop()
    return 0
