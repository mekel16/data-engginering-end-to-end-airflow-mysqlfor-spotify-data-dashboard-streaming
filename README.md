<div align="center">

# 🎧 Spotify Personal Analytics

**End-to-End Data Engineering Pipeline untuk Menganalisis Perilaku Mendengarkan Musik Pribadi di Spotify**

Python · MySQL · Apache Airflow · Spotify Web API

</div>

---

## 📌 Ikhtisar

Project ini adalah **pipeline data end-to-end** yang secara otomatis menarik data aktivitas mendengarkan Spotify, menyimpannya secara terstruktur di MySQL, dan mengubahnya menjadi **mart data analitik** yang siap digunakan.

Pipeline dibangun dengan pendekatan **ETL** dan **medallion architecture** (raw → staging → mart), diorkestrasi otomatis menggunakan **Apache Airflow**.

### Pertanyaan Analitik yang Dapat Dijawab

- Siapa artis & lagu favorit saya?
- Berapa menit musik yang saya dengarkan per hari?
- Berapa sesi mendengarkan yang saya lakukan?
- Apa top tracks & artists untuk rentang short / medium / long term?

---

## 🏗️ Arsitektur

```
┌──────────────────────┐
│    Spotify Web API   │
└──────────┬───────────┘
           │ Extract (OAuth 2.0 + refresh token)
           ▼
┌──────────────────────┐   raw layer
│   Raw MySQL Layer    │   raw_spotify_api_responses
└──────────┬───────────┘   (JSON mentah + checksum + watermark)
           │ Transform (JSON_TABLE, dedup, window functions)
           ▼
┌──────────────────────┐   staging layer
│  Staging MySQL Layer │   stg_track_plays · stg_top_tracks
└──────────┬───────────┘   stg_top_artists · stg_playlists
           │ Load / Aggregation
           ▼
┌──────────────────────┐   mart layer
│     Mart Layer       │   mrt_daily_listening · mrt_top_tracks
└──────────┬───────────┘   mrt_top_artists · mrt_overview
           │              mrt_recent_activity
           ▲
           │ Scheduling (setiap 6 jam)
┌──────────────────────┐
│  Apache Airflow DAG  │
└──────────────────────┘
```

Pipeline terdiri dari 3 tahap yang dijalankan sebagai task di Airflow:

```
ensure_mysql_tables  →  extract_spotify_to_mysql_raw  →  build_staging_and_marts
```

---

## 🧰 Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Bahasa | Python 3.11+ |
| Orkestrasi | Apache Airflow |
| Database / Warehouse | MySQL (InnoDB, utf8mb4) |
| Sumber Data | Spotify Web API (OAuth 2.0) |
| Transformasi | SQL (JSON_TABLE, window functions, CTE) |
| Manajemen Paket | pyproject.toml (setuptools) |

---

## 📁 Struktur Project

```
spotify-personal-analytics/
├── src/spotify_pipeline/
│   ├── config.py              # Konfigurasi dari .env
│   ├── spotify_client.py      # Klien Spotify API (OAuth, retry, rate limit)
│   ├── extract.py             # Ekstraksi data → raw layer
│   ├── transform.py           # Transformasi → staging & mart
│   ├── mysql_store.py         # Repository interaksi MySQL
│   └── pipeline.py            # Orkestrasi pipeline (CLI)
├── airflow/dags/
│   └── spotify_pipeline_dag.py  # DAG Airflow
├── sql/
│   ├── 001_create_tables.sql   # Skema raw layer
│   └── 002_transform.sql       # Staging & mart (semua transformasi)
├── pyproject.toml
├── requirements.txt
└── .env                        # Konfigurasi (JANGAN di-commit)
```

---

## ✨ Fitur Utama

### Extract
- **OAuth 2.0** dengan refresh token — akses berkelanjutan tanpa login manual
- **Rate limit handling** — otomatis menunggu sesual nilai `Retry-After` (HTTP 429)
- **Watermark (incremental load)** — hanya menarik `recently_played` setelah waktu terakhir
- **Checksum deduplication** — `raw_checksum` (SHA-256) mencegah snapshot terduplikasi

### Transform
- **JSON_TABLE** — "flatten" JSON bertingkat Spotify menjadi tabel relasional
- **Deduplication** dengan `ROW_NUMBER()` — memilih baris terbaru per event
- **Deterministic `play_event_id`** (MD5) untuk identifikasi unik setiap play
- **Sessionization** — mendefinisikan sesi mendengarkan (jeda > 30 menit = sesi baru)
- **Idempotent DDL** — aman dijalankan berulang kali

### Mart yang Dihasilkan
| Tabel | Konten |
|-------|--------|
| `mrt_daily_listening` | Play count, menit, sesi per hari |
| `mrt_top_tracks` | Ranking lagu berdasarkan play & menit |
| `mrt_top_artists` | Ranking artis + menit + lagu unik |
| `mrt_overview` | Ringkasan total (KPI keseluruhan) |
| `mrt_recent_activity` | 100 aktivitas terakhir |

---

## 🚀 Cara Menjalankan

### 1. Persiapan

#### Prasyarat
- Python 3.11+
- MySQL (mis. XAMPP) — server berjalan di lokal

#### Setup Spotify Credentials
1. Buat app di [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Dapatkan `Client ID` & `Client Secret`
3. Dapatkan `Refresh Token` (gunakan `get_refresh_token.py`)

#### Setup Environment
Salin variabel berikut ke file `.env`:

```bash
# Spotify
SPOTIFY_CLIENT_ID=xxx
SPOTIFY_CLIENT_SECRET=xxx
SPOTIFY_REFRESH_TOKEN=xxx

# MySQL
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=spotify_analytics
```

### 2. Install

```bash
# Buat virtual environment
python -m venv .venv

# Aktifkan (.venv\Scripts\activate di Windows, atau source .venv/bin/activate di Linux/Mac)
pip install -e .
```

### 3. Jalankan Pipeline (Tanpa Airflow)

```bash
spotify-pipeline
```

Perintah ini akan: membuat schema → ekstraksi data → membangun staging & mart.

### 4. Jalankan dengan Airflow

```bash
export AIRFLOW_HOME=./airflow_home
export AIRFLOW__CORE__DAGS_FOLDER=./airflow/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False

airflow db init
airflow standalone
```

Lalu aktifkan DAG `spotify_personal_analytics` di UI Airflow. DAG terjadwal **setiap 6 jam** (`0 */6 * * *`).

---

## 🧪 Contoh Output / Insight

*(Isi dengan hasil nyata dari data Anda, contoh:)*

> Setelah pipeline berjalan, mart `mrt_overview` menunjukkan total **X menit** musik didengarkan dan **Y lagu unik** sejak data mulai direkam. `mrt_daily_listening` menunjukkan rata-rata **Z menit** per hari.

---

## 🗃️ Data Model (skema singkat)

**Raw layer** — `raw_spotify_api_responses`

| Kolom | Tipe | Deskripsi |
|-------|------|-----------|
| ingestion_id | CHAR(36) | UUID setiap snapshot |
| raw_checksum | CHAR(64) | SHA-256 untuk dedup |
| source | VARCHAR(100) | `recently_played`, `top_tracks_*`, dsb. |
| endpoint | VARCHAR(255) | Endpoint Spotify |
| request_params_json | JSON | Parameter request |
| fetched_at | DATETIME(6) | Waktu data diambil |
| payload_json | JSON | Respons mentah Spotify |

*Transformasi staging & mart lengkap ada di `sql/002_transform.sql`.*

---

## 🔒 Keamanan

- **`.env` tidak di-commit** — berisi kredensial sensitif
- Pastikan menambahkan `.env` ke `.gitignore`

---

## 🗺️ Roadmap

- [ ] Visualisasi mart dengan Metabase / Superset
- [ ] Incremental loading yang lebih efisien (partisi)
- [ ] Monitoring & alerting kualitas data
- [ ] Migrasi ke cloud (Snowflake / BigQuery + dbt)

---

## 📝 Lisensi

Project ini dibuat untuk tujuan **portfolio & pembelajaran pribadi**.

---

<div align="center">
Dibuat dengan 💚 · Michael Spotify Analytics
</div>
