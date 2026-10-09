-- SEC filers missing any of the four FY2024 reports (Q1, Q2, Q3 10-Q and the FY 10-K).
SELECT fw.company_id, expected.key AS missing_period
FROM files_with fw
CROSS JOIN (VALUES ('Q1-2024'), ('Q2-2024'), ('Q3-2024'), ('FY2024')) AS expected (key)
WHERE fw.regulator = 'SEC'
  AND NOT EXISTS (
      SELECT 1
      FROM has_filing hf
      JOIN covers_period cp USING (regulator, native_id)
      WHERE hf.company_id = fw.company_id AND cp.period_key = expected.key
  )
