// Check: every company has at least one identifier.
MATCH (c:Company)
WHERE NOT (c)-[:HAS_IDENTIFIER]->()
RETURN c.company_id AS company_id
