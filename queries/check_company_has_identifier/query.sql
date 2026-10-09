-- Check: every company has at least one identifier.
SELECT c.company_id
FROM company c
WHERE NOT EXISTS (SELECT 1 FROM has_identifier h WHERE h.company_id = c.company_id)
