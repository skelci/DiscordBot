from database_manager import DatabaseManager
from settings_manager import SettingsManager
from commands.list_commands import ListCommands
from commands.settings_commands import SettingsCommands

import os
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    await tree.sync()
    print("Slash commands synced.")

settings_manager = SettingsManager()
database_manager = DatabaseManager()
list_cog = ListCommands(settings_manager, database_manager)
list_cog.bind_to_tree(tree)
settings_cog = SettingsCommands(settings_manager)
settings_cog.bind_to_tree(tree)

client.run(token)