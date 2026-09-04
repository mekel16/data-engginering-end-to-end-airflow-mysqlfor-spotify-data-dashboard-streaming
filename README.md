<div align="center">

# End-to-End Data Engineering Pipeline for Personal Spotify Streaming Analytics

*tools i use*

Python · MySQL · Apache Airflow · Spotify Web API

</div>

<div align="center">
  <!-- Baris 1 -->
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/MySQL-005C84?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL">
  <br>
  <!-- Baris 2 -->
  <img src="https://img.shields.io/badge/Apache_Airflow-017CEE?style=for-the-badge&logo=Apache-Airflow&logoColor=white" alt="Apache Airflow">
  <img src="https://img.shields.io/badge/Spotify_API-1DB954?style=for-the-badge&logo=spotify&logoColor=white" alt="Spotify Web API">
</div>

---

<div align="center">

## Proses

<table>
  <tr>
    <td align="center">
      <h2>Extract Load Transform</h2>
      <img width="333" height="404" alt="Frame 9 (2)" src="https://github.com/user-attachments/assets/14663320-f75c-437e-b4e2-f941eed90712" />
    </td>
    <td align="center">
      <h2>Dashboard (data dari database update tiap jam 6 sore)</h2>
      <img width="640" height="400" alt="image" src="https://github.com/user-attachments/assets/51d66e5e-2e65-4907-a243-d7fcf1a9c92e" />
    </td>
  </tr>
</table>

</div>

```
Staging (stg) → data flatten & bersih dari JSON mentah, tapi masih per-row/granular, belum diagregasi.
- stg_track_plays → setiap play event satu baris
- stg_top_tracks → setiap lagu per time_range satu baris
- stg_top_artists → setiap artist per time_range satu baris
- stg_playlists → setiap playlist satu baris

Mart (mrt) → data diagregasi & siap pakai untuk analisis/dashboard.
- mrt_daily_listening → total play per hari, sesi, menit
- mrt_top_tracks → rangking berdasarkan total play count
- mrt_top_artists → rangking berdasarkan total play count
- mrt_overview → single-row KPI summary
```

<div align="center">

## Berikut bagaimana projek ini dibuat dan untuk digunakan.

</div>

### Setup Spotify Developer + OAuth

