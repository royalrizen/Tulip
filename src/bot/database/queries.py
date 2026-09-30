from .connection import Database


async def create_tables(db: Database):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id BIGINT PRIMARY KEY,
            logging_channel_id BIGINT NULL
        )
    """)

    columns = await db.fetchall("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'guild_settings'
    """)

    existing = {
        row["COLUMN_NAME"]
        for row in columns
    }

    if "verification_channel_id" not in existing:
        await db.execute("""
            ALTER TABLE guild_settings
            ADD COLUMN verification_channel_id BIGINT NULL
        """)

    if "verification_webhook_url" not in existing:
        await db.execute("""
            ALTER TABLE guild_settings
            ADD COLUMN verification_webhook_url TEXT NULL
        """)

    if "joins_channel_id" not in existing:
        await db.execute("""
            ALTER TABLE guild_settings
            ADD COLUMN joins_channel_id BIGINT NULL
        """)

    if "skullboard_channel_id" not in existing:
        await db.execute("""
            ALTER TABLE guild_settings
            ADD COLUMN skullboard_channel_id BIGINT NULL
        """)

    if "skullboard_threshold" not in existing:
        await db.execute("""
            ALTER TABLE guild_settings
            ADD COLUMN skullboard_threshold INT NULL
        """)

    if "skullboard_webhook_url" not in existing:
        await db.execute("""
            ALTER TABLE guild_settings
            ADD COLUMN skullboard_webhook_url TEXT NULL
        """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS model_settings (
            guild_id BIGINT PRIMARY KEY,
            channel_id BIGINT NOT NULL,
            message_id BIGINT NULL,
            save_interval INT NOT NULL DEFAULT 3600
        )
    """)


async def set_logging_channel(
    db: Database,
    guild_id: int,
    channel_id: int,
):
    await db.execute(
        """
        INSERT INTO guild_settings (
            guild_id,
            logging_channel_id
        )
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE
            logging_channel_id = %s
        """,
        guild_id,
        channel_id,
        channel_id,
    )


async def get_logging_channel(
    db: Database,
    guild_id: int,
) -> int | None:
    return await db.fetchval(
        """
        SELECT logging_channel_id
        FROM guild_settings
        WHERE guild_id = %s
        """,
        guild_id,
    )


async def set_verification_config(
    db: Database,
    guild_id: int,
    channel_id: int,
    webhook_url: str,
):
    await db.execute(
        """
        INSERT INTO guild_settings (
            guild_id,
            verification_channel_id,
            verification_webhook_url
        )
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            verification_channel_id = %s,
            verification_webhook_url = %s
        """,
        guild_id,
        channel_id,
        webhook_url,
        channel_id,
        webhook_url,
    )


async def get_verification_config(
    db: Database,
    guild_id: int,
):
    return await db.fetchone(
        """
        SELECT
            verification_channel_id,
            verification_webhook_url
        FROM guild_settings
        WHERE guild_id = %s
        """,
        guild_id,
    )


async def set_joins_channel(
    db: Database,
    guild_id: int,
    channel_id: int,
):
    await db.execute(
        """
        INSERT INTO guild_settings (
            guild_id,
            joins_channel_id
        )
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE
            joins_channel_id = %s
        """,
        guild_id,
        channel_id,
        channel_id,
    )


async def get_joins_channel(
    db: Database,
    guild_id: int,
) -> int | None:
    return await db.fetchval(
        """
        SELECT joins_channel_id
        FROM guild_settings
        WHERE guild_id = %s
        """,
        guild_id,
    )


async def set_skullboard_config(
    db: Database,
    guild_id: int,
    channel_id: int,
    threshold: int,
    webhook_url: str,
):
    await db.execute(
        """
        INSERT INTO guild_settings (
            guild_id,
            skullboard_channel_id,
            skullboard_threshold,
            skullboard_webhook_url
        )
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            skullboard_channel_id = %s,
            skullboard_threshold = %s,
            skullboard_webhook_url = %s
        """,
        guild_id,
        channel_id,
        threshold,
        webhook_url,
        channel_id,
        threshold,
        webhook_url,
    )


async def get_skullboard_config(
    db: Database,
    guild_id: int,
):
    return await db.fetchone(
        """
        SELECT
            skullboard_channel_id,
            skullboard_threshold,
            skullboard_webhook_url
        FROM guild_settings
        WHERE guild_id = %s
        """,
        guild_id,
    )


async def set_model_config(
    db: Database,
    guild_id: int,
    channel_id: int,
    save_interval: int,
):
    await db.execute(
        """
        INSERT INTO model_settings (
            guild_id,
            channel_id,
            save_interval
        )
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            channel_id = %s,
            save_interval = %s
        """,
        guild_id,
        channel_id,
        save_interval,
        channel_id,
        save_interval,
    )


async def get_model_config(
    db: Database,
    guild_id: int,
):
    return await db.fetchone(
        """
        SELECT
            channel_id,
            message_id,
            save_interval
        FROM model_settings
        WHERE guild_id = %s
        """,
        guild_id,
    )


async def set_model_message(
    db: Database,
    guild_id: int,
    message_id: int,
):
    await db.execute(
        """
        UPDATE model_settings
        SET message_id = %s
        WHERE guild_id = %s
        """,
        message_id,
        guild_id,
    )
