import aiosqlite
from pathlib import Path

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
            # Create tables on startup
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
        if not self.conn:
            return
        
        cursor = await self.conn.cursor()
        # Example table for logging command usage
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                command_name TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            )
        """)
        await self.conn.commit()
        await cursor.close()
        print("Database tables checked/created.")


# --- Singleton instance ---
db_instance = Database(DB_FILE)

# In main.py, you would call:
# await db_instance.connect()
# and add a shutdown hook for:
# await db_instance.close()
