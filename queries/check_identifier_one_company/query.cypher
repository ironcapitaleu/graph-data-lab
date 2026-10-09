// Check: an identifier belongs to one company. Two companies with the same identifier are
// either one company or one wrong record.
MATCH (i:Identifier)<-[:HAS_IDENTIFIER]-(c:Company)
WITH i, count(c) AS companies
WHERE companies > 1
RETURN i.scheme AS scheme, i.value AS value, companies
