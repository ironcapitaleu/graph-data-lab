"""Shared fixtures: connect to both stores and load them from nothing."""

from collections.abc import Iterator

import psycopg
import pytest
from neo4j import GraphDatabase, Session

from scripts.load_stores import NEO4J_AUTH, NEO4J_URI, POSTGRES_DSN, load_neo4j, load_postgres


@pytest.fixture(scope="session")
def neo4j_session() -> Iterator[Session]:
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    with driver.session() as session:
        load_neo4j(session)
        yield session
    driver.close()


@pytest.fixture(scope="session")
def postgres_connection() -> Iterator[psycopg.Connection]:
    with psycopg.connect(POSTGRES_DSN, autocommit=True) as connection:
        load_postgres(connection)
        yield connection
