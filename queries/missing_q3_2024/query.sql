-- Companies whose SEC fiscal year 2024 has no filing for its third quarter. Anti-join.
SELECT g.company_id
FROM fiscal_quarter q
JOIN registrant g ON g.source = q.source AND g.native_id = q.registrant
WHERE q.source = 'SEC' AND q.fiscal_year = 2024 AND q.quarter = 3
  AND NOT EXISTS (
      SELECT 1
      FROM filing f
      WHERE f.source = q.source AND f.registrant = q.registrant
        AND f.fiscal_year = q.fiscal_year AND f.quarter = q.quarter
  )
