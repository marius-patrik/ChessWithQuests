"""Test session setup.

`properdocs` is a rename of `mkdocs`, and it makes third-party plugins work by installing an import
hook that redirects every `mkdocs.*` import to the matching `properdocs.*` module. The hook only
helps imports that happen *after* it is installed.

`mkdocstrings` depends on `mkdocs`, so if anything imports it before the hook is in place, its
plugin class subclasses the real `mkdocs.plugins.BasePlugin` and configuration then fails with
"must be a subclass of properdocs.plugins.BasePlugin". The command line never hits this because
`properdocs` installs the hook as it starts; a test session has no such guarantee, so it is
installed here, before any test module is imported.
"""

import tkinter as tk

import pytest

import properdocs.replacement  # noqa: F401  (imported for its import-hook side effect)


@pytest.fixture(scope="session")
def tk_root():
    """Yield one Tk root for the whole session.

    Destroying the last Tk root in a process tears down the Tcl interpreter, and building a new
    root afterwards segfaults rather than raising. So every test that needs a window uses this
    one root, and none of them destroys it. Where there is no display the fixture skips, so a
    headless run of the suite still works.

    Yields:
        tk.Tk: A withdrawn root, ready to build widgets into.
    """
    try:
        root = tk.Tk()
    except tk.TclError as error:  # pragma: no cover - depends on the machine
        pytest.skip(f"no display available: {error}")
    root.withdraw()
    yield root
