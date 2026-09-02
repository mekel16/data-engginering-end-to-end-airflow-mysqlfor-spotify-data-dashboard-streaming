# Portofolio Data Engineering — Personal Spotify Analytics Pipeline

> Draf tulisan untuk LinkedIn / Medium. Sesuaikan bagian `[Nama Anda]`, `[link]`, dan detail personal.

---

## Judul Pilihan

- **"Membangun Pipeline Data Engineering Personal: Menganalisis Perilaku Mendengarkan Musik Saya dengan Spotify API, MySQL & Airflow"**
- **"Dari API ke Insight: End-to-End Data Pipeline untuk Musik Spotify"**

---

## Pendahuluan

Sebagai calon data engineer, saya percaya bahwa cara terbaik untuk belajar adalah dengan membangun sesuatu yang nyata — bukan sekadar mengikuti tutorial. Salah satu cara yang paling menyenangkan sekaligus menantang adalah menganalisis **data pribadi saya sendiri di Spotify**: lagu apa yang paling sering saya putar, artis favorit saya, berapa lama saya mendengarkan musik setiap hari, hingga kebiasaan mendengarkan saya.

Karena itu saya membangun **sebuah pipeline data end-to-end** yang secara otomatis menarik data aktivitas mendengarkan Spotify saya, menyimpannya secara terstruktur, dan mengubahnya menjadi analitik siap pakai.

---

## Masalah yang Ingin Saya Selesaikan

Spotify menyediakan data pribadi pengguna melalui **Web API**-nya, sebuah endpoint yang berisi *recently played*, *top tracks*, *top artists*, dan *playlists*. Namun data mentah ini:

- **Tidak terstruktur** (berupa JSON mentah)
- **Tidak konsisten** antar snapshot waktu
- **Tidak mudah dianalisis** tanpa transformasi
- **Tidak terjadwal** — perlu dijalankan berkala agar selalu update

Tantangannya: bagaimana mengubah data mentah ini menjadi sebuah **data warehouse mini** yang bisa langsung dianalisis, misalnya untuk menjawab:

- Siapa artis favorit saya bulan ini?
- Berapa menit musik yang saya dengarkan per hari?
- Berapa sesi mendengarkan yang saya lakukan?
- Kapan saya paling aktif mendengarkan musik?

---

## Arsitektur & Tech Stack

Saya membangun pipeline dengan pendekatan **ETL** (Extract-Transform-Load) dengan **medallion architecture** (raw → staging → mart):

```
[Spotify Web API]
       │
       ▼  (Extract - API call via OAuth refresh token)
[MySQL Raw Layer]  ← raw_spotify_api_responses (JSON mentah + checksum)
       │
       ▼  (Transform - JSON_TABLE parsing + dedup)
[MySQL Staging Layer]  ← stg_track_plays, stg_top_tracks, stg_top_artists, stg_playlists
       │
       ▼  (Load / Aggregation)
[MySQL Mart Layer]  ← mrt_daily_listening, mrt_top_tracks, mrt_top_artists, mrt_overview, mrt_recent_activity
       ▲
       │  (Scheduling - Airflow DAG, setiap 6 jam)
[Apache Airflow]
```

**Tech Stack:**
- **Bahasa:** Python 3.12
- **Orkestrasi:** Apache Airflow
- **Database / DW:** MySQL (InnoDB, utf8mb4)
- **API:** Spotify Web API (OAuth 2.0 dengan refresh token)
- **Transformasi:** SQL (JSON_TABLE, window functions, CTE)
- **Manajemen paket:** pyproject.toml (setuptools) + pip

---

## Mengapa Pilihan Teknologi Ini?

1. **MySQL**: Ringan, mudah diset up, tetapi tetap mendukung **JSON_TABLE** dan **window functions** — cukup kuat untuk membangun warehouse mini. Cocok untuk skala personal.
2. **Airflow**: Standar industri untuk orkestrasi pipeline. Saya menggunakannya untuk menjadwalkan ekstraksi tiap 6 jam, lengkap dengan *retry* dan *dependency* antar task.
3. **Medallion architecture**: Memisahkan raw, staging, dan mart — praktik terbaik yang bisa saya tunjukkan di project kecil ini.

---

## Bagaimana Pipeline Bekerja

Pipeline saya terdiri dari **3 tahap utama** yang dijalankan sebagai alur task di Airflow:

### 1. Extract (Raw Layer)
Melakukan request ke endpoint Spotify (`recently_played`, `top_tracks`, `top_artists`, `playlists`) menggunakan token OAuth. Setiap respons JSON disimpan sebagai **satu baris snapshot** di tabel `raw_spotify_api_responses`, lengkap dengan:

- **`raw_checksum`** — untuk mencegah duplikasi data
- **`fetched_at`** — timestamp kapan data diambil
- **`request_params_json`** — konteks request (mis. rentang waktu API)

Saya juga menggunakan **watermark**: hanya menarik data `recently_played` setelah waktu terakhir yang saya miliki, sehingga ringkas dan efisien.

