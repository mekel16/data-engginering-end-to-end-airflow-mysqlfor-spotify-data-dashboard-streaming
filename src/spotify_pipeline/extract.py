from .config import Settings
from .mysql_store import MySQLStore
from .spotify_client import SpotifyClient


def extract_to_mysql() -> int:
    """
    Mengambil data dari Spotify dan menyimpan
    response mentah ke MySQL.
    """

    settings = Settings.from_env()

    store = MySQLStore(settings)

    watermark = store.latest_played_at()

    spotify = SpotifyClient(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
        refresh_token=settings.spotify_refresh_token,
    )

    snapshots = spotify.collect(
        recently_played_after=watermark
    )

    return store.insert_raw_snapshots(
        snapshots
    )