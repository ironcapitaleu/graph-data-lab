-- SEC registrants whose fiscal year 2024 misses a report: the 10-Q of the first, second, or
-- third quarter, or the 10-K of the year. The fourth quarter has no report of its own.
SELECT g.company_id, 'Q' || q.quarter AS missing_period
FROM fiscal_quarter q
JOIN registrant g ON g.regulator = q.regulator AND g.native_id = q.registrant
WHERE q.regulator = 'SEC' AND q.fiscal_year = 2024 AND q.quarter <= 3
  AND NOT EXISTS (
      SELECT 1
      FROM filing f
      WHERE f.regulator = q.regulator AND f.registrant = q.registrant
        AND f.fiscal_year = q.fiscal_year AND f.quarter = q.quarter
  )
UNION ALL
SELECT g.company_id, 'FY'
FROM fiscal_year y
JOIN registrant g ON g.regulator = y.regulator AND g.native_id = y.registrant
WHERE y.regulator = 'SEC' AND y.fiscal_year = 2024
  AND NOT EXISTS (
      SELECT 1
      FROM filing f
      WHERE f.regulator = y.regulator AND f.registrant = y.registrant
        AND f.fiscal_year = y.fiscal_year AND f.quarter IS NULL
  )
