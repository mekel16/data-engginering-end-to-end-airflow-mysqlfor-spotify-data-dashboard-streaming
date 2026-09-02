from .config import Settings
from .extract import extract_to_mysql
from .mysql_store import MySQLStore
from .transform import transform_to_marts


def main() -> None:
    """
    Menjalankan pipeline lengkap:
    1. Buat schema
    2. Extract Spotify
    3. Transform ke mart
    """

    settings = Settings.from_env()

    store = MySQLStore(settings)

    print("Membuat database dan tabel...")
    store.ensure_schema()

    print("Mengambil data Spotify...")
    inserted_count = extract_to_mysql()

    print(
        f"Snapshot raw baru: {inserted_count}"
    )

    print("Membangun tabel staging dan mart...")
    transform_to_marts()

    print("Pipeline selesai.")


if __name__ == "__main__":
    main()