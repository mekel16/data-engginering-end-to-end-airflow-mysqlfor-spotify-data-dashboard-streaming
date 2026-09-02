CREATE TABLE IF NOT EXISTS raw_spotify_api_responses (
    ingestion_id CHAR(36) NOT NULL,
    raw_checksum CHAR(64) NOT NULL,
    source VARCHAR(100) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    request_params_json JSON NULL,
    fetched_at DATETIME(6) NOT NULL,
    payload_json JSON NOT NULL,
    loaded_at DATETIME(6) NOT NULL
        DEFAULT CURRENT_TIMESTAMP(6),

    PRIMARY KEY (ingestion_id),

    UNIQUE KEY uq_raw_checksum (
        raw_checksum
    ),

    KEY idx_raw_source_fetched (
        source,
        fetched_at
    )
)
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;