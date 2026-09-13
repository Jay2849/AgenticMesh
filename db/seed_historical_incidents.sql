-- Seed some services
INSERT INTO services (id, name, current_image_tag, stable_image_tag) VALUES
  ('11111111-1111-1111-1111-111111111111', 'payment-service', 'v2.1', 'v2.0'),
  ('22222222-2222-2222-2222-222222222222', 'auth-service', 'v1.5', 'v1.4'),
  ('55555555-5555-5555-5555-555555555555', 'ingestion-service', 'v1.0', 'v1.0')
ON CONFLICT (id) DO NOTHING;

-- Seed historical incidents
INSERT INTO incidents (id, incident_id, service_id, fingerprint_hash, status) VALUES
  ('33333333-3333-3333-3333-333333333333', 'inc_hist_001', '11111111-1111-1111-1111-111111111111', 'hash1', 'REMEDIATED'),
  ('44444444-4444-4444-4444-444444444444', 'inc_hist_002', '11111111-1111-1111-1111-111111111111', 'hash2', 'REMEDIATED')
ON CONFLICT (id) DO NOTHING;

-- Seed incident embeddings (mocking 1536 dim vectors with random data)
INSERT INTO incident_embeddings (incident_id, error_signature, embedding)
SELECT 
  '33333333-3333-3333-3333-333333333333', 
  'payment-service | ConnectionPoolExhaustedError | process_payment', 
  (SELECT array_agg(random())::vector(1536) FROM generate_series(1, 1536));

INSERT INTO incident_embeddings (incident_id, error_signature, embedding)
SELECT 
  '44444444-4444-4444-4444-444444444444', 
  'payment-service | TimeoutError | check_balance', 
  (SELECT array_agg(random())::vector(1536) FROM generate_series(1, 1536));

-- Seed RCA results for history
INSERT INTO rca_results (incident_id, root_cause, suggested_fix_diff) VALUES
  ('33333333-3333-3333-3333-333333333333', 'DB connections not closed in process_payment. Ensure `conn.close()` is called.', 'diff --git a/payment_service.py b/payment_service.py'),
  ('44444444-4444-4444-4444-444444444444', 'External API timeout during check_balance. Increased timeout from 1s to 5s.', 'diff --git a/payment_service.py b/payment_service.py');
