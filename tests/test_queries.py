"""Run every query in queries/ against both stores and compare to its expected.json.

External dependencies: Neo4j and Postgres from `docker-compose.yml`.
"""

import json
from typing import Any

import psycopg
import pytest
from neo4j import Session
from psycopg.rows import dict_row

from scripts.load_stores import QUERIES, read_statement

QUERY_NAMES = sorted(path.name for path in QUERIES.iterdir() if path.is_dir())

type Row = dict[str, Any]


def normalized(rows: list[Row]) -> list[Row]:
    """Sorts rows so the comparison ignores row order. Both stores return rows in any order."""
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))


def expected_rows(name: str) -> list[Row]:
    return normalized(json.loads((QUERIES / name / "expected.json").read_text()))


@pytest.mark.parametrize("name", QUERY_NAMES)
def test_should_return_the_expected_rows_for_neo4j(name: str, neo4j_session: Session) -> None:
    query = read_statement(QUERIES / name / "query.cypher")

    expected_result = expected_rows(name)

    result = normalized(neo4j_session.run(query).data())

    assert result == expected_result


@pytest.mark.parametrize("name", QUERY_NAMES)
def test_should_return_the_expected_rows_for_postgres(
    name: str, postgres_connection: psycopg.Connection
) -> None:
    query = read_statement(QUERIES / name / "query.sql")

    expected_result = expected_rows(name)

    with postgres_connection.cursor(row_factory=dict_row) as cursor:
        result = normalized(cursor.execute(query).fetchall())

    assert result == expected_result