1. Buat app di Spotify Developer Dashboard (https://developer.spotify.com/dashboard)
2. akan menDapatkan client_id, client_secret
3. Simpan credentials tersebut di file .env lalu,
4. run (get_refresh_token.py) untuk dapat *refresh_token*
5. copy *refresh_token* dan masukkan lagi di .env

Tahap terebut akan mendapatkan *refresh_token*

### 1. Setup Spotify Developer + OAuth

Project ini menggunakan **Spotify Web API** sebagai sumber data utama. Sebelum pipeline dapat dijalankan, aplikasi harus memiliki kredensial OAuth dari Spotify.

#### Langkah setup

1. Buat aplikasi pada Spotify Developer Dashboard.
2. Dapatkan:

   * `client_id`
   * `client_secret`
3. Implementasikan OAuth flow menggunakan `get_refresh_token.py`.
4. Jalankan script tersebut untuk mendapatkan `refresh_token`.
5. Simpan seluruh credentials di file `.env`.

Contoh struktur `.env`:

```env
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REFRESH_TOKEN=your_refresh_token
```

`refresh_token` digunakan oleh aplikasi untuk mendapatkan access token baru ketika melakukan request ke Spotify API.

Dengan pendekatan ini, pipeline tidak perlu melakukan login Spotify secara manual setiap kali proses extraction dijalankan.

---

### 2. Build Spotify API Client

Setelah credentials tersedia, project membuat sebuah client khusus untuk berkomunikasi dengan Spotify Web API.

File utama:

```text
config.py
spotify_client.py
```

#### `config.py`

`config.py` bertanggung jawab membaca konfigurasi dari `.env`, sehingga credentials tidak ditulis langsung di source code.

#### `spotify_client.py`

File ini menjadi layer utama untuk komunikasi dengan Spotify API.

Beberapa tanggung jawabnya:

* melakukan OAuth token refresh
* mendapatkan access token
* menyediakan generic method `get()`
* melakukan request ke berbagai endpoint Spotify
* menangani rate limit dari API
* menyediakan mekanisme pengambilan snapshot data

Secara sederhana:

```text
.env
 ↓
config.py
 ↓
spotify_client.py
 ↓
Spotify Web API
```

#### Manual test

Sebelum masuk ke pipeline, API client perlu diuji terlebih dahulu.

Test sederhana dilakukan dengan memanggil endpoint:

```text
/me
```

Jika response berhasil dan profile Spotify dapat diterima, berarti:

```text
OAuth
  ↓
Access Token
  ↓
API Request
  ↓
Response OK
```

dan Spotify API client siap digunakan.

---

### 3. Buat MySQL Schema — Raw Layer

Setelah koneksi ke Spotify API berhasil, project menyiapkan database MySQL sebagai tempat penyimpanan data mentah.

Schema awal dibuat melalui:

```text
001_create_tables.sql
```

Pada tahap ini dibuat tabel:

```text
raw_spotify_api_responses
```

Tabel ini berfungsi sebagai **raw layer**, yaitu tempat menyimpan response asli dari Spotify API sebelum dilakukan transformasi.

Struktur utamanya mencakup:

```text
UUID Primary Key
Checksum
Payload JSON
```

Konsep penyimpanannya:

```text
Spotify API
     ↓
Raw JSON Response
     ↓
MySQL
     ↓
raw_spotify_api_responses
```

Data pada layer ini **belum mengalami transformasi menjadi tabel analitik**.

Tujuannya adalah mempertahankan response asli dari API sehingga data dapat ditelusuri kembali apabila diperlukan.

---

### 4. Build Extract + Load

Tahap berikutnya adalah membangun proses **Extract + Load**.

Pada tahap ini Spotify API dipanggil, response dikumpulkan, kemudian disimpan ke MySQL sebagai raw data.

File yang terlibat:

```text
spotify_client.py
mysql_store.py
extract.py
```

#### `spotify_client.py`

Method `snapshot()` digunakan untuk membungkus response API menjadi objek:

```text
SpotifySnapshot
```

Kemudian method `collect()` digunakan untuk memanggil seluruh endpoint yang dibutuhkan project, seperti:

* profile
* recently played tracks
* top tracks
* top artists
* playlists
* dan endpoint Spotify lainnya yang digunakan oleh pipeline

Alur pengambilan data:

```text
Spotify API
     ↓
collect()
     ↓
SpotifySnapshot
```

#### `mysql_store.py`

Method:

```text
insert_raw_snapshots()
```

bertugas menyimpan snapshot ke MySQL.

Sebelum disimpan, payload JSON:

1. di-serialize
2. dibuatkan checksum menggunakan **SHA-256**
3. kemudian di-insert ke tabel raw

Konsepnya:

```text
SpotifySnapshot
      ↓
Serialize JSON
      ↓
SHA-256 Checksum
      ↓
MySQL Raw Layer
```

#### `extract.py`

`extract.py` bertindak sebagai orchestrator untuk proses extraction.

Alurnya:

```text
collect()
   ↓
insert_raw_snapshots()
   ↓
MySQL
```

#### Test extraction

Setelah `extract.py` dijalankan, tabel:

```text
raw_spotify_api_responses
```

harus sudah memiliki data.

Dengan demikian dapat dipastikan bahwa proses:

```text
Spotify API → Extract → Load → MySQL
```

berhasil.

---

### 5. Buat Transform SQL

Setelah raw data tersedia di MySQL, tahap berikutnya adalah melakukan transformasi.

Seluruh transformasi utama berada pada:

```text
002_transform.sql
```

Ini merupakan salah satu bagian paling besar dan kompleks dalam project karena response JSON dari Spotify harus diubah menjadi struktur relational yang dapat digunakan untuk analisis dan dashboard.

Transformasi dibagi menjadi dua layer:

```text
RAW
 ↓
STAGING
 ↓
MART
```

#### Staging Layer

Pada staging layer, JSON mentah di-flatten menggunakan:

```sql
JSON_TABLE
```

Data kemudian diubah menjadi tabel relational.

Contohnya:

```text
Raw JSON
   ↓
JSON_TABLE
   ↓
stg_track_plays
stg_top_tracks
stg_top_artists
stg_playlists
```

Selain flattening, dilakukan juga proses deduplication menggunakan:

```sql
ROW_NUMBER()
```

Tujuannya adalah memastikan data yang sama tidak menghasilkan record duplicate pada staging layer.

Staging tetap mempertahankan granularitas data.

Contohnya:

```text
1 play event = 1 row
1 track      = 1 row
1 artist     = 1 row
1 playlist   = 1 row
```

#### Mart Layer

Setelah staging selesai, data kemudian diagregasi menjadi mart.

Beberapa teknik SQL yang digunakan antara lain:

```text
GROUP BY
SUM()
COUNT()
LAG()
```

`LAG()` digunakan untuk membantu melakukan analisis antar-event, termasuk menentukan pola/session listening berdasarkan urutan aktivitas.

Hasil akhirnya adalah data yang sudah siap digunakan oleh dashboard.

```text
Staging
   ↓
Aggregation
   ↓
Mart
   ↓
Dashboard
```

#### Hasil Transformasi

Mart layer menghasilkan beberapa tabel utama:

```text
mrt_daily_listening
mrt_top_tracks
mrt_top_artists
mrt_overview
```

**`mrt_daily_listening`**

Berisi ringkasan aktivitas listening per hari, termasuk total play, session, dan durasi dalam menit.

**`mrt_top_tracks`**

Berisi ranking lagu berdasarkan total play count.

**`mrt_top_artists`**

Berisi ranking artist berdasarkan total play count.

**`mrt_overview`**

Berisi single-row KPI summary yang digunakan untuk menampilkan overview pada dashboard.

#### Test Transform

SQL transformation dapat dijalankan secara manual di MySQL terlebih dahulu.

Setelah query selesai dijalankan, staging dan mart table diperiksa untuk memastikan hasil flattening, deduplication, dan aggregation sudah sesuai.

---

### 6. Build Transform Python Wrapper

Walaupun transformation utama dilakukan menggunakan SQL, project tetap menyediakan Python wrapper agar proses transformasi dapat dipanggil sebagai bagian dari pipeline.

File yang digunakan:

```text
mysql_store.py
transform.py
```

#### `mysql_store.py`

Method:

```text
run_transformations()
```

bertugas:

1. membaca file `002_transform.sql`
2. menjalankan SQL transformation
3. mengeksekusi seluruh proses staging dan mart di MySQL

#### `transform.py`

`transform.py` hanya bertugas memanggil:

```text
run_transformations()
```

Dengan demikian Python tidak melakukan transformasi data secara langsung.

Arsitekturnya:

```text
transform.py
     ↓
run_transformations()
     ↓
002_transform.sql
     ↓
MySQL
     ↓
Staging + Mart
```

Pendekatan ini membuat logic transformation tetap terpusat di SQL, sementara Python berfungsi sebagai trigger/orchestrator.

---

### 7. Pipeline CLI

Setelah extraction dan transformation selesai dibuat secara terpisah, keduanya digabungkan menjadi satu pipeline.

File utama:

```text
pipeline.py
```

Pipeline menggabungkan seluruh proses dengan urutan:

```text
ensure_schema()
      ↓
extract()
      ↓
transform()
```

Secara lengkap:

```text
Check MySQL Schema
       ↓
Spotify API
       ↓
Extract
       ↓
Raw Layer
       ↓
Transform SQL
       ↓
Staging
       ↓
Mart
       ↓
Dashboard
```

Pipeline dapat dijalankan secara manual melalui terminal.

Tujuannya adalah memastikan seluruh proses dapat berjalan secara end-to-end tanpa harus menjalankan setiap script secara manual satu per satu.

---

### 8. Orchestrate dengan Apache Airflow

Setelah pipeline CLI berhasil berjalan, proses tersebut kemudian di-orchestrate menggunakan **Apache Airflow**.

File DAG:

```text
spotify_pipeline_dag.py
```

DAG mendefinisikan tiga task utama:

```text
ensure_schema
      ↓
extract
      ↓
transform
```

Dependency antar-task memastikan transform tidak dijalankan sebelum extraction selesai.

Secara visual:

```text
┌─────────────────┐
│  ensure_schema  │
└────────┬────────┘
         ↓
┌─────────────────┐
│     extract     │
└────────┬────────┘
         ↓
┌─────────────────┐
│    transform    │
└─────────────────┘
```

Pipeline dijadwalkan menggunakan:

```text
0 */6 * * *
```

Artinya pipeline dijalankan **setiap 6 jam**.

Dengan scheduling ini, data Spotify pada database akan terus diperbarui secara otomatis sehingga dashboard dapat menampilkan data terbaru sesuai dengan hasil pipeline.

#### Airflow Setup

Environment Airflow disiapkan melalui:

```text
airflow_home/
```

Kemudian dilakukan proses:

```text
Airflow DB initialization
        ↓
Create Airflow user
        ↓
Configure DAG
        ↓
Run Scheduler
        ↓
Run Webserver
```

Setelah Airflow aktif, `spotify_pipeline_dag.py` akan menjalankan pipeline berdasarkan schedule yang telah ditentukan.

---

## End-to-End Architecture

Secara keseluruhan, project ini membangun pipeline data dari Spotify API sampai menjadi data yang siap digunakan oleh dashboard.

```text
                    SPOTIFY WEB API
                          │
                          ▼
                ┌───────────────────┐
                │  Spotify API      │
                │  Client           │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │      EXTRACT      │
                │   collect()       │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │     RAW LAYER     │
                │ MySQL             │
                │ JSON Response     │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │  STAGING LAYER    │
                │ JSON_TABLE        │
                │ Deduplication     │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │    MART LAYER     │
                │ Aggregation       │
                │ KPI & Ranking     │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │     DASHBOARD     │
                └───────────────────┘

                 ↑
                 │
          Apache Airflow
        Orchestration & Schedule
```

---

## Project Flow

Secara sederhana, keseluruhan proses project dapat diringkas menjadi:

```text
Spotify Web API
      ↓
OAuth Authentication
      ↓
Spotify API Client
      ↓
Extract
      ↓
Raw MySQL
      ↓
JSON Flattening
      ↓
Staging
      ↓
Deduplication
      ↓
Aggregation
      ↓
Mart
      ↓
Dashboard
```

Apache Airflow berfungsi sebagai orchestration layer yang mengatur kapan seluruh proses tersebut dijalankan dan memastikan dependency antar-task berjalan sesuai urutan.

---

## Data Architecture

Project ini menggunakan pendekatan **Raw → Staging → Mart**.

```text
RAW
│
└── raw_spotify_api_responses
        │
        ▼
STAGING
│
├── stg_track_plays
├── stg_top_tracks
├── stg_top_artists
└── stg_playlists
        │
        ▼
MART
│
├── mrt_daily_listening
├── mrt_top_tracks
├── mrt_top_artists
└── mrt_overview
```

Pendekatan ini memisahkan data berdasarkan tingkat transformasinya.

**Raw** menyimpan response asli dari Spotify.

**Staging** menyimpan data yang sudah di-flatten dan dibersihkan tetapi masih dalam bentuk granular.

**Mart** menyimpan data yang sudah diagregasi dan siap dikonsumsi oleh dashboard.

---

## Technologies

| Technology      | Usage                                           |
| --------------- | ----------------------------------------------- |
| Python          | API client, extraction, orchestration wrapper   |
| Spotify Web API | Source data                                     |
| MySQL           | Data storage dan SQL transformation             |
| Apache Airflow  | Pipeline orchestration dan scheduling           |
| SQL             | Data transformation, aggregation, deduplication |
| JSON            | Raw API response format                         |
| SHA-256         | Data checksum / integrity identification        |

---

## Kesimpulan

Project ini merupakan implementasi **end-to-end data engineering pipeline** menggunakan Spotify Web API sebagai sumber data.

Pipeline tidak hanya mengambil data dari API, tetapi juga membangun seluruh proses data engineering mulai dari authentication, extraction, raw data storage, transformation, aggregation, hingga orchestration menggunakan Apache Airflow.

Hasil akhirnya adalah data Spotify yang terstruktur di dalam MySQL dan siap digunakan oleh dashboard untuk melakukan monitoring serta analisis aktivitas listening.

```text
API
 ↓
Extract
 ↓
Raw
 ↓
Staging
 ↓
Mart
 ↓
Dashboard

        ↑
   Apache Airflow
```
<div align="center">
  
### TENGSSSSS

https://github.com/user-attachments/assets/a08961d7-360c-45c5-97b3-9b2ebb216172

</div>


