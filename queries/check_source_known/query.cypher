// Check: every claim names a source that the Source list holds.
MATCH ()-[r:LISTED_ON|IN_INDUSTRY|SUBSIDIARY_OF|OWNS_STAKE_IN]->()
WITH DISTINCT r.source AS source
WHERE NOT EXISTS { (:Source {code: source}) }
RETURN source
