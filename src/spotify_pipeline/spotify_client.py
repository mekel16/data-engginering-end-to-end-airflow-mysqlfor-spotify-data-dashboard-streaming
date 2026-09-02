import base64
import time

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests


class SpotifyApiError(RuntimeError):
    """
    Error ketika Spotify API mengembalikan response gagal.
    """


@dataclass(frozen=True)
class SpotifySnapshot:
    """
    Satu response mentah dari Spotify API.
    """

    source: str
    endpoint: str
    params: dict[str, Any]
    fetched_at: str
    payload: dict[str, Any]


class SpotifyClient:
    API_BASE_URL = "https://api.spotify.com/v1"
    TOKEN_URL = "https://accounts.spotify.com/api/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

        self.session = requests.Session()
        self.access_token: str | None = None

    def get_access_token(self) -> str:
        """
        Mengambil access token menggunakan refresh token.
        """

        if self.access_token:
            return self.access_token

        basic_credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode(
                "utf-8"
            )
        ).decode("ascii")

        response = self.session.post(
            self.TOKEN_URL,
            headers={
                "Authorization": (
                    f"Basic {basic_credentials}"
                ),
                "Content-Type": (
                    "application/x-www-form-urlencoded"
                ),
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            timeout=30,
        )

        if not response.ok:
            raise SpotifyApiError(
                "Gagal melakukan refresh token Spotify. "
                f"HTTP {response.status_code}: "
                f"{response.text[:300]}"
            )

        token_data = response.json()

        access_token = token_data.get("access_token")

        if not access_token:
            raise SpotifyApiError(
                "Response Spotify tidak memiliki access_token."
            )

        self.access_token = str(access_token)

        return self.access_token

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Mengambil data dari Spotify Web API.
        """

        access_token = self.get_access_token()

        url = f"{self.API_BASE_URL}{endpoint}"

        for attempt in range(3):
            response = self.session.get(
                url,
                headers={
                    "Authorization": (
                        f"Bearer {access_token}"
                    )
                },
                params=params or {},
                timeout=30,
            )

            if response.status_code == 429:
                retry_after = int(
                    response.headers.get(
                        "Retry-After",
                        "5",
                    )
                )

                time.sleep(
                    min(retry_after, 30)
                )

                continue

            if response.status_code == 401:
                raise SpotifyApiError(
                    "Spotify mengembalikan HTTP 401. "
                    "Refresh token tidak valid atau expired."
                )

            if response.status_code == 403:
                raise SpotifyApiError(
                    "Spotify mengembalikan HTTP 403. "
                    "Scope token belum mencukupi."
                )

            if not response.ok:
                raise SpotifyApiError(
                    f"Spotify API gagal untuk {endpoint}. "
                    f"HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )

            payload = response.json()

            if not isinstance(payload, dict):
                raise SpotifyApiError(
                    "Response Spotify bukan JSON object."
                )

            return payload

        raise SpotifyApiError(
            f"Rate limit Spotify masih aktif untuk {endpoint}."
        )

    def snapshot(
        self,
        source: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> SpotifySnapshot:
        """
        Membungkus hasil API menjadi raw snapshot.
        """

        return SpotifySnapshot(
            source=source,
            endpoint=endpoint,
            params=params or {},
            fetched_at=datetime.now(
                timezone.utc
            ).isoformat(),
            payload=self.get(
                endpoint,
                params,
            ),
        )

    def collect(
        self,
        recently_played_after: datetime | None = None,
    ) -> list[SpotifySnapshot]:
        """
        Mengambil seluruh data yang diperlukan.
        """

        snapshots: list[SpotifySnapshot] = []

        if (
            recently_played_after
            and recently_played_after.tzinfo is None
        ):
            recently_played_after = (
                recently_played_after.replace(
                    tzinfo=timezone.utc
                )
            )

        snapshots.append(
            self.snapshot(
                source="profile",
                endpoint="/me",
            )
        )

        recently_played_params: dict[str, Any] = {
            "limit": 50,
        }

        if recently_played_after:
            recently_played_params["after"] = int(
                recently_played_after.timestamp() * 1000
            )

        snapshots.append(
            self.snapshot(
                source="recently_played",
                endpoint="/me/player/recently-played",
                params=recently_played_params,
            )
        )

        for time_range in [
            "short_term",
            "medium_term",
            "long_term",
        ]:
            snapshots.append(
                self.snapshot(
                    source=f"top_tracks_{time_range}",
                    endpoint="/me/top/tracks",
                    params={
                        "time_range": time_range,
                        "limit": 50,
                    },
                )
            )

            snapshots.append(
                self.snapshot(
                    source=f"top_artists_{time_range}",
                    endpoint="/me/top/artists",
                    params={
                        "time_range": time_range,
                        "limit": 50,
                    },
                )
            )

        snapshots.append(
            self.snapshot(
                source="playlists",
                endpoint="/me/playlists",
                params={
                    "limit": 50,
                },
            )
        )

        snapshots.append(
            self.snapshot(
                source="saved_tracks",
                endpoint="/me/tracks",
                params={
                    "limit": 50,
                },
            )
        )

        return snapshots