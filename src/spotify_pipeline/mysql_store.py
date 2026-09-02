import hashlib
import json
import re
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import mysql.connector

from .config import Settings
from .spotify_client import SpotifySnapshot


class MySQLStore:
    """
    Repository untuk database MySQL XAMPP.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

        self.validate_identifier(
            settings.mysql_database
        )

    @staticmethod
    def validate_identifier(value: str) -> None:
        """
        Validasi nama database agar aman digunakan
        dalam SQL identifier.
        """

        if not re.fullmatch(
            r"[A-Za-z0-9_]+",
            value,
        ):
            raise ValueError(
                "MYSQL_DATABASE hanya boleh berisi "
                "huruf, angka, dan underscore."
            )

    def connect(
        self,
        include_database: bool = True,
    ):
        """
        Membuka koneksi database.
        """

        config = {
            "host": self.settings.mysql_host,
            "port": self.settings.mysql_port,
            "user": self.settings.mysql_user,
            "password": self.settings.mysql_password,
        }

        if include_database:
            config["database"] = (
                self.settings.mysql_database
            )

        return mysql.connector.connect(**config)

    def ensure_schema(self) -> None:
        """
        Membuat database dan tabel raw.
        """

        database_name = (
            f"`{self.settings.mysql_database}`"
        )

        connection = self.connect(
            include_database=False
        )

        try:
            cursor = connection.cursor()

            cursor.execute(
                f"""
                CREATE DATABASE IF NOT EXISTS {database_name}
                CHARACTER SET utf8mb4
                COLLATE utf8mb4_unicode_ci
                """
            )

            connection.commit()

        finally:
            connection.close()

        sql_file = (
            Path(__file__).resolve().parents[2]
            / "sql"
            / "001_create_tables.sql"
        )

        self.execute_script(
            sql_file.read_text(
                encoding="utf-8"
            )
        )

    def latest_played_at(self):
        """
        Mengambil watermark playback terakhir.
        """

        connection = self.connect()

        try:
            cursor = connection.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT MAX(played_at) AS max_played_at
                FROM stg_track_plays
                """
            )

            row = cursor.fetchone()

            if row:
                return row["max_played_at"]

            return None

        except mysql.connector.Error as error:
            # Tabel belum ada ketika pipeline pertama kali
            # dijalankan.
            if error.errno == 1146:
                return None

            raise

        finally:
            connection.close()

    def insert_raw_snapshots(
        self,
        snapshots: Iterable[SpotifySnapshot],
    ) -> int:
        """
        Menyimpan snapshot Spotify ke raw table.

        raw_checksum digunakan untuk mencegah duplikasi.
        """

        connection = self.connect()
        inserted_count = 0

        sql = """
            INSERT INTO raw_spotify_api_responses (
                ingestion_id,
                raw_checksum,
                source,
                endpoint,
                request_params_json,
                fetched_at,
                payload_json
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            ON DUPLICATE KEY UPDATE
                raw_checksum = raw_checksum
        """

        try:
            cursor = connection.cursor()

            for snapshot in snapshots:
                payload_json = json.dumps(
                    snapshot.payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )

                checksum_input = (
                    f"{snapshot.source}|"
                    f"{payload_json}"
                )

                raw_checksum = hashlib.sha256(
                    checksum_input.encode("utf-8")
                ).hexdigest()

                fetched_at = (
                    self.to_mysql_datetime(
                        snapshot.fetched_at
                    )
                )

                cursor.execute(
                    sql,
                    (
                        str(uuid.uuid4()),
                        raw_checksum,
                        snapshot.source,
                        snapshot.endpoint,
                        json.dumps(
                            snapshot.params,
                            separators=(",", ":"),
                        ),
                        fetched_at,
                        payload_json,
                    ),
                )

                if cursor.rowcount == 1:
                    inserted_count += 1

            connection.commit()

            return inserted_count

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def run_transformations(self) -> None:
        """
        Menjalankan transformasi staging dan mart.
        """

        sql_file = (
            Path(__file__).resolve().parents[2]
            / "sql"
            / "002_transform.sql"
        )

        self.execute_script(
            sql_file.read_text(
                encoding="utf-8"
            )
        )

    def execute_script(
        self,
        sql_script: str,
    ) -> None:
        """
        Mengeksekusi beberapa SQL statement.

        Setiap statement dipisahkan dengan:
        -- STATEMENT
        """

        statements = [
            statement.strip()
            for statement in sql_script.split(
                "-- STATEMENT"
            )
            if statement.strip()
        ]

        connection = self.connect()

        try:
            cursor = connection.cursor()

            for statement in statements:
                cursor.execute(statement)

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    @staticmethod
    def to_mysql_datetime(
        iso_timestamp: str,
    ) -> datetime:
        """
        Mengubah timestamp ISO Spotify menjadi
        datetime UTC untuk MySQL DATETIME.
        """

        parsed = datetime.fromisoformat(
            iso_timestamp.replace(
                "Z",
                "+00:00",
            )
        )

        if parsed.tzinfo:
            parsed = (
                parsed.astimezone(timezone.utc)
                .replace(tzinfo=None)
            )

        return parsed