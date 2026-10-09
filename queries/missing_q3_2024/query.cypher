// SEC filers with no filing that covers Q3-2024. Anti-join.
MATCH (c:Company)-[:FILES_WITH]->(:Regulator {code: 'SEC'})
WHERE NOT EXISTS { (c)-[:HAS_FILING]->(:Filing)-[:COVERS_PERIOD]->(:Period {key: 'Q3-2024'}) }
RETURN c.company_id AS company_id
