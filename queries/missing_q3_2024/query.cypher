// Companies whose SEC fiscal year 2024 has no filing for its third quarter. Anti-join.
MATCH (c:Company)-[:REGISTERED_WITH]->(:Registrant {source: 'SEC'})
      -[:HAS_FISCAL_YEAR]->(:FiscalYear {fiscal_year: 2024})
      -[:HAS_QUARTER]->(q:FiscalQuarter {quarter: 3})
WHERE NOT EXISTS { (:Filing)-[:REPORTS_ON]->(q) }
RETURN c.company_id AS company_id
