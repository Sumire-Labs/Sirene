import yaml
from dataclasses import dataclass, field
from pathlib import Path

# --- Type-safe data classes for config.yaml ---

@dataclass
class AIModelsConfig:
    chat: str
    image: str

@dataclass
class VertexAIConfig:
    project_id: str
    location: str
    models: AIModelsConfig
    credentials_json_path: str | None = None

@dataclass
class Config:
    token: str
    vertex_ai: VertexAIConfig

# --- Type-safe data classes for commands.yaml ---

@dataclass
class CommandConfig:
    enabled: bool

@dataclass
class CogConfig:
    enabled: bool
    commands: dict[str, bool] = field(default_factory=dict)

@dataclass
class Commands:
    cogs: dict[str, CogConfig] = field(default_factory=dict)

# --- Main loader class ---

class ConfigLoader:
    def __init__(self, config_path: Path, commands_path: Path):
        self.config_path = config_path
        self.commands_path = commands_path
        self.config = self._load_config()
        self.commands = self._load_commands()

    def _load_yaml(self, path: Path) -> dict:
        """Loads a YAML file and returns its content."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Handle error appropriately in a real app
            raise FileNotFoundError(f"Configuration file not found at: {path}")
        except yaml.YAMLError as e:
            # Handle error appropriately
            raise yaml.YAMLError(f"Error parsing YAML file at: {path}\n{e}")

    def _load_config(self) -> Config:
        """Loads and parses the main config.yaml."""
        data = self._load_yaml(self.config_path)
        vertex_ai_data = data.get('vertex_ai', {})
        models_data = vertex_ai_data.get('models', {})

        return Config(
            token=data.get('token', 'YOUR_DISCORD_BOT_TOKEN'),
            vertex_ai=VertexAIConfig(
                project_id=vertex_ai_data.get('project_id', 'YOUR_GOOGLE_CLOUD_PROJECT_ID'),
                location=vertex_ai_data.get('location', 'YOUR_GOOGLE_CLOUD_LOCATION'),
                credentials_json_path=vertex_ai_data.get('credentials_json_path'),
                models=AIModelsConfig(
                    chat=models_data.get('chat', 'gemini-1.5-flash'),
                    image=models_data.get('image', 'imagen-4')
                )
            )
        )

    def _load_commands(self) -> Commands:
        """Loads and parses the commands.yaml."""
        data = self._load_yaml(self.commands_path)
        cogs_data = data.get('cogs', {})
        
        loaded_cogs = {}
        for name, cog_data in cogs_data.items():
            loaded_cogs[name] = CogConfig(
                enabled=cog_data.get('enabled', False),
                commands=cog_data.get('commands', {})
            )
        return Commands(cogs=loaded_cogs)

# --- Singleton instance for easy access ---

# Define paths relative to the project root
# This assumes the script is run from the project root
CONFIG_FILE_PATH = Path("configs/config.yaml")
COMMANDS_FILE_PATH = Path("configs/commands.yaml")

# Create a single, globally accessible instance of the loader
# In a real DI setup, this would be managed by the container
loader = ConfigLoader(config_path=CONFIG_FILE_PATH, commands_path=COMMANDS_FILE_PATH)

# You can now import 'loader' from this module elsewhere
# and access config with `loader.config` and commands with `loader.commands`
