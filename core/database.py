import aiosqlite
from pathlib import Path
import time
import datetime
from dataclasses import dataclass

# Define the path to the database file
DB_FILE = Path("data.sqlite3")

@dataclass
class GuildSettings:
    guild_id: int
    log_channel_id: int | None
    logging_enabled: bool
    ticket_panel_channel_id: int | None
    ticket_category_id: int | None
    ticket_staff_role_id: int | None
    raid_detection_enabled: bool

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
                logging_enabled BOOLEAN DEFAULT TRUE,
                ticket_panel_channel_id INTEGER,
                ticket_category_id INTEGER,
                ticket_staff_role_id INTEGER,
                raid_detection_enabled BOOLEAN DEFAULT TRUE
            )
        """)
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL, -- e.g., 'open', 'closed'
                created_at DATETIME NOT NULL
            )
        """)
        await self.conn.commit()
        await cursor.close()
        print("Database tables checked/created.")

    async def ping(self) -> float:
        if not self.conn: return -1.0
        start_time = time.monotonic()
        async with self.conn.execute("SELECT 1") as cursor:
            await cursor.fetchone()
        end_time = time.monotonic()
        return (end_time - start_time) * 1000

    # --- Settings Management ---
    async def set_log_channel(self, guild_id: int, channel_id: int | None):
        if not self.conn: return
        await self.conn.execute(
            "INSERT INTO guild_settings (guild_id, log_channel_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET log_channel_id = excluded.log_channel_id",
            (guild_id, channel_id)
        )
        await self.conn.commit()

    async def set_logging_status(self, guild_id: int, enabled: bool):
        if not self.conn: return
        await self.conn.execute(
            "INSERT INTO guild_settings (guild_id, logging_enabled) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET logging_enabled = excluded.logging_enabled",
            (guild_id, enabled)
        )
        await self.conn.commit()

    async def set_ticket_config(self, guild_id: int, panel_channel_id: int | None, category_id: int | None, staff_role_id: int | None):
        if not self.conn: return
        await self.conn.execute(
            """INSERT INTO guild_settings (guild_id, ticket_panel_channel_id, ticket_category_id, ticket_staff_role_id) VALUES (?, ?, ?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET 
               ticket_panel_channel_id = excluded.ticket_panel_channel_id,
               ticket_category_id = excluded.ticket_category_id,
               ticket_staff_role_id = excluded.ticket_staff_role_id
            """,
            (guild_id, panel_channel_id, category_id, staff_role_id)
        )
        await self.conn.commit()

    async def set_raid_detection_status(self, guild_id: int, enabled: bool):
        """Enables or disables raid detection for a specific guild."""
        if not self.conn: return
        await self.conn.execute(
            "INSERT INTO guild_settings (guild_id, raid_detection_enabled) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET raid_detection_enabled = excluded.raid_detection_enabled",
            (guild_id, enabled)
        )
        await self.conn.commit()

    async def get_guild_settings(self, guild_id: int) -> GuildSettings | None:
        if not self.conn: return None
        async with self.conn.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return GuildSettings(
                    guild_id=row[0],
                    log_channel_id=row[1],
                    logging_enabled=row[2] if row[2] is not None else True,
                    ticket_panel_channel_id=row[3],
                    ticket_category_id=row[4],
                    ticket_staff_role_id=row[5],
                    raid_detection_enabled=row[6] if row[6] is not None else True
                )
            return None

    # --- Ticket Management ---
    async def create_ticket(self, channel_id: int, guild_id: int, user_id: int):
        if not self.conn: return
        await self.conn.execute(
            "INSERT INTO tickets (channel_id, guild_id, user_id, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (channel_id, guild_id, user_id, "open", datetime.datetime.utcnow())
        )
        await self.conn.commit()

    async def get_ticket_by_channel(self, channel_id: int):
        if not self.conn: return None
        async with self.conn.execute("SELECT * FROM tickets WHERE channel_id = ?", (channel_id,)) as cursor:
            return await cursor.fetchone()

    async def close_ticket(self, channel_id: int):
        if not self.conn: return
        await self.conn.execute("UPDATE tickets SET status = ? WHERE channel_id = ?", ("closed", channel_id))
        await self.conn.commit()

# --- Singleton instance ---
db_instance = Database(DB_FILE)