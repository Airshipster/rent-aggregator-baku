ALTER TABLE channel_posts DROP CONSTRAINT IF EXISTS channel_posts_status_check;
ALTER TABLE channel_posts ADD CONSTRAINT channel_posts_status_check
  CHECK (status IN ('pending','sent','failed','removed','retired'));

UPDATE channel_posts AS post
SET status='retired',updated_at=now()
FROM listings AS listing
WHERE post.listing_id=listing.id
  AND NOT (
    listing.payload->>'deal_type'='rent'
    AND listing.payload->>'city'='Bakı'
    AND listing.payload->>'category_slug' IN ('menziller/yeni-tikili','menziller/kohne-tikili')
  );
