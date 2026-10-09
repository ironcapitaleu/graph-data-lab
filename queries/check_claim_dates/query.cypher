// Check: an ownership claim is not about a date after we observed it (as_of <= observed_at).
MATCH (o:Company)-[r:OWNS_STAKE_IN]->(t:Company)
WHERE r.as_of > r.observed_at
RETURN o.company_id AS owner_id, t.company_id AS owned_id, r.source AS source
