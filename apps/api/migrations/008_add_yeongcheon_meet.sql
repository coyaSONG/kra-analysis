-- Preserve historical migration checksums; widen only the physical venue check.
ALTER TABLE races
DROP CONSTRAINT IF EXISTS races_meet_check;

ALTER TABLE races
ADD CONSTRAINT races_meet_check CHECK (meet IN (1, 2, 3, 4));
