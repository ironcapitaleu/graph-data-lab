// SEC registrants whose fiscal year 2024 has no filing for its third quarter. Anti-join.
MATCH (c:Company)-[:REGISTERED_AS]->(:Registrant {regulator: 'SEC'})
      -[:HAS_FISCAL_YEAR]->(:FiscalYear {fiscal_year: 2024})
      -[:HAS_QUARTER]->(q:FiscalQuarter {quarter: 3})
WHERE NOT EXISTS { (:Filing)-[:REPORTS_ON]->(q) }
RETURN c.company_id AS company_id
