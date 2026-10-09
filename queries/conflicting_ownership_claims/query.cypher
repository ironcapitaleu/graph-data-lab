// Same owner, same owned company, same as_of, different percentages: a genuine conflict.
MATCH (o:Company)-[r:OWNS_STAKE_IN]->(t:Company)
WITH o, t, r.as_of AS as_of, count(DISTINCT r.percentage) AS distinct_percentages
WHERE distinct_percentages > 1
RETURN o.company_id AS owner_id, t.company_id AS owned_id,
       toString(as_of) AS as_of, distinct_percentages
