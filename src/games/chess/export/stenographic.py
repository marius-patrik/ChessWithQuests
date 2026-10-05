"""The chess coordinate record, written by a writer that belongs to chess.

The stenographic record is a coordinate pair per move — the squares each move starts on and
ends on, in chess's own algebraic naming. The naming is chess's, so it is imported relatively
from `algebraic.py` beside this file: an absolute `games.chess.…` import would load the
original's naming when this directory is copied into a variant, which is exactly the failure
`tests/test_configuration_copying.py` exists to catch.

The public name of the notation is `Stenographic`, in that spelling. It used to be declared
`"Stenographic"` and dispatched as `"STENOGRAPHIC"`, so the two disagreed and the dispatch was
a second, private spelling of a name callers could already see. This writer declares one
spelling and answers the notation however the caller spells it — `GameManager.writer_for`
matches without regard to case, and `tests/test_game_loop.py` asks for `Stenographic` by name.

## What the owner wrote about the compression, and what was read out of it

There are three sentences about this and none of them is a grammar. The diagram's operation
compartment annotates the format *"(Standard or custom compression)"*
(`notes/reference_diagram.md`). `PRD.md` FR-49 says *"with compression that is either a standard
choice or a configured one, drawn from the standard library codecs only"*. `SCRATCHPAD.md` §7
PR 19 says *"with standard or configured compression from the standard library codecs"*. That
is the whole of the specification, and it is worth being plain that it is thin: it names the
requirement and the source of the compression, and says nothing about which codec, nothing about
the bytes, and nothing about how a record is read back.

What it does settle, and what is therefore implemented:

- **The compression is a standard library codec and not a scheme written here.** No run-length
  scheme, no dictionary of this game's own squares, no invented packing. `STANDARD_CODECS` is
  the standard library's own compression modules and nothing else.
- **The choice is a standard one by default and a configured one when asked.** `zlib` is the
  standard choice; a writer may be built with another, and `export` may be handed one per call.
  Both halves of "either a standard choice or a configured one", which is what that phrase is
  for.
- **The compressed bytes are written as text.** A writer returns a `str` because `GameManager.
  save_log` writes one to a file and every other writer in this directory returns one; raw
  compressed bytes are not that. Base85 is the standard library's own text rendering of bytes
  and it costs a quarter rather than the third that base64 costs, so it is what is used.

What is not settled by the three sentences, and is decided here and recorded: the record carries
the name of the codec that produced it, so a record says how to read itself back rather than
requiring the reader to know which codec the writer happened to be configured with. Everything
after the first colon is the base85 of the compressed record, and `from_stenographic` is the
inverse — a record nobody can read back is not a transcript, and the diagram's *game transcript*
(`FR-50`) is a format of its own beside this one.

The coordinate pairs themselves are untouched: a record of one move is still `e2e4`, because
the squares are the record and the compression is a container around it.
"""

import base64
import zlib
from typing import Any, Callable, Dict, List, Tuple

from model.game.manager import UnsupportedExportFormat
from model.misc.export_writers import ExportWriter

from .algebraic import pos_to_algebraic

#: The codecs a record may be compressed with, and what each is called in a record. Standard
#: library compression modules only, and named as the modules are named. `zlib` is first because
#: it is the one that is everywhere, and the default is the first of them.
STANDARD_CODECS: Dict[str, str] = {"zlib": "zlib", "gzip": "gzip", "bz2": "bz2", "lzma": "lzma"}

#: What a record says when it has been compressed with the standard choice.
DEFAULT_CODEC = "zlib"

#: What separates the codec's name from the bytes it produced.
SEPARATOR = ":"


