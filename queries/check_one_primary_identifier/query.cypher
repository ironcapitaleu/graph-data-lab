// Check: every company has exactly one primary identifier.
MATCH (c:Company)
OPTIONAL MATCH (c)-[h:HAS_IDENTIFIER {primary: true}]->()
WITH c, count(h) AS primary_count
WHERE primary_count <> 1
RETURN c.company_id AS company_id, primary_count
