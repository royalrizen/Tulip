import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Config:
    token: str
    prefix: str
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str

    @classmethod
    def load(cls):
        token = os.getenv("DISCORD_TOKEN")
        prefix = os.getenv("PREFIX", "!")

        mysql_host = os.getenv("MYSQL_HOST")
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_user = os.getenv("MYSQL_USER")
        mysql_password = os.getenv("MYSQL_PASSWORD")
        mysql_database = os.getenv("MYSQL_DATABASE")

        if not token:
            raise RuntimeError("DISCORD_TOKEN is not set")

        if not mysql_host:
            raise RuntimeError("MYSQL_HOST is not set")

        if not mysql_user:
            raise RuntimeError("MYSQL_USER is not set")

        if not mysql_password:
            raise RuntimeError("MYSQL_PASSWORD is not set")

        if not mysql_database:
            raise RuntimeError("MYSQL_DATABASE is not set")

        try:
            mysql_port = int(mysql_port)
        except ValueError:
            raise RuntimeError("MYSQL_PORT must be a number")

        return cls(
            token=token,
            prefix=prefix,
            mysql_host=mysql_host,
            mysql_port=mysql_port,
            mysql_user=mysql_user,
            mysql_password=mysql_password,
            mysql_database=mysql_database,
        )