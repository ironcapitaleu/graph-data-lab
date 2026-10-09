-- Check: ownership percentage is in (0, 100].
SELECT owner_id, owned_id, source
FROM owns_stake_in
WHERE NOT (percentage > 0 AND percentage <= 100)
