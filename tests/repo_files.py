"""Paths to the model, seed, and query files of the lab, and a reader for them."""

from pathlib import Path
from typing import LiteralString, cast

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "queries"


def read_statement(path: Path) -> LiteralString:
    """Reads a Cypher or SQL file of this repo as a statement the drivers accept.

    Both drivers accept only a literal string, to stop injection through user input. The files
    under `model/`, `fixtures/`, and `queries/` are version controlled and hold no user input.
    """
    return cast(LiteralString, path.read_text())
