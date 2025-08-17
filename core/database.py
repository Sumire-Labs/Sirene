import aiosqlite
from pathlib import Path
import time

# Define the path to the database file
DB_FILE = Path("data.sqlite3")

class Database:
    """Handles the connection to the SQLite database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        """Establishes a connection to the database."""
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            print(f"Successfully connected to database at '{self.db_path}'")
            await self.setup_tables()
        except Exception as e:
            print(f"[ERROR] Failed to connect to database: {e}")

    async def close(self):
        """Closes the database connection."""
        if self.conn:
            await self.conn.close()
            print("Database connection closed.")

    async def setup_tables(self):
        """Creates the necessary tables if they don't exist."""
        if not self.conn: return
        cursor = await self.conn.cursor()
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                command_name TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            )
        """)
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                log_channel_id INTEGER,
                logging_enabled BOOLEAN DEFAULT TRUE
            )
        """)
        await self.conn.commit()
        await cursor.close()
        print("Database tables checked/created.")

    async def ping(self) -> float:
        """Measures the database query latency and returns it in milliseconds."""
        if not self.conn: return -1.0
        start_time = time.monotonic()
        async with self.conn.execute("SELECT 1") as cursor:
            await cursor.fetchone()
        end_time = time.monotonic()
        return (end_time - start_time) * 1000

    async def set_log_channel(self, guild_id: int, channel_id: int | None):
        """Sets or clears the log channel for a specific guild."""
        if not self.conn: return
        await self.conn.execute(
            """
            INSERT INTO guild_settings (guild_id, log_channel_id) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET log_channel_id = excluded.log_channel_id
            """,
            (guild_id, channel_id)
        )
        await self.conn.commit()

    async def set_logging_status(self, guild_id: int, enabled: bool):
        """Enables or disables logging for a specific guild."""
        if not self.conn: return
        await self.conn.execute(
            """
            INSERT INTO guild_settings (guild_id, logging_enabled) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET logging_enabled = excluded.logging_enabled
            """,
            (guild_id, enabled)
        )
        await self.conn.commit()

    async def get_guild_settings(self, guild_id: int) -> tuple[int | None, bool]:
        """Gets the log channel ID and enabled status for a specific guild."""
        if not self.conn: return (None, False)
        async with self.conn.execute(
            "SELECT log_channel_id, logging_enabled FROM guild_settings WHERE guild_id = ?",
            (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                # Return (channel_id, logging_enabled). logging_enabled defaults to True if not set.
                return (row[0], row[1] if row[1] is not None else True)
            else:
                # Default settings for a new guild
                return (None, True)

# --- Singleton instance ---
db_instance = Database(DB_FILE)