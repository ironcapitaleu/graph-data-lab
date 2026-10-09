-- Check: identifiers match their scheme's format. LEI check digits are not verified yet.
SELECT scheme, value
FROM identifier
WHERE (scheme = 'LEI' AND value !~ '^[A-Z0-9]{18}[0-9]{2}$')
   OR (scheme = 'CIK' AND value !~ '^[0-9]{10}$')
