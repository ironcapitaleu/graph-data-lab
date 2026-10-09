// Check: the quarters of a fiscal year follow each other with no gap and no overlap, the first
// starts with the year, and the fourth ends with the year.
MATCH (y:FiscalYear)-[:HAS_QUARTER]->(q:FiscalQuarter)
OPTIONAL MATCH (y)-[:HAS_QUARTER]->(previous:FiscalQuarter {quarter: q.quarter - 1})
WITH y, q,
     CASE WHEN q.quarter = 1 THEN y.start_date
          ELSE previous.end_date + duration({days: 1}) END AS expected_start
WHERE expected_start IS NULL
   OR q.start_date <> expected_start
   OR (q.quarter = 4 AND q.end_date <> y.end_date)
RETURN q.registrant AS registrant, q.fiscal_year AS fiscal_year, q.quarter AS quarter
