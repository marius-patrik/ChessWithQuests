"""Miscellaneous utilities package: the writer protocol, and the quest manager.

The metadata writer is not here. It was, for as long as the manager built it, and it left
because its defaults are the seven-tag roster with `White`, `Black` and `Round` and its one
writing method was `format_pgn_headers()` — which is a format rather than a mechanism. It is
`games/chess/export/metadata.py` now, beside the writers that compose their headers from it,
and `Configuration.metadata` is how a configuration supplies one.
"""
