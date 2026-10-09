// SEC filers missing any of the four FY2024 reports (Q1, Q2, Q3 10-Q and the FY 10-K).
MATCH (c:Company)-[:FILES_WITH]->(:Regulator {code: 'SEC'})
UNWIND ['Q1-2024', 'Q2-2024', 'Q3-2024', 'FY2024'] AS key
WITH c, key
WHERE NOT EXISTS { (c)-[:HAS_FILING]->(:Filing)-[:COVERS_PERIOD]->(:Period {key: key}) }
RETURN c.company_id AS company_id, key AS missing_period
