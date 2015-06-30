BEGIN;

ALTER TABLE samples
  ADD COLUMN subsample_count int,
  ADD COLUMN chem_analyses_count int,
  ADD COLUMN image_count int;

ALTER TABLE subsamples
  ADD COLUMN chem_analyses_count int,
  ADD COLUMN image_count int;

COMMIT;
