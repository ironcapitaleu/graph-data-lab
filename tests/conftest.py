"""Shared fixtures: connect to both stores, reset them, load the schema and the seed."""

import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import LiteralString, cast

import psycopg
import pytest
from neo4j import GraphDatabase, Session

from tests.repo_files import ROOT, read_statement

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = (
    os.environ.get("NEO4J_USER", "neo4j"),
    os.environ.get("NEO4J_PASSWORD", "graph-data-lab"),
)
POSTGRES_DSN = os.environ.get("POSTGRES_DSN", "postgresql://lab:graph-data-lab@localhost:5432/lab")


def cypher_statements(path: Path) -> list[LiteralString]:
    """Splits a Cypher file on statement-ending semicolons and drops comment-only parts."""
    statements: list[LiteralString] = []
    for part in re.split(r";\s*$", read_statement(path), flags=re.MULTILINE):
        code = "\n".join(
            line for line in part.splitlines() if not line.strip().startswith("//")
        ).strip()
        if code:
            # `re.split` widens the type to `str`. The text still comes from a repo file.
            statements.append(cast(LiteralString, code))
    return statements


@pytest.fixture(scope="session")
def neo4j_session() -> Iterator[Session]:
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n").consume()
        for record in session.run("SHOW CONSTRAINTS YIELD name").data():
            # The name comes from the database itself, not from user input.
            drop_constraint = cast(LiteralString, f"DROP CONSTRAINT {record['name']}")
            session.run(drop_constraint).consume()
        for path in (
            ROOT / "model/schema.cypher",
            ROOT / "fixtures/seed.cypher",
            ROOT / "fixtures/sp500.cypher",
        ):
            for statement in cypher_statements(path):
                session.run(statement).consume()
        yield session
    driver.close()


@pytest.fixture(scope="session")
def postgres_connection() -> Iterator[psycopg.Connection]:
    with psycopg.connect(POSTGRES_DSN, autocommit=True) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        for path in (
            ROOT / "model/schema.sql",
            ROOT / "fixtures/seed.sql",
            ROOT / "fixtures/sp500.sql",
        ):
            connection.execute(read_statement(path))
        yield connection
