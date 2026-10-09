-- Check: every filing reports on a fiscal year or a fiscal quarter.
SELECT native_id
FROM filing
WHERE fiscal_year IS NULL
