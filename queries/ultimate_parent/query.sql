-- For every subsidiary, the top of its SUBSIDIARY_OF chain. Recursive CTE.
WITH RECURSIVE chain (company_id, ancestor_id) AS (
    SELECT child_id, parent_id FROM subsidiary_of
    UNION
    SELECT chain.company_id, s.parent_id
    FROM chain
    JOIN subsidiary_of s ON s.child_id = chain.ancestor_id
)
SELECT DISTINCT company_id, ancestor_id AS ultimate_parent_id
FROM chain
WHERE NOT EXISTS (SELECT 1 FROM subsidiary_of s WHERE s.child_id = chain.ancestor_id)
