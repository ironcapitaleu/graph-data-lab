-- Every company below Alpha in the SUBSIDIARY_OF tree, with its shortest depth.
-- UNION removes repeated (company, depth) rows, and the depth cap stops a cycle.
WITH RECURSIVE tree (company_id, depth) AS (
    SELECT child_id, 1 FROM subsidiary_of WHERE parent_id = 'LEI:5493001ALPHAHOLD0020'
    UNION
    SELECT s.child_id, tree.depth + 1
    FROM tree
    JOIN subsidiary_of s ON s.parent_id = tree.company_id
    WHERE tree.depth < 100
)
SELECT company_id, min(depth) AS depth
FROM tree
GROUP BY company_id
