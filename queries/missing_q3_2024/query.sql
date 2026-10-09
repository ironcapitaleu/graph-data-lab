-- SEC registrants whose fiscal year 2024 has no filing for its third quarter. Anti-join.
SELECT g.company_id
FROM fiscal_quarter q
JOIN registrant g ON g.regulator = q.regulator AND g.native_id = q.registrant
WHERE q.regulator = 'SEC' AND q.fiscal_year = 2024 AND q.quarter = 3
  AND NOT EXISTS (
      SELECT 1
      FROM filing f
      WHERE f.regulator = q.regulator AND f.registrant = q.registrant
        AND f.fiscal_year = q.fiscal_year AND f.quarter = q.quarter
  )
