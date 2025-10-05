from discord.ext import commands
import discord
from discord import app_commands


class UserCommands(commands.Cog):
    def __init__(self, database_manager):
        self.database_manager = database_manager
    
    def bind_to_tree(self, tree):
        tree.add_command(self.add_user)
        tree.add_command(self.remove_user)
        tree.add_command(self.get_users)


    @app_commands.command(name="add-user", description="Add a user.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_user(self, interaction: discord.Interaction, member: discord.Member):
        if member.id in [user[0] for user in self.database_manager.get_users()]:
            await interaction.response.send_message(f"User @{member.display_name} already exists.", ephemeral=True)
            return
        self.database_manager.add_user(member.id, member.display_name)
        await interaction.response.send_message(f"Successfully added user @{member.display_name}.")


    @app_commands.command(name="get-users", description="Get a list of all users.")
    async def get_users(self, interaction: discord.Interaction):
        users = self.database_manager.get_users()
        if not users:
            await interaction.response.send_message("No users found.")
            return
        users = sorted(users, key=lambda x: x[1].split(' ')[1:])
        user_list = "\n".join(f"1. {user[1]}" for user in users)
        await interaction.response.send_message(f"Users:\n{user_list}")


    @app_commands.command(name="remove-user", description="Remove a user.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_user(self, interaction: discord.Interaction, member: discord.Member):
        if member.id not in [user[0] for user in self.database_manager.get_users()]:
            await interaction.response.send_message(f"User @{member.display_name} does not exist.", ephemeral=True)
            return
        self.database_manager.remove_user(member.id)
        await interaction.response.send_message(f"Successfully removed user @{member.display_name}.")