-- Align ``subscribers`` with app/models.Subscriber (Neon / Postgres).
-- Run only the parts that match your existing schema.

-- If the table does not exist yet:
CREATE TABLE IF NOT EXISTS subscribers (
  id SERIAL PRIMARY KEY,
  email VARCHAR(320) UNIQUE NOT NULL,
  first_name VARCHAR(120),
  last_name VARCHAR(120),
  is_subscribed BOOLEAN NOT NULL DEFAULT FALSE,
  has_requested_demo BOOLEAN NOT NULL DEFAULT FALSE
);

-- If the table already exists but new columns are missing:
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS is_subscribed BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS has_requested_demo BOOLEAN NOT NULL DEFAULT FALSE;

-- Optional: store normalized emails for lookups (matches app upserts):
-- UPDATE subscribers SET email = lower(trim(email)) WHERE email IS NOT NULL;
