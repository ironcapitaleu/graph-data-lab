-- Same owner, same owned company, same as_of, different percentages: a genuine conflict.
SELECT owner_id, owned_id, as_of::text AS as_of, count(DISTINCT percentage) AS distinct_percentages
FROM owns_stake_in
GROUP BY owner_id, owned_id, as_of
HAVING count(DISTINCT percentage) > 1
