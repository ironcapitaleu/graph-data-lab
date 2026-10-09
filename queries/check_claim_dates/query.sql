-- Check: an ownership claim is not about a date after we observed it (as_of <= observed_at).
SELECT owner_id, owned_id, source
FROM owns_stake_in
WHERE as_of > observed_at
