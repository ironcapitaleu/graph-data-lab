-- SEC filers with no filing that covers Q3-2024. Anti-join.
SELECT fw.company_id
FROM files_with fw
WHERE fw.regulator = 'SEC'
  AND NOT EXISTS (
      SELECT 1
      FROM has_filing hf
      JOIN covers_period cp USING (regulator, native_id)
      WHERE hf.company_id = fw.company_id AND cp.period_key = 'Q3-2024'
  )
