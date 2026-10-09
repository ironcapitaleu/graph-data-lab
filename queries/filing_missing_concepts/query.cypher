// Concepts a filing's form requires but the filing does not report. Set difference.
MATCH (f:Filing)-[:OF_FORM]->(:FormType)-[:REQUIRES]->(k:Concept)
WHERE NOT (f)-[:REPORTS_CONCEPT]->(k)
RETURN f.native_id AS native_id, k.element AS element
