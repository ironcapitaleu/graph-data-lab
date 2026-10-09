-- Concepts a filing's form requires but the filing does not report. Set difference.
SELECT f.native_id, r.element
FROM filing f
JOIN requires r ON r.regulator = f.regulator AND r.form = f.form
EXCEPT
SELECT native_id, element
FROM reports_concept
