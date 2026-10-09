-- Check: the quarters of a fiscal year follow each other with no gap and no overlap, the first
-- starts with the year, and the fourth ends with the year.
SELECT q.registrant, q.fiscal_year, q.quarter
FROM fiscal_quarter q
JOIN fiscal_year y USING (regulator, registrant, fiscal_year)
LEFT JOIN fiscal_quarter previous
    ON previous.regulator = q.regulator AND previous.registrant = q.registrant
   AND previous.fiscal_year = q.fiscal_year AND previous.quarter = q.quarter - 1
WHERE q.start_date IS DISTINCT FROM
          CASE WHEN q.quarter = 1 THEN y.start_date ELSE previous.end_date + 1 END
   OR (q.quarter = 4 AND q.end_date <> y.end_date)
