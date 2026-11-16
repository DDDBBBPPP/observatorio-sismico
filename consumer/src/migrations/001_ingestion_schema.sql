CREATE TABLE IF NOT EXISTS ingestion_run (
    run_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    load_type TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('live', 'historical', 'replay')),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    records_seen INTEGER NOT NULL DEFAULT 0,
    records_accepted INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS source_response (
    response_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES ingestion_run(run_id),
    url TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    http_status INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL,
    record_count INTEGER NOT NULL,
    payload_jsonb JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS event_version (
    event_version_id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL,
    updated BIGINT NOT NULL,
    event_time BIGINT,
    mag DOUBLE PRECISION,
    place TEXT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    depth_km DOUBLE PRECISION,
    source_response_id TEXT REFERENCES source_response(response_id),
    run_id TEXT NOT NULL REFERENCES ingestion_run(run_id),
    mode TEXT NOT NULL CHECK (mode IN ('live', 'historical', 'replay')),
    ingested_at TIMESTAMPTZ NOT NULL,
    original_jsonb JSONB NOT NULL,
    normalized_jsonb JSONB NOT NULL,
    source TEXT NOT NULL DEFAULT 'usgs',
    load_type TEXT NOT NULL DEFAULT 'live_feed',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    country_id TEXT,
    country_name TEXT,
    UNIQUE (event_id, updated)
);

CREATE TABLE IF NOT EXISTS event_current (
    event_id TEXT PRIMARY KEY,
    event_version_id BIGINT NOT NULL REFERENCES event_version(event_version_id),
    current_updated BIGINT NOT NULL,
    event_time BIGINT,
    mag DOUBLE PRECISION,
    place TEXT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    depth_km DOUBLE PRECISION,
    country_id TEXT,
    country_name TEXT,
    country_assignment_status TEXT NOT NULL DEFAULT 'unassigned',
    country_assignment_reason TEXT,
    original_jsonb JSONB NOT NULL,
    normalized_jsonb JSONB NOT NULL
    ,source TEXT NOT NULL DEFAULT 'usgs'
    ,load_type TEXT NOT NULL DEFAULT 'live_feed'
    ,is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
);

ALTER TABLE event_current ADD COLUMN IF NOT EXISTS country_id TEXT;
ALTER TABLE event_current ADD COLUMN IF NOT EXISTS country_name TEXT;
ALTER TABLE event_current ADD COLUMN IF NOT EXISTS country_assignment_status TEXT NOT NULL DEFAULT 'unassigned';
ALTER TABLE event_current ADD COLUMN IF NOT EXISTS country_assignment_reason TEXT;
ALTER TABLE event_version ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'usgs';
ALTER TABLE event_version ADD COLUMN IF NOT EXISTS load_type TEXT NOT NULL DEFAULT 'live_feed';
ALTER TABLE event_version ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE event_version ADD COLUMN IF NOT EXISTS country_id TEXT;
ALTER TABLE event_version ADD COLUMN IF NOT EXISTS country_name TEXT;
ALTER TABLE event_current ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'usgs';
ALTER TABLE event_current ADD COLUMN IF NOT EXISTS load_type TEXT NOT NULL DEFAULT 'live_feed';
ALTER TABLE event_current ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE event_version SET is_synthetic = TRUE WHERE event_id LIKE 'controlled-%';
UPDATE event_current SET is_synthetic = TRUE WHERE event_id LIKE 'controlled-%';
ALTER TABLE ingestion_run DROP CONSTRAINT IF EXISTS ingestion_run_mode_check;
ALTER TABLE event_version DROP CONSTRAINT IF EXISTS event_version_mode_check;
ALTER TABLE ingestion_run ADD CONSTRAINT ingestion_run_mode_check CHECK (mode IN ('live', 'historical', 'replay'));
ALTER TABLE event_version ADD CONSTRAINT event_version_mode_check CHECK (mode IN ('live', 'historical', 'replay'));

CREATE INDEX IF NOT EXISTS event_version_event_updated_idx
    ON event_version (event_id, updated);
CREATE INDEX IF NOT EXISTS event_current_event_time_idx
    ON event_current (event_time);
CREATE INDEX IF NOT EXISTS event_current_country_time_idx
    ON event_current (country_id, event_time);
CREATE INDEX IF NOT EXISTS ingestion_run_status_started_idx
    ON ingestion_run (status, started_at);
CREATE INDEX IF NOT EXISTS source_response_run_received_idx
    ON source_response (run_id, received_at);

CREATE TABLE IF NOT EXISTS quarantine_record (
    quarantine_id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES ingestion_run(run_id),
    source_response_id TEXT,
    event_id TEXT,
    stage TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    reason_detail TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    original_jsonb JSONB NOT NULL,
    payload_reference TEXT
);

CREATE INDEX IF NOT EXISTS quarantine_reason_created_idx
    ON quarantine_record (reason_code, created_at);

CREATE TABLE IF NOT EXISTS historical_interval_checkpoint (
    run_id TEXT NOT NULL REFERENCES ingestion_run(run_id),
    interval_start TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    accepted INTEGER NOT NULL,
    duplicates INTEGER NOT NULL,
    quarantined INTEGER NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, interval_start)
);

CREATE TABLE IF NOT EXISTS replay_event_version (
    event_id TEXT NOT NULL,
    updated BIGINT NOT NULL,
    event_time BIGINT,
    mag DOUBLE PRECISION,
    place TEXT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    depth_km DOUBLE PRECISION,
    country_id TEXT,
    country_name TEXT,
    original_jsonb JSONB NOT NULL,
    replay_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (event_id, updated)
);

CREATE TABLE IF NOT EXISTS replay_event_current (
    event_id TEXT PRIMARY KEY,
    current_updated BIGINT NOT NULL,
    event_time BIGINT,
    mag DOUBLE PRECISION,
    place TEXT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    depth_km DOUBLE PRECISION,
    country_id TEXT,
    country_name TEXT,
    original_jsonb JSONB NOT NULL,
    replay_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS replay_event_current_time_idx ON replay_event_current (event_time);

-- Repair only the completed corrected run's legacy counter from persisted rows.
UPDATE ingestion_run r SET records_accepted = (
    SELECT count(*) FROM event_version v WHERE v.run_id = r.run_id
)
WHERE r.run_id = 'historical-2025-minmag4-earthquake'
  AND r.status = 'completed'
  AND r.records_accepted <> (SELECT count(*) FROM event_version v WHERE v.run_id = r.run_id);
