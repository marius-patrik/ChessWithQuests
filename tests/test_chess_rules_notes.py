import os
import pytest


def test_chess_rules_reference_exists_and_complete():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rules_file = os.path.join(repo_root, ".agents", "notes", "chess_rules.md")

    assert os.path.exists(rules_file), ".agents/notes/chess_rules.md must exist"

    with open(rules_file, encoding="utf-8") as f:
        content = f.read()

    required_keywords = [
        "King",
        "Queen",
        "Rook",
        "Bishop",
        "Knight",
        "Pawn",
        "Castling",
        "En Passant",
        "Promotion",
        "Checkmate",
        "Stalemate",
        "Fifty-Move Rule",
        "Threefold Repetition",
    ]
    for kw in required_keywords:
        assert kw in content, f"Chess rules must mention '{kw}'"
