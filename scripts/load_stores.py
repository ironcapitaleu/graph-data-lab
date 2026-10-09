"""Creates both data stores from nothing: wipes them, then loads the schema and the seeds.

The tests use the same functions, so a store that the tests load and a store that this script
loads hold the same data. The load order is fixed in `LOAD_ORDER`.

Run it from the repo root. Start the stores first with `docker compose up -d --wait`.

    uv run python -m scripts.load_stores
"""

import os
import re
from pathlib import Path
from typing import LiteralString, cast

import psycopg
from neo4j import GraphDatabase, Session

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "queries"

LOAD_ORDER = ("model/schema", "fixtures/seed", "fixtures/sp500")
"""Files to load, without extension. Each one builds on the ones before it.

The schema comes first. The hand-written seed creates the reference data: sources, concepts,
and form types. The S&P 500 seed needs that reference data.
"""

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = (
    os.environ.get("NEO4J_USER", "neo4j"),
    os.environ.get("NEO4J_PASSWORD", "graph-data-lab"),
)
POSTGRES_DSN = os.environ.get("POSTGRES_DSN", "postgresql://lab:graph-data-lab@localhost:5432/lab")


def main() -> None:
    """Loads Neo4j and Postgres and prints how many nodes and rows each one holds."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    with driver.session() as session:
        load_neo4j(session)
        nodes = session.run("MATCH (n) RETURN count(n)").single(strict=True)[0]
        edges = session.run("MATCH ()-[r]->() RETURN count(r)").single(strict=True)[0]
    driver.close()
    print(f"Neo4j: {nodes} nodes, {edges} edges")

    with psycopg.connect(POSTGRES_DSN, autocommit=True) as connection:
        load_postgres(connection)
        companies = connection.execute("SELECT count(*) FROM company").fetchall()[0][0]
        filings = connection.execute("SELECT count(*) FROM filing").fetchall()[0][0]
    print(f"Postgres: {companies} companies, {filings} filings")


def load_neo4j(session: Session) -> None:
    """Deletes all data, constraints, and indexes, then loads the files of `LOAD_ORDER`."""
    session.run("MATCH (n) DETACH DELETE n").consume()
    for record in session.run("SHOW CONSTRAINTS YIELD name").data():
        session.run(schema_statement("DROP CONSTRAINT", record["name"])).consume()
    for record in session.run("SHOW INDEXES YIELD name, type WHERE type <> 'LOOKUP'").data():
        session.run(schema_statement("DROP INDEX", record["name"])).consume()
    for name in LOAD_ORDER:
        for statement in cypher_statements(ROOT / f"{name}.cypher"):
            session.run(statement).consume()


def load_postgres(connection: psycopg.Connection) -> None:
    """Drops the `public` schema, then loads the files of `LOAD_ORDER`."""
    connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
    connection.execute("CREATE SCHEMA public")
    for name in LOAD_ORDER:
        connection.execute(read_statement(ROOT / f"{name}.sql"))


def read_statement(path: Path) -> LiteralString:
    """Reads a Cypher or SQL file of this repo as a statement the drivers accept.

    Both drivers accept only a literal string, to stop injection through user input. The files
    under `model/`, `fixtures/`, and `queries/` are version controlled and hold no user input.
    """
    return cast(LiteralString, path.read_text())


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


def schema_statement(command: LiteralString, name: str) -> LiteralString:
    # The name comes from the database itself, not from user input.
    return cast(LiteralString, f"{command} {name}")


if __name__ == "__main__":
    main()
