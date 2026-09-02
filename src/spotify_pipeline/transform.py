from .config import Settings
from .mysql_store import MySQLStore


def transform_to_marts() -> None:
    """
    Mengubah raw data menjadi staging dan mart.
    """

    settings = Settings.from_env()

    store = MySQLStore(settings)

    store.run_transformations()