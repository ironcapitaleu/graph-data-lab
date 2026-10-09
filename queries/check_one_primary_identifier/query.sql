-- Check: every company has exactly one primary identifier.
SELECT c.company_id, count(h.company_id) AS primary_count
FROM company c
LEFT JOIN has_identifier h ON h.company_id = c.company_id AND h.is_primary
GROUP BY c.company_id
HAVING count(h.company_id) <> 1
