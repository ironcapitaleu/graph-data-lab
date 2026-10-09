// Companies whose SEC fiscal year 2024 misses a report: the 10-Q of the first, second, or
// third quarter, or the 10-K of the year. The fourth quarter has no report of its own.
MATCH (c:Company)-[:REGISTERED_WITH]->(:Registrant {source: 'SEC'})
      -[:HAS_FISCAL_YEAR]->(y:FiscalYear {fiscal_year: 2024})
CALL (y) {
  MATCH (y)-[:HAS_QUARTER]->(q:FiscalQuarter)
  WHERE q.quarter <= 3 AND NOT EXISTS { (:Filing)-[:REPORTS_ON]->(q) }
  RETURN 'Q' + toString(q.quarter) AS missing_period
  UNION
  MATCH (y)
  WHERE NOT EXISTS { (:Filing)-[:REPORTS_ON]->(y) }
  RETURN 'FY' AS missing_period
}
RETURN c.company_id AS company_id, missing_period
