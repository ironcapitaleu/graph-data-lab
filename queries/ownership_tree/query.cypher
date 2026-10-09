// Every company below Alpha in the SUBSIDIARY_OF tree, with its shortest depth.
MATCH path = (c:Company)-[:SUBSIDIARY_OF*1..]->(:Company {company_id: 'C-000001'})
RETURN c.company_id AS company_id, min(length(path)) AS depth
