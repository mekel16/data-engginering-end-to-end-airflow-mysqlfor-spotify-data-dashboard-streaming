import os

from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


class ConfigurationError(RuntimeError):
    """
    Error untuk konfigurasi yang belum lengkap.
    """


def required_env(name: str) -> str:
    """
    Mengambil environment variable yang wajib ada.
    """

    value = os.getenv(name, "").strip()

    if not value:
        raise ConfigurationError(
            f"Environment variable {name} belum diisi."
        )

    return value


@dataclass(frozen=True)
class Settings:
    """
    Seluruh konfigurasi pipeline.
    """

    # Spotify
    spotify_client_id: str
    spotify_client_secret: str
    spotify_refresh_token: str

    # MySQL
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Membaca konfigurasi dari file .env
        atau environment variable.
        """

        return cls(
            spotify_client_id=required_env(
                "SPOTIFY_CLIENT_ID"
            ),
            spotify_client_secret=required_env(
                "SPOTIFY_CLIENT_SECRET"
            ),
            spotify_refresh_token=required_env(
                "SPOTIFY_REFRESH_TOKEN"
            ),
            mysql_host=os.getenv(
                "MYSQL_HOST",
                "127.0.0.1",
            ),
            mysql_port=int(
                os.getenv(
                    "MYSQL_PORT",
                    "3306",
                )
            ),
            mysql_user=os.getenv(
                "MYSQL_USER",
                "root",
            ),
            mysql_password=os.getenv(
                "MYSQL_PASSWORD",
                "",
            ),
            mysql_database=os.getenv(
                "MYSQL_DATABASE",
                "spotify_analytics",
            ),
        )