// Check: identifiers match their scheme's format. LEI check digits are not verified yet.
MATCH (i:Identifier)
WHERE (i.scheme = 'LEI' AND NOT i.value =~ '[A-Z0-9]{18}[0-9]{2}')
   OR (i.scheme = 'CIK' AND NOT i.value =~ '[0-9]{10}')
RETURN i.scheme AS scheme, i.value AS value
