-- Check: every claim names a source that the source table holds.
SELECT claim.source
FROM (
    SELECT source FROM listed_on
    UNION SELECT source FROM in_industry
    UNION SELECT source FROM subsidiary_of
    UNION SELECT source FROM owns_stake_in
) AS claim
WHERE NOT EXISTS (SELECT 1 FROM source s WHERE s.code = claim.source)
