// Every company below Alpha in the SUBSIDIARY_OF tree, with its shortest depth.
MATCH path = (c:Company)-[:SUBSIDIARY_OF*1..]->(:Company {company_id: 'LEI:5493001ALPHAHOLD0020'})
RETURN c.company_id AS company_id, min(length(path)) AS depth
