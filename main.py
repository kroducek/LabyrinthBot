import discord
import os
import logging
from discord.ext import commands
from dotenv import load_dotenv

# ====== LOAD ENV ======
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ DISCORD_TOKEN nebyl nalezen v prostředí!")
    exit(1)

# ====== LOGGING ======
logging.basicConfig(level=logging.INFO)

# ====== CONFIG ======
config = {
    "prefix": os.getenv("PREFIX", "!"),
}

class LabyrinthBot(commands.Bot):
    def __init__(self):
        self.config = config

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=config['prefix'],
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        print("--- 🐾 Načítám Labyrinth ---")
        try:
            await self.load_extension('labyrinth2.lobby')
            await self.load_extension('labyrinth2.roll')
            print("✅ labyrinth 2.0 (lobby & roll) načten.")
        except Exception as e:
            logging.exception("❌ labyrinth 2.0 selhal při načítání:")

        print("🔄 Synchronizuji slash commandy...")
        synced = await self.tree.sync()
        print(f"✅ Synced {len(synced)} commandů.")

    async def on_ready(self):
        print(f'🚀 LabyrinthBot je online jako {self.user}')

# ====== RUN ======
if __name__ == "__main__":
    bot = LabyrinthBot()
    bot.run(TOKEN)
