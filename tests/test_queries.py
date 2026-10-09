"""Run every query in queries/ against both stores and compare to its expected.json."""

import json
from pathlib import Path

import pytest
from psycopg.rows import dict_row

QUERIES = Path(__file__).resolve().parent.parent / "queries"
QUERY_NAMES = sorted(path.name for path in QUERIES.iterdir() if path.is_dir())


def normalized(rows: list[dict]) -> list[dict]:
    """Sort rows so the comparison ignores row order. Both stores return rows in any order."""
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))


def expected_rows(name: str) -> list[dict]:
    return normalized(json.loads((QUERIES / name / "expected.json").read_text()))


@pytest.mark.parametrize("name", QUERY_NAMES)
def test_neo4j(name, neo4j_session):
    query = (QUERIES / name / "query.cypher").read_text()

    result = normalized(neo4j_session.run(query).data())

    assert result == expected_rows(name)


@pytest.mark.parametrize("name", QUERY_NAMES)
def test_postgres(name, postgres_connection):
    query = (QUERIES / name / "query.sql").read_text()

    with postgres_connection.cursor(row_factory=dict_row) as cursor:
        result = normalized(cursor.execute(query).fetchall())

    assert result == expected_rows(name)
