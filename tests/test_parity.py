"""Check that seed.cypher and seed.sql load the same data, by comparing counts.

External dependencies: Neo4j and Postgres from `docker-compose.yml`.
"""

from typing import LiteralString

import psycopg
import pytest
from neo4j import Session

# Each pair counts the same thing in both stores. An edge that is a column or a foreign key in
# SQL counts as the rows of its table.
COUNTS: list[tuple[LiteralString, LiteralString]] = [
    ("MATCH (n:Source) RETURN count(n)", "SELECT count(*) FROM source"),
    ("MATCH (n:Concept) RETURN count(n)", "SELECT count(*) FROM concept"),
    ("MATCH (n:FormType) RETURN count(n)", "SELECT count(*) FROM form_type"),
    ("MATCH (n:Company) RETURN count(n)", "SELECT count(*) FROM company"),
    ("MATCH (n:Identifier) RETURN count(n)", "SELECT count(*) FROM identifier"),
    ("MATCH (n:Registrant) RETURN count(n)", "SELECT count(*) FROM registrant"),
    (
        "MATCH (n:Registrant {source: 'GLEIF'}) RETURN count(n)",
        "SELECT count(*) FROM registrant WHERE source = 'GLEIF'",
    ),
    ("MATCH (n:FiscalYear) RETURN count(n)", "SELECT count(*) FROM fiscal_year"),
    ("MATCH (n:FiscalQuarter) RETURN count(n)", "SELECT count(*) FROM fiscal_quarter"),
    (
        "MATCH (n:FiscalQuarter {calendar_quarter: 'Q3-2024'}) RETURN count(n)",
        "SELECT count(*) FROM fiscal_quarter WHERE calendar_quarter = 'Q3-2024'",
    ),
    ("MATCH (n:Filing) RETURN count(n)", "SELECT count(*) FROM filing"),
    ("MATCH (n:Exchange) RETURN count(n)", "SELECT count(*) FROM exchange"),
    ("MATCH (n:Industry) RETURN count(n)", "SELECT count(*) FROM industry"),
    ("MATCH ()-[r:REQUIRES]->() RETURN count(r)", "SELECT count(*) FROM requires"),
    ("MATCH ()-[r:HAS_IDENTIFIER]->() RETURN count(r)", "SELECT count(*) FROM has_identifier"),
    ("MATCH ()-[r:REGISTERED_WITH]->() RETURN count(r)", "SELECT count(*) FROM registrant"),
    ("MATCH ()-[r:HAS_FISCAL_YEAR]->() RETURN count(r)", "SELECT count(*) FROM fiscal_year"),
    ("MATCH ()-[r:HAS_QUARTER]->() RETURN count(r)", "SELECT count(*) FROM fiscal_quarter"),
    ("MATCH ()-[r:HAS_FILING]->() RETURN count(r)", "SELECT count(*) FROM filing"),
    (
        "MATCH ()-[r:REPORTS_ON]->() RETURN count(r)",
        "SELECT count(*) FROM filing WHERE fiscal_year IS NOT NULL",
    ),
    (
        "MATCH ()-[r:REPORTS_ON]->(:FiscalQuarter) RETURN count(r)",
        "SELECT count(*) FROM filing WHERE quarter IS NOT NULL",
    ),
    ("MATCH ()-[r:REPORTS_CONCEPT]->() RETURN count(r)", "SELECT count(*) FROM reports_concept"),
    ("MATCH ()-[r:LISTED_ON]->() RETURN count(r)", "SELECT count(*) FROM listed_on"),
    ("MATCH ()-[r:IN_INDUSTRY]->() RETURN count(r)", "SELECT count(*) FROM in_industry"),
    ("MATCH ()-[r:SUBSIDIARY_OF]->() RETURN count(r)", "SELECT count(*) FROM subsidiary_of"),
    ("MATCH ()-[r:OWNS_STAKE_IN]->() RETURN count(r)", "SELECT count(*) FROM owns_stake_in"),
    # The graph holds no node and no edge that the tables do not account for.
    (
        "MATCH (n) RETURN count(DISTINCT labels(n))",
        "SELECT 11",
    ),
    (
        "MATCH ()-[r]->() RETURN count(DISTINCT type(r))",
        "SELECT 12",
    ),
]


@pytest.mark.parametrize(
    ("cypher", "sql"), COUNTS, ids=[" ".join(cypher.split()[1:-2]) for cypher, _ in COUNTS]
)
def test_should_hold_the_same_count_for_both_stores(
    cypher: LiteralString,
    sql: LiteralString,
    neo4j_session: Session,
    postgres_connection: psycopg.Connection,
) -> None:
    expected_result = postgres_connection.execute(sql).fetchall()[0][0]

    result = neo4j_session.run(cypher).single(strict=True)[0]

    assert result == expected_result
