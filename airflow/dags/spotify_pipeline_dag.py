"""
Airflow DAG untuk menjalankan pipeline Spotify ke MySQL.

Urutan task:
1. Membuat database dan tabel
2. Mengambil data Spotify ke raw layer
3. Membuat tabel staging dan mart
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

load_dotenv(PROJECT_ROOT / ".env")


from airflow import DAG
from airflow.operators.python import PythonOperator


def ensure_mysql_tables() -> None:
    """Membuat database dan tabel raw jika belum tersedia."""
    from spotify_pipeline.config import Settings
    from spotify_pipeline.mysql_store import MySQLStore

    settings = Settings.from_env()
    MySQLStore(settings).ensure_schema()


def extract_spotify_data() -> int:
    """Mengambil data Spotify dan menyimpannya ke raw MySQL."""
    from spotify_pipeline.extract import extract_to_mysql

    inserted = extract_to_mysql()
    print(f"Snapshot raw baru: {inserted}")
    return inserted


def transform_spotify_data() -> None:
    """Membangun tabel staging dan mart."""
    from spotify_pipeline import transform

    # Mendukung dua nama fungsi dari versi project berbeda.
    transform_function = getattr(transform, "transform_to_marts", None)

    if transform_function is None:
        transform_function = getattr(transform, "build_marts", None)

    if transform_function is None:
        raise AttributeError(
            "Tidak ditemukan fungsi transform_to_marts atau build_marts "
            "di spotify_pipeline.transform."
        )

    transform_function()


default_args = {
    "owner": "spotify-analytics",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="spotify_personal_analytics",
    description="Extract Spotify data and build MySQL analytics marts.",
    start_date=datetime(2026, 1, 1),
    schedule="0 */6 * * *",
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["spotify", "mysql", "etl"],
) as dag:

    ensure_tables = PythonOperator(
        task_id="ensure_mysql_tables",
        python_callable=ensure_mysql_tables,
    )

    extract = PythonOperator(
        task_id="extract_spotify_to_mysql_raw",
        python_callable=extract_spotify_data,
    )

    transform = PythonOperator(
        task_id="build_staging_and_marts",
        python_callable=transform_spotify_data,
    )

    ensure_tables >> extract >> transform