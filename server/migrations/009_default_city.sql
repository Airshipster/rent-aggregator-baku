ALTER TABLE users ADD COLUMN IF NOT EXISTS default_city_id integer NOT NULL DEFAULT 1;
ALTER TABLE users ADD COLUMN IF NOT EXISTS default_city_name text NOT NULL DEFAULT 'Bakı';

UPDATE filters
SET basic = jsonb_set(
  CASE WHEN basic ? 'city' THEN basic ELSE basic || '{"city":["Bakı"]}'::jsonb END,
  '{category_slug}',
  to_jsonb(ARRAY[
    CASE basic->'category_slug'->>0
      WHEN 'yeni-tikili' THEN 'menziller/yeni-tikili'
      WHEN 'kohne-tikili' THEN 'menziller/kohne-tikili'
      WHEN 'house' THEN 'heyet-evleri'
      WHEN 'office' THEN 'ofisler'
      WHEN 'garage' THEN 'qarajlar'
      WHEN 'land' THEN 'torpaq'
      WHEN 'commercial' THEN 'obyektler'
      ELSE basic->'category_slug'->>0
    END
  ]::text[]),
  true
)
WHERE basic ? 'category_slug';

UPDATE filters
SET basic = basic || '{"city":["Bakı"]}'::jsonb
WHERE NOT (basic ? 'city');
