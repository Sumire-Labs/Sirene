import discord
import os
import sys
from pathlib import Path
import asyncio

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.di import container
from utils.embeds import embed_factory

class MyBot(discord.Bot):
    """Custom Bot class to hold the DI container."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.container = container

# --- Bot setup ---

bot = MyBot(
    intents=discord.Intents.default(),
    debug_guilds=None # Optional: for testing in a specific guild
)

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    embed_factory.set_bot_user(bot.user)
    await bot.container.connect_services()
    
    print(f"Logged in as {bot.user}")
    print(f"Pycord version: {discord.__version__}")
    print("UI Factory and services ready.")
    print("-------------------")

@bot.event
async def on_close():
    """Called when the bot is shutting down."""
    print("Bot is shutting down...")
    await bot.container.close_services()

def load_cogs():
    """Loads enabled cogs from subdirectories based on commands.yaml."""
    print("Loading cogs...")
    cogs_config = bot.container.config_loader.commands.cogs
    cogs_dir = project_root / "cogs"

    for category_name, category_config in cogs_config.items():
        if category_config.enabled:
            category_dir = cogs_dir / category_name
            if not category_dir.is_dir():
                print(f"  - [WARNING] Cog category '{category_name}' is enabled but directory 'cogs/{category_name}' not found.")
                continue

            print(f"  - Loading category: {category_name}")
            for cog_file in category_dir.glob("*.py"):
                if cog_file.stem == "__init__":
                    continue
                
                cog_path = f"cogs.{category_name}.{cog_file.stem}"
                try:
                    bot.load_extension(cog_path)
                    print(f"    - Successfully loaded cog module: {cog_file.stem}")
                except Exception as e:
                    print(f"    - [ERROR] Failed to load cog module: {cog_file.stem}")
                    print(f"      Reason: {e}")
        else:
            print(f"  - Skipping disabled cog category: {category_name}")

async def main():
    """Main function to run the bot."""
    load_cogs()
    
    bot_token = bot.container.config_loader.config.token
    
    if bot_token == "YOUR_DISCORD_BOT_TOKEN":
        print("\n!!! BOT TOKEN IS NOT SET !!!")
        print("Please open 'configs/config.yaml' and replace 'YOUR_DISCORD_BOT_TOKEN' with your actual bot token.")
    else:
        try:
            await bot.start(bot_token)
        except discord.LoginFailure:
            print("\n!!! LOGIN FAILED !!!")
            print("The provided bot token is invalid. Please check 'configs/config.yaml'.")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutdown requested by user.")