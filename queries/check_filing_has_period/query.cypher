// Check: every filing reports on a fiscal year or a fiscal quarter.
MATCH (f:Filing)
WHERE NOT EXISTS { (f)-[:REPORTS_ON]->() }
RETURN f.native_id AS native_id
