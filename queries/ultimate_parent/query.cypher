// For every subsidiary, the top of its SUBSIDIARY_OF chain. Multi-hop traversal.
MATCH (c:Company)-[:SUBSIDIARY_OF*1..]->(top:Company)
WHERE NOT (top)-[:SUBSIDIARY_OF]->()
RETURN DISTINCT c.company_id AS company_id, top.company_id AS ultimate_parent_id
