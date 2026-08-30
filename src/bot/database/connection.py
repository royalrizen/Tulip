import aiomysql


class Database:
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        self.pool: aiomysql.Pool | None = None

    async def connect(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

        self.pool = await aiomysql.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.database,
            autocommit=True,
        )

    async def close(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None

    async def execute(
        self,
        query: str,
        *args,
    ):
        if self.pool is None:
            raise RuntimeError(
                "Database is not connected."
            )

        async with self.pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    query,
                    args,
                )

    async def fetchone(
        self,
        query: str,
        *args,
    ):
        if self.pool is None:
            raise RuntimeError(
                "Database is not connected."
            )

        async with self.pool.acquire() as connection:
            async with connection.cursor(
                aiomysql.DictCursor
            ) as cursor:
                await cursor.execute(
                    query,
                    args,
                )

                return await cursor.fetchone()

    async def fetchall(
        self,
        query: str,
        *args,
    ):
        if self.pool is None:
            raise RuntimeError(
                "Database is not connected."
            )

        async with self.pool.acquire() as connection:
            async with connection.cursor(
                aiomysql.DictCursor
            ) as cursor:
                await cursor.execute(
                    query,
                    args,
                )

                return await cursor.fetchall()

    async def fetchval(
        self,
        query: str,
        *args,
    ):
        row = await self.fetchone(
            query,
            *args,
        )

        if row is None:
            return None

        return next(iter(row.values()))