def _codec(name: str) -> Tuple[Callable[[bytes], bytes], Callable[[bytes], bytes]]:
    """Return the compressing and decompressing halves of one standard library codec.

    The modules are imported here rather than at module level so that a codec nobody has chosen
    costs nothing until it is chosen — `lzma` in particular is the slowest import in the standard
    library's compression set — and so that the roster above is the single place a codec is
    named.

    Args:
        name: The codec's name, as `STANDARD_CODECS` spells it.

    Returns:
        Tuple[Callable[[bytes], bytes], Callable[[bytes], bytes]]: The compressing and the
        decompressing function.

    Raises:
        ValueError: If the codec is not one of the standard library's. A record compressed by a
            scheme this writer cannot name is a record this writer cannot read, and a caller
            that names one is told so rather than given an uncompressed record that looks like
            a compressed one.
    """
    module = STANDARD_CODECS.get(str(name).strip().lower())
    if module is None:
        raise ValueError(
            f"{name!r} is not a compression codec from the standard library; this writer "
            f"writes {', '.join(sorted(STANDARD_CODECS))}"
        )
    if module == "zlib":
        return zlib.compress, zlib.decompress
    if module == "gzip":
        import gzip

        return gzip.compress, gzip.decompress
    if module == "bz2":
        import bz2

        return bz2.compress, bz2.decompress
    import lzma

    return lzma.compress, lzma.decompress


class ExportStenographic(ExportWriter):
    """Writes a game's moves as a compressed record of coordinate pairs."""

    def __init__(self, codec: str = DEFAULT_CODEC):
        """Choose the codec a record is compressed with.

        The choice is checked here rather than at write time, because a configuration that
        named a codec this writer cannot read should hear about it when the configuration loads
        rather than when a player saves a game for the first time.

        Args:
            codec: The codec's name, as `STANDARD_CODECS` spells it. Defaults to `zlib`, the
                standard choice; a configuration that prefers another names it here.

        Raises:
            ValueError: If the codec is not one of the standard library's.
        """
        self.codec: str = str(codec).strip().lower()
        _codec(self.codec)

    def formats(self) -> Tuple[str, ...]:
        """Return the notations this writer writes.

        Returns:
            Tuple[str, ...]: The one notation this writer writes. A writer declares exactly
            what it can produce, which is how the manager tells a game that cannot write this
            notation from one that had nothing to write.
        """
        return ("Stenographic",)

    def to_stenographic(self, moves: List[Any], codec: str = "") -> str:
        """Write a list of moves as a compressed record of coordinate pairs.

        Args:
            moves: List of Move instances with start_pos and end_pos.
            codec: The codec to compress with, overriding the one this writer was built with.
                Defaults to an empty string, which is the writer's own.

        Returns:
            str: The record: the codec's name, a colon, and the compressed coordinate pairs
            rendered as text.

        Raises:
            ValueError: If the codec is not one of the standard library's.
        """
        chosen = str(codec).strip().lower() or self.codec
        compress, _decompress = _codec(chosen)
        plain = " ".join(
            f"{pos_to_algebraic(m.start_pos)}{pos_to_algebraic(m.end_pos)}" for m in moves or []
        )
        return f"{chosen}{SEPARATOR}{base64.b85encode(compress(plain.encode('utf-8'))).decode('ascii')}"

    def from_stenographic(self, record: str) -> str:
        """Read a record back into its coordinate pairs.

        Args:
            record: A record this writer wrote.

        Returns:
            str: The coordinate pairs, space-delimited, exactly as they were written before
            the compression.

        Raises:
            ValueError: If the record does not name a codec this writer knows. A record it
                cannot read is refused rather than returned as though it had been read.
        """
        text = str(record)
        name, separator, payload = text.partition(SEPARATOR)
        if not separator:
            raise ValueError(
                "this is not a compressed coordinate record: it names no compression, so "
                "there is nothing to undo"
            )
        _compress, decompress = _codec(name)
        return decompress(base64.b85decode(payload.encode("ascii"))).decode("utf-8")

    def export(self, format_type: str, **kwargs: Any) -> str:
        """Write the game as a coordinate record.

        Args:
            format_type: The notation asked for, in the caller's own spelling. The manager
                looks a writer up without regard to case, so this writer compares the same
                way rather than expecting one exact string.
            **kwargs: Any: `moves`, and optionally `codec`.

        Returns:
            str: The moves as a compressed record of coordinate pairs.

        Raises:
            UnsupportedExportFormat: If the notation asked for is not one this writer writes.
                A writer writes the notations it declares and answers no others: the empty
                string this replaces was indistinguishable from a game with nothing to say.
            ValueError: If the codec asked for is not one of the standard library's.
        """
        if not self._writes(format_type):
            raise UnsupportedExportFormat(
                f"{format_type!r} is not a notation this writer writes; it writes "
                f"{', '.join(self.formats())}"
            )
        return self.to_stenographic(kwargs.get("moves", []), kwargs.get("codec", ""))
