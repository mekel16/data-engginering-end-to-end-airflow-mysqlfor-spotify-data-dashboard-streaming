<div align="center">

# data engginering end to end airflow mysql for spotify data dashboard streaming


_tools i use_

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




https://github.com/user-attachments/assets/f3771f85-47fb-47c5-a2bb-bdfa24191930




