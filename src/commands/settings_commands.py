from discord.ext import commands
import discord
from discord import app_commands


class SettingsCommands(commands.Cog):
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager

    def bind_to_tree(self, tree):
        tree.add_command(self.set_max_place)


    @app_commands.command(name="set-max-place", description="Set the maximum place allowed in lists. If no value is provided, the current setting will be shown.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_max_place(self, interaction: discord.Interaction, max_place: int = None):
        if max_place is None:
            max_place = self.settings_manager.get("max_place", 25)
            await interaction.response.send_message(f"Current maximum place is {max_place}.")
            return
        if max_place < 1:
            await interaction.response.send_message("Please provide a valid maximum place (positive integer).", ephemeral=True)
            return
        self.settings_manager.set("max_place", max_place)
        await interaction.response.send_message(f"Maximum place set to `{max_place}`.")