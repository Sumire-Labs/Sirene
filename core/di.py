# core/di.py

# Add the project root to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.config import ConfigLoader, CONFIG_FILE_PATH, COMMANDS_FILE_PATH
from core.ai import AIService
from core.database import Database, DB_FILE

class DependencyContainer:
    """A container for managing application-wide dependencies."""

    def __init__(self):
        # Configuration
        self.config_loader = ConfigLoader(
            config_path=CONFIG_FILE_PATH,
            commands_path=COMMANDS_FILE_PATH
        )
        
        # Services
        self.db = Database(DB_FILE)
        # Inject the Vertex AI config into the AIService
        self.ai_service = AIService(self.config_loader.config.vertex_ai)

    async def connect_services(self):
        """Connects to external services like the database."""
        await self.db.connect()

    async def close_services(self):
        """Closes connections to external services."""
        await self.db.close()

# --- Singleton instance ---
container = DependencyContainer()
