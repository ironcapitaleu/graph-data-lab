// Check: ownership percentage is in (0, 100].
MATCH (o:Company)-[r:OWNS_STAKE_IN]->(t:Company)
WHERE NOT (r.percentage > 0 AND r.percentage <= 100)
RETURN o.company_id AS owner_id, t.company_id AS owned_id, r.source AS source
