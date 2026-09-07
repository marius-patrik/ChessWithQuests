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

import properdocs.replacement  # noqa: F401  (imported for its import-hook side effect)