### 2. Transform (Staging Layer)
Di sini saya mengubah JSON mentah menjadi tabel relasional yang bersih. Teknik kunci yang saya gunakan:

- **`JSON_TABLE`** di MySQL untuk "flatten" struktur JSON bertingkat menjadi baris/kolom
- **`ROW_NUMBER()` untuk deduplikasi** — karena endpoint dapat mengembalikan data yang tumpang tindih antar snapshot, saya memilih baris terbaru per event (`row_num = 1`)
- Menghasilkan **`play_event_id`** deterministik (berbasis MD5) agar setiap event listen bisa diidentifikasi secara unik

Hasilnya: tabel `stg_track_plays`, `stg_top_tracks`, `stg_top_artists`, `stg_playlists` yang bersih dan siap dianalisis.

### 3. Load & Aggregation (Mart Layer)
Tahap terakhir membangun tabel analitik (`mrt_*`) yang siap untuk visualisasi / BI. Salah satu bagian yang paling saya banggakan adalah **listening sessionization**:

> Saya mendefinisikan **satu "sesi mendengarkan"** dengan melihat selisih waktu antar play (`LAG`). Jika jeda antar lagu lebih dari 30 menit, saya menganggapnya sebagai sesi baru. Ini memungkinkan saya menghitung berapa sesi mendengarkan per hari — metrik yang tidak disediakan langsung oleh Spotify.

Mart yang dihasilkan:
- **`mrt_daily_listening`** — jumlah play, menit didengarkan, jumlah sesi per hari
- **`mrt_top_tracks`** — ranking lagu berdasarkan jumlah play & menit
- **`mrt_top_artists`** — ranking artis beserta menit & jumlah lagu unik
- **`mrt_overview`** — ringkasan total
- **`mrt_recent_activity`** — 100 aktivitas terakhir

---

## Hasil / Insight yang Diperoleh

Dari pipeline ini, saya bisa menjawab pertanyaan analitik seperti:

- Total menit musik yang saya dengarkan sejak data mulai direkam
- Lagu dan artis paling sering diputar
- Pola mendengarkan harian (berapa sesi, berapa menit)
- Top tracks & artists untuk rentang waktu tertentu (short/medium/long term)

*(Tambahkan contoh angka nyata Anda di sini, mis. "Secara total saya mendengarkan X menit musik dan Y lagu unik.")*

---

## Keterampilan yang Saya Tunjukkan

Project ini melatih dan menunjukkan keterampilan penting seorang data engineer:

| Area | Detail |
|------|--------|
| **ETL / Pipeline** | Extract, transform, load end-to-end |
| **API Integration** | OAuth 2.0, rate handling, refresh token |
| **Data Modeling** | Medallion architecture (raw/staging/mart) |
| **SQL (Advanced)** | JSON_TABLE, window functions, CTE, deduplication, sessionization |
| **Orkestrasi** | Airflow DAG dengan dependency & retry |
| **Versioning & Paket** | Git, pyproject.toml, packaging Python |
| **Data Quality** | Checksum dedup, watermark, idempotent DDL |

---

## Struktur Project

```
spotify-personal-analytics/
├── src/spotify_pipeline/
│   ├── config.py          # Konfigurasi dari environment (.env)
│   ├── spotify_client.py  # Klien API Spotify (OAuth)
│   ├── extract.py         # Ekstraksi data alias raw layer
│   ├── transform.py       # Transformasi ke staging & mart
│   ├── mysql_store.py     # Interaksi dengan MySQL
│   └── pipeline.py        # Orkestrasi pipeline (CLI)
├── airflow/dags/
│   └── spotify_pipeline_dag.py  # DAG Airflow
├── sql/
│   ├── 001_create_tables.sql   # Skema raw layer
│   └── 002_transform.sql       # Staging & mart
├── pyproject.toml
└── requirements.txt
```

*(Link ke repo: [link repository Anda])*

---

## Yang Ingin Saya Pelajari Berikutnya

- **Visualisasi** data mart dengan Superset / Metabase / tabel laporan
- **Incremental loading** yang lebih efisien dengan partitions
- **Monitoring & alerting** kualitas pipeline
- Migrasi ke **cloud** (mis. Snowflake / BigQuery + dbt) untuk skala yang lebih besar

---

## Kesimpulan

Project ini bukan sekadar "menarik data dari API". Ia menunjukkan pemahaman saya tentang **seluruh siklus hidup data**: dari sumber mentah, proses transformasi yang bersih, hingga produk analitik yang siap digunakan — diorkestrasi secara otomatis dengan standar industri.

Saya sangat antusias untuk terus mengembangkan keterampilan sebagai **Data Engineer**, dan project ini adalah salah satu fondasi yang membuktikannya.

Jika Anda ingin berdiskusi lebih lanjut seputar data engineering, jangan ragu untuk menghubungi saya! ✋

---

*— [Nama Anda] —*
*[LinkedIn] | [GitHub] | [Email]*
