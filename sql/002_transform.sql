-- STATEMENT
DROP TABLE IF EXISTS stg_track_plays;

-- STATEMENT
CREATE TABLE stg_track_plays (
  play_event_id CHAR(32) NOT NULL,
  played_at DATETIME(6) NOT NULL,
  track_id VARCHAR(64) NOT NULL,
  track_name VARCHAR(255) NOT NULL,
  album_id VARCHAR(64) NULL,
  album_name VARCHAR(255) NULL,
  artist_id VARCHAR(64) NULL,
  artist_name VARCHAR(255) NULL,
  duration_ms INT NULL,
  context_type VARCHAR(64) NULL,
  context_uri VARCHAR(255) NULL,
  raw_checksum CHAR(64) NOT NULL,
  fetched_at DATETIME(6) NOT NULL,
  PRIMARY KEY (play_event_id),
  KEY idx_track_plays_date (played_at),
  KEY idx_track_plays_track (track_id),
  KEY idx_track_plays_artist (artist_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- STATEMENT
INSERT INTO stg_track_plays (
  play_event_id,
  played_at,
  track_id,
  track_name,
  album_id,
  album_name,
  artist_id,
  artist_name,
  duration_ms,
  context_type,
  context_uri,
  raw_checksum,
  fetched_at
)
WITH parsed AS (
  SELECT
    MD5(
      CONCAT_WS(
        '|',
        jt.played_at_raw,
        jt.track_id,
        jt.duration_ms
      )
    ) AS play_event_id,

    STR_TO_DATE(
      REPLACE(
        REPLACE(jt.played_at_raw, 'T', ' '),
        'Z',
        ''
      ),
      '%Y-%m-%d %H:%i:%s.%f'
    ) AS played_at,

    jt.track_id,
    jt.track_name,
    jt.album_id,
    jt.album_name,
    jt.artist_id,
    jt.artist_name,
    jt.duration_ms,
    jt.context_type,
    jt.context_uri,
    r.raw_checksum,
    r.fetched_at

  FROM raw_spotify_api_responses AS r

  JOIN JSON_TABLE(
    r.payload_json,
    '$.items[*]' COLUMNS (
      played_at_raw VARCHAR(40) PATH '$.played_at',
      track_id VARCHAR(64) PATH '$.track.id',
      track_name VARCHAR(255) PATH '$.track.name',
      album_id VARCHAR(64) PATH '$.track.album.id',
      album_name VARCHAR(255) PATH '$.track.album.name',
      artist_id VARCHAR(64) PATH '$.track.artists[0].id',
      artist_name VARCHAR(255) PATH '$.track.artists[0].name',
      duration_ms INT PATH '$.track.duration_ms',
      context_type VARCHAR(64) PATH '$.context.type',
      context_uri VARCHAR(255) PATH '$.context.uri'
    )
  ) AS jt ON TRUE

  WHERE r.source = 'recently_played'
),
ranked AS (
  SELECT
    parsed.*,
    ROW_NUMBER() OVER (
      PARTITION BY play_event_id
      ORDER BY fetched_at DESC
    ) AS row_num
  FROM parsed
  WHERE played_at IS NOT NULL
    AND track_id IS NOT NULL
)
SELECT
  play_event_id,
  played_at,
  track_id,
  track_name,
  album_id,
  album_name,
  artist_id,
  artist_name,
  duration_ms,
  context_type,
  context_uri,
  raw_checksum,
  fetched_at
FROM ranked
WHERE row_num = 1;

-- STATEMENT
DROP TABLE IF EXISTS stg_top_tracks;

-- STATEMENT
CREATE TABLE stg_top_tracks (
  time_range VARCHAR(32) NOT NULL,
  ranking INT NOT NULL,
  track_id VARCHAR(64) NOT NULL,
  track_name VARCHAR(255) NOT NULL,
  album_name VARCHAR(255) NULL,
  artist_id VARCHAR(64) NULL,
  artist_name VARCHAR(255) NULL,
  fetched_at DATETIME(6) NOT NULL,
  PRIMARY KEY (time_range, track_id),
  KEY idx_top_tracks_rank (time_range, ranking)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- STATEMENT
INSERT INTO stg_top_tracks (
  time_range,
  ranking,
  track_id,
  track_name,
  album_name,
  artist_id,
  artist_name,
  fetched_at
)
WITH parsed AS (
  SELECT
    SUBSTRING(
      r.source,
      CHAR_LENGTH('top_tracks_') + 1
    ) AS time_range,
    jt.ranking,
    jt.track_id,
    jt.track_name,
    jt.album_name,
    jt.artist_id,
    jt.artist_name,
    r.fetched_at,

    ROW_NUMBER() OVER (
      PARTITION BY r.source, jt.track_id
      ORDER BY r.fetched_at DESC
    ) AS row_num

  FROM raw_spotify_api_responses AS r

  JOIN JSON_TABLE(
    r.payload_json,
    '$.items[*]' COLUMNS (
      ranking FOR ORDINALITY,
      track_id VARCHAR(64) PATH '$.id',
      track_name VARCHAR(255) PATH '$.name',
      album_name VARCHAR(255) PATH '$.album.name',
      artist_id VARCHAR(64) PATH '$.artists[0].id',
      artist_name VARCHAR(255) PATH '$.artists[0].name'
    )
  ) AS jt ON TRUE

  WHERE r.source LIKE 'top_tracks_%'
)
SELECT
  time_range,
  ranking,
  track_id,
  track_name,
  album_name,
  artist_id,
  artist_name,
  fetched_at
FROM parsed
WHERE row_num = 1
  AND track_id IS NOT NULL;

-- STATEMENT
DROP TABLE IF EXISTS stg_top_artists;

-- STATEMENT
CREATE TABLE stg_top_artists (
  time_range VARCHAR(32) NOT NULL,
  ranking INT NOT NULL,
  artist_id VARCHAR(64) NOT NULL,
  artist_name VARCHAR(255) NOT NULL,
  genres_json JSON NULL,
  fetched_at DATETIME(6) NOT NULL,
  PRIMARY KEY (time_range, artist_id),
  KEY idx_top_artists_rank (time_range, ranking)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- STATEMENT
INSERT INTO stg_top_artists (
  time_range,
  ranking,
  artist_id,
  artist_name,
  genres_json,
  fetched_at
)
WITH parsed AS (
  SELECT
    SUBSTRING(
      r.source,
      CHAR_LENGTH('top_artists_') + 1
    ) AS time_range,
    jt.ranking,
    jt.artist_id,
    jt.artist_name,

    JSON_EXTRACT(
      r.payload_json,
      CONCAT(
        '$.items[',
        jt.ranking - 1,
        '].genres'
      )
    ) AS genres_json,

    r.fetched_at,

    ROW_NUMBER() OVER (
      PARTITION BY r.source, jt.artist_id
      ORDER BY r.fetched_at DESC
    ) AS row_num

  FROM raw_spotify_api_responses AS r

  JOIN JSON_TABLE(
    r.payload_json,
    '$.items[*]' COLUMNS (
      ranking FOR ORDINALITY,
      artist_id VARCHAR(64) PATH '$.id',
      artist_name VARCHAR(255) PATH '$.name'
    )
  ) AS jt ON TRUE

  WHERE r.source LIKE 'top_artists_%'
)
SELECT
  time_range,
  ranking,
  artist_id,
  artist_name,
  genres_json,
  fetched_at
FROM parsed
WHERE row_num = 1
  AND artist_id IS NOT NULL;

-- STATEMENT
DROP TABLE IF EXISTS stg_playlists;

-- STATEMENT
CREATE TABLE stg_playlists (
  playlist_id VARCHAR(64) NOT NULL,
  playlist_name VARCHAR(255) NOT NULL,
  description TEXT NULL,
  is_public BOOLEAN NULL,
  track_count INT NULL,
  owner_display_name VARCHAR(255) NULL,
  fetched_at DATETIME(6) NOT NULL,
  PRIMARY KEY (playlist_id),
  KEY idx_playlists_name (playlist_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- STATEMENT
INSERT INTO stg_playlists (
  playlist_id,
  playlist_name,
  description,
  is_public,
  track_count,
  owner_display_name,
  fetched_at
)
WITH parsed AS (
  SELECT
    jt.*,
    r.fetched_at,

    ROW_NUMBER() OVER (
      PARTITION BY jt.playlist_id
      ORDER BY r.fetched_at DESC
    ) AS row_num

  FROM raw_spotify_api_responses AS r

  JOIN JSON_TABLE(
    r.payload_json,
    '$.items[*]' COLUMNS (
      playlist_id VARCHAR(64) PATH '$.id',
      playlist_name VARCHAR(255) PATH '$.name',
      description VARCHAR(1000) PATH '$.description',
      is_public BOOLEAN PATH '$.public',
      track_count INT PATH '$.tracks.total',
      owner_display_name VARCHAR(255) PATH '$.owner.display_name'
    )
  ) AS jt ON TRUE

  WHERE r.source = 'playlists'
)
SELECT
  playlist_id,
  playlist_name,
  description,
  is_public,
  track_count,
  owner_display_name,
  fetched_at
FROM parsed
WHERE row_num = 1
  AND playlist_id IS NOT NULL;

-- STATEMENT
DROP TABLE IF EXISTS mrt_daily_listening;

-- STATEMENT
CREATE TABLE mrt_daily_listening AS
WITH with_gaps AS (
  SELECT
    stg_track_plays.*,

    TIMESTAMPDIFF(
      MINUTE,
      LAG(played_at) OVER (
        ORDER BY played_at, play_event_id
      ),
      played_at
    ) AS gap_minutes

  FROM stg_track_plays
),
sessionized AS (
  SELECT
    with_gaps.*,

    SUM(
      CASE
        WHEN gap_minutes IS NULL
          OR gap_minutes > 30
        THEN 1
        ELSE 0
      END
    ) OVER (
      ORDER BY played_at, play_event_id
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS session_number

  FROM with_gaps
)
SELECT
  DATE(played_at) AS listening_date,
  COUNT(*) AS play_count,
  ROUND(
    SUM(COALESCE(duration_ms, 0)) / 60000,
    1
  ) AS minutes_listened,
  COUNT(DISTINCT track_id) AS unique_tracks,
  COUNT(DISTINCT artist_id) AS unique_artists,
  COUNT(DISTINCT session_number) AS session_count,
  MAX(played_at) AS last_played_at
FROM sessionized
GROUP BY DATE(played_at);

-- STATEMENT
ALTER TABLE mrt_daily_listening
  ADD PRIMARY KEY (listening_date),
  ADD KEY idx_daily_listening_date (listening_date);

-- STATEMENT
DROP TABLE IF EXISTS mrt_top_tracks;

-- STATEMENT
CREATE TABLE mrt_top_tracks AS
SELECT
  track_id,
  MAX(track_name) AS track_name,
  MAX(album_name) AS album_name,
  MAX(artist_id) AS artist_id,
  MAX(artist_name) AS artist_name,
  COUNT(*) AS play_count,
  ROUND(
    SUM(COALESCE(duration_ms, 0)) / 60000,
    1
  ) AS minutes_listened,
  MAX(played_at) AS last_played_at
FROM stg_track_plays
GROUP BY track_id
ORDER BY play_count DESC;

-- STATEMENT
ALTER TABLE mrt_top_tracks
  ADD PRIMARY KEY (track_id),
  ADD KEY idx_top_tracks_play_count (play_count);

-- STATEMENT
DROP TABLE IF EXISTS mrt_top_artists;

-- STATEMENT
CREATE TABLE mrt_top_artists AS
SELECT
  artist_id,
  MAX(artist_name) AS artist_name,
  COUNT(*) AS play_count,
  ROUND(
    SUM(COALESCE(duration_ms, 0)) / 60000,
    1
  ) AS minutes_listened,
  COUNT(DISTINCT track_id) AS unique_tracks,
  MAX(played_at) AS last_played_at
FROM stg_track_plays
WHERE artist_id IS NOT NULL
GROUP BY artist_id
ORDER BY play_count DESC;

-- STATEMENT
ALTER TABLE mrt_top_artists
  ADD PRIMARY KEY (artist_id),
  ADD KEY idx_top_artists_play_count (play_count);

-- STATEMENT
DROP TABLE IF EXISTS mrt_recent_activity;

-- STATEMENT
CREATE TABLE mrt_recent_activity AS
SELECT
  play_event_id,
  played_at,
  track_id,
  track_name,
  album_name,
  artist_id,
  artist_name,
  duration_ms,
  context_type,
  context_uri
FROM stg_track_plays
ORDER BY played_at DESC
LIMIT 100;

-- STATEMENT
ALTER TABLE mrt_recent_activity
  ADD PRIMARY KEY (play_event_id),
  ADD KEY idx_recent_activity_played_at (played_at);

-- STATEMENT
DROP TABLE IF EXISTS mrt_overview;

-- STATEMENT
CREATE TABLE mrt_overview AS
SELECT
  CURRENT_TIMESTAMP(6) AS generated_at,
  COUNT(*) AS total_plays,
  ROUND(
    SUM(COALESCE(duration_ms, 0)) / 60000,
    1
  ) AS total_minutes_listened,
  COUNT(DISTINCT track_id) AS unique_tracks,
  COUNT(DISTINCT artist_id) AS unique_artists,
  MIN(played_at) AS first_recorded_play,
  MAX(played_at) AS last_recorded_play
FROM stg_track_plays;