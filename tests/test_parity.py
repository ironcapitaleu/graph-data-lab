"""Check that seed.cypher and seed.sql load the same data, by comparing counts."""

import pytest

# Each pair counts the same thing in both stores. FILED_UNDER and OF_FORM are columns of
# `filing` in SQL, so they count as filings.
COUNTS = [
    ("MATCH (n:Company) RETURN count(n)", "SELECT count(*) FROM company"),
    ("MATCH (n:Identifier) RETURN count(n)", "SELECT count(*) FROM identifier"),
    ("MATCH (n:Concept) RETURN count(n)", "SELECT count(*) FROM concept"),
    ("MATCH (n:Period) RETURN count(n)", "SELECT count(*) FROM period"),
    ("MATCH (n:Regulator) RETURN count(n)", "SELECT count(*) FROM regulator"),
    ("MATCH (n:FormType) RETURN count(n)", "SELECT count(*) FROM form_type"),
    ("MATCH (n:Filing) RETURN count(n)", "SELECT count(*) FROM filing"),
    ("MATCH (n:Exchange) RETURN count(n)", "SELECT count(*) FROM exchange"),
    ("MATCH (n:Industry) RETURN count(n)", "SELECT count(*) FROM industry"),
    ("MATCH ()-[r:HAS_IDENTIFIER]->() RETURN count(r)", "SELECT count(*) FROM has_identifier"),
    ("MATCH ()-[r:REQUIRES]->() RETURN count(r)", "SELECT count(*) FROM requires"),
    ("MATCH ()-[r:FILES_WITH]->() RETURN count(r)", "SELECT count(*) FROM files_with"),
    ("MATCH ()-[r:HAS_FILING]->() RETURN count(r)", "SELECT count(*) FROM has_filing"),
    ("MATCH ()-[r:FILED_UNDER]->() RETURN count(r)", "SELECT count(*) FROM filing"),
    ("MATCH ()-[r:OF_FORM]->() RETURN count(r)", "SELECT count(*) FROM filing"),
    ("MATCH ()-[r:COVERS_PERIOD]->() RETURN count(r)", "SELECT count(*) FROM covers_period"),
    ("MATCH ()-[r:REPORTS_CONCEPT]->() RETURN count(r)", "SELECT count(*) FROM reports_concept"),
    ("MATCH ()-[r:LISTED_ON]->() RETURN count(r)", "SELECT count(*) FROM listed_on"),
    ("MATCH ()-[r:IN_INDUSTRY]->() RETURN count(r)", "SELECT count(*) FROM in_industry"),
    ("MATCH ()-[r:SUBSIDIARY_OF]->() RETURN count(r)", "SELECT count(*) FROM subsidiary_of"),
    ("MATCH ()-[r:OWNS_STAKE_IN]->() RETURN count(r)", "SELECT count(*) FROM owns_stake_in"),
]


@pytest.mark.parametrize(("cypher", "sql"), COUNTS, ids=[cypher.split()[1] for cypher, _ in COUNTS])
def test_same_count_in_both_stores(cypher, sql, neo4j_session, postgres_connection):
    expected_count = postgres_connection.execute(sql).fetchone()[0]

    count = neo4j_session.run(cypher).single()[0]

    assert count == expected_count
