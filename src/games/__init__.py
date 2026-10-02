"""Shipped game configurations.

A configuration is a directory that can be copied. `cp -r games/chess games/house`,
change what differs, and a variant exists: duplication is the extension mechanism.

The engine in `model/`, `controller/` and `view/` holds no game logic. Everything that
makes one game different from another lives in a directory beside this package.
"""
