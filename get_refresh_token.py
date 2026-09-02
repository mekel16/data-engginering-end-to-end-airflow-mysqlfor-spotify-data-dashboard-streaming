import base64
import getpass

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests


CLIENT_ID = input("Masukkan Spotify Client ID: ").strip()

CLIENT_SECRET = getpass.getpass(
    "Masukkan Spotify Client Secret: "
).strip()

REDIRECT_URI = "http://127.0.0.1:8888/callback"

SCOPES = [
    "user-read-recently-played",
    "user-top-read",
    "user-read-private",
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
]

AUTHORIZATION_URL = (
    "https://accounts.spotify.com/authorize"
)

TOKEN_URL = (
    "https://accounts.spotify.com/api/token"
)


class CallbackHandler(BaseHTTPRequestHandler):
    authorization_code = None
    error = None

    def do_GET(self):
        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)

        CallbackHandler.authorization_code = (
            query.get("code", [None])[0]
        )

        CallbackHandler.error = (
            query.get("error", [None])[0]
        )

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8",
        )
        self.end_headers()

        self.wfile.write(
            b"""
            <html>
                <body>
                    <h2>Authorization selesai.</h2>
                    <p>Anda boleh menutup browser.</p>
                </body>
            </html>
            """
        )

    def log_message(self, format, *args):
        return


def main():
    authorization_params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "show_dialog": "true",
    }

    authorization_url = (
        f"{AUTHORIZATION_URL}?"
        f"{urlencode(authorization_params)}"
    )

    print("\nBuka URL berikut di browser:\n")
    print(authorization_url)
    print()

    print(
        "Setelah proses login selesai, "
        "program akan menerima callback otomatis."
    )

    server = HTTPServer(
        ("127.0.0.1", 8888),
        CallbackHandler,
    )

    while (
        CallbackHandler.authorization_code is None
        and CallbackHandler.error is None
    ):
        server.handle_request()

    server.server_close()

    if CallbackHandler.error:
        raise RuntimeError(
            "Authorization Spotify gagal: "
            f"{CallbackHandler.error}"
        )

    authorization_code = (
        CallbackHandler.authorization_code
    )

    credentials = base64.b64encode(
        f"{CLIENT_ID}:{CLIENT_SECRET}".encode("utf-8")
    ).decode("ascii")

    response = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": (
                "application/x-www-form-urlencoded"
            ),
        },
        data={
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )

    response.raise_for_status()

    token_data = response.json()

    refresh_token = token_data.get("refresh_token")

    if not refresh_token:
        raise RuntimeError(
            "Spotify tidak mengembalikan refresh token."
        )

    print("\nRefresh token berhasil diperoleh:")
    print(refresh_token)

    print(
        "\nMasukkan token tersebut ke file .env sebagai:"
    )
    print(
        "SPOTIFY_REFRESH_TOKEN=refresh_token_anda"
    )


if __name__ == "__main__":
    main()