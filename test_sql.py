import os

import mysql.connector

from dotenv import load_dotenv


load_dotenv()


host = os.getenv(
    "MYSQL_HOST",
    "127.0.0.1",
)

port = int(
    os.getenv(
        "MYSQL_PORT",
        "3306",
    )
)

user = os.getenv(
    "MYSQL_USER",
    "spotify_user",
)

password = os.getenv(
    "MYSQL_PASSWORD",
    "password_lokal_anda",
)

database = os.getenv(
    "MYSQL_DATABASE",
    "spotify_analytics",
)


try:
    connection = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            DATABASE(),
            VERSION()
        """
    )

    result = cursor.fetchone()

    print("Koneksi MySQL berhasil.")
    print(f"Database aktif: {result[0]}")
    print(f"MySQL version: {result[1]}")

    cursor.close()
    connection.close()

except mysql.connector.Error as error:
    print("Koneksi MySQL gagal.")
    print(error)