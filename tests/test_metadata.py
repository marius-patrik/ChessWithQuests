import pytest
from model.misc.metadata import MetadataWriter


def test_metadata_writer_defaults():
    mw = MetadataWriter()
    assert mw.get_header("Event") == "Chess Match"
    assert mw.get_header("Result") == "*"
    headers_text = mw.format_pgn_headers()
    assert '[Event "Chess Match"]' in headers_text
    assert '[Result "*"]' in headers_text


def test_metadata_writer_custom_headers():
    mw = MetadataWriter({"Event": "World Championship", "White": "Magnus", "Black": "Hikaru"})
    assert mw.get_header("White") == "Magnus"
    mw.set_header("Result", "1-0")
    assert mw.get_header("Result") == "1-0"
    assert '[Result "1-0"]' in mw.format_pgn_headers()
    exported = mw.export()
    assert exported["White"] == "Magnus"
    assert exported["Result"] == "1-0"
