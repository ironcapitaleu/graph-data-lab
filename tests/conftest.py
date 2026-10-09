"""Shared fixtures: connect to both stores, reset them, load the schema and the seed."""

import os
import re
from pathlib import Path

import psycopg
import pytest
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent.parent

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = (
    os.environ.get("NEO4J_USER", "neo4j"),
    os.environ.get("NEO4J_PASSWORD", "graph-data-lab"),
)
POSTGRES_DSN = os.environ.get(
    "POSTGRES_DSN", "postgresql://lab:graph-data-lab@localhost:5432/lab"
)


def cypher_statements(path: Path) -> list[str]:
    """Split a Cypher file on statement-ending semicolons and drop comment-only parts."""
    parts = re.split(r";\s*$", path.read_text(), flags=re.MULTILINE)
    statements = []
    for part in parts:
        code = "\n".join(
            line for line in part.splitlines() if not line.strip().startswith("//")
        ).strip()
        if code:
            statements.append(code)
    return statements


@pytest.fixture(scope="session")
def neo4j_session():
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n").consume()
        for record in session.run("SHOW CONSTRAINTS YIELD name").data():
            session.run(f"DROP CONSTRAINT {record['name']}").consume()
        for path in (ROOT / "model/schema.cypher", ROOT / "fixtures/seed.cypher"):
            for statement in cypher_statements(path):
                session.run(statement).consume()
        yield session
    driver.close()


@pytest.fixture(scope="session")
def postgres_connection():
    with psycopg.connect(POSTGRES_DSN, autocommit=True) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        for path in (ROOT / "model/schema.sql", ROOT / "fixtures/seed.sql"):
            connection.execute(path.read_text())
        yield connection
