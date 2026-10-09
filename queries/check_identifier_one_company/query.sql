-- Check: an identifier belongs to one company. Two companies with the same identifier are
-- either one company or one wrong record.
SELECT scheme, value, count(*) AS companies
FROM has_identifier
GROUP BY scheme, value
HAVING count(*) > 1
