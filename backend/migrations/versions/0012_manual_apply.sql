-- Manual SQL Migration for adding is_pretrained column
-- Run this if you need to apply migration manually on Render database
-- Migration: 0012_add_pretrained_fields

-- Add is_pretrained column to ml_models
ALTER TABLE ml_models
ADD COLUMN IF NOT EXISTS is_pretrained BOOLEAN NOT NULL DEFAULT false;

-- Add default_model_id column to ml_models
ALTER TABLE ml_models
ADD COLUMN IF NOT EXISTS default_model_id UUID;

-- Add foreign key constraint
ALTER TABLE ml_models
ADD CONSTRAINT IF NOT EXISTS fk_ml_models_default_model
FOREIGN KEY (default_model_id)
REFERENCES default_ml_models(id);

-- Verify columns were added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'ml_models'
  AND column_name IN ('is_pretrained', 'default_model_id')
ORDER BY column_name;

-- Insert migration record to alembic_version table
-- This tells Alembic that this migration has been applied
INSERT INTO alembic_version (version_num)
VALUES ('0012_add_pretrained_fields')
ON CONFLICT (version_num) DO NOTHING;

-- Verify migration record
SELECT * FROM alembic_version;
