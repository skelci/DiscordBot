from discord.ext import commands
import discord
from discord import app_commands, Interaction


class ListCommands(commands.Cog):
    def __init__(self, settings_manager, database_manager):
        self.settings_manager = settings_manager
        self.database_manager = database_manager
    
    def bind_to_tree(self, tree):
        tree.add_command(self.create_list)
        tree.add_command(self.get_lists)
        tree.add_command(self.add_to_list)
        tree.add_command(self.assign_to_list)
        tree.add_command(self.remove_from_list)
        tree.add_command(self.view_list)

    async def list_name_autocomplete(
        self,
        interaction: Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        names = [lst[1] for lst in self.database_manager.get_lists()]
        filtered = [name for name in names if current.lower() in name.lower()]
        return [
            app_commands.Choice(name=name, value=name)
            for name in filtered[:25]
        ]
    
    async def place_autocomplete(
        self,
        interaction: Interaction,
        current: str,
    ) -> list[app_commands.Choice[int]]:
        if not current == "":
            if not current.isdigit():
                return []
            current_int = int(current)
            if current_int < 1:
                return []
        
        max_place = self.settings_manager.get("max_place", 25)
        available_places = set([i for i in range(1, max_place + 1)])
        for entry in self.database_manager.get_list_entries(interaction.namespace.list_name):
            if entry[2] in available_places:
                available_places.remove(entry[2])

        return [
            app_commands.Choice(name=str(i), value=i)
            for i in available_places if (str(i).startswith(current) or current == "")
        ][:25]
    

    def verify_place(self, place: int) -> bool:
        max_place = self.settings_manager.get("max_place", 25)
        return 1 <= place <= max_place


    @app_commands.command(name="create-list", description="Create a new list.")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_list(self, interaction: discord.Interaction, list_name: str):
        if list_name in [lst[1] for lst in self.database_manager.get_lists()]:
            await interaction.response.send_message(f"List `{list_name}` already exists.", ephemeral=True)
            return
        
        self.database_manager.create_list(list_name)
        await interaction.response.send_message(f"Successfully created list `{list_name}`.")


    @app_commands.command(name="get-lists", description="Get all lists.")
    @app_commands.checks.has_permissions(administrator=True)
    async def get_lists(self, interaction: discord.Interaction):
        lists = self.database_manager.get_lists()
        if not lists:
            await interaction.response.send_message("No lists found.")
            return

        response = "Here are the available lists:\n"
        for lst in lists:
            response += f"- {lst[1]} (Created at: {lst[2]})\n"
        await interaction.response.send_message(response)


    @app_commands.command(name="add-to-list", description="Add a user to a list.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(list_name=list_name_autocomplete)
    @app_commands.autocomplete(place=place_autocomplete)
    async def add_to_list(self, interaction: discord.Interaction, list_name: str, member: discord.Member, place: int):
        if list_name not in [lst[1] for lst in self.database_manager.get_lists()]:
            await interaction.response.send_message(f"List `{list_name}` does not exist.", ephemeral=True)
            return
        
        if member.id not in [user[0] for user in self.database_manager.get_users()]:
            await interaction.response.send_message(f"User @{member.display_name} does not exist. Please add them first.", ephemeral=True)
            return
        
        if place in [entry[2] for entry in self.database_manager.get_list_entries(list_name)]:
            await interaction.response.send_message(f"Place {place} is already taken in list `{list_name}`.", ephemeral=True)
            return

        if not self.verify_place(place):
            await interaction.response.send_message(f"Please provide a valid place (1-{self.settings_manager.get('max_place', 25)}).", ephemeral=True)
            return

        self.database_manager.add_list_entry(list_name, member.id, place)
        await interaction.response.send_message(f"Successfully added @{member.display_name} to list `{list_name}` at position {place}.")


    @app_commands.command(name="assign-to-list", description="Assign self to a list.")
    @app_commands.autocomplete(list_name=list_name_autocomplete)
    @app_commands.autocomplete(place=place_autocomplete)
    async def assign_to_list(self, interaction: discord.Interaction, list_name: str, place: int):
        member = interaction.user
        if list_name not in [lst[1] for lst in self.database_manager.get_lists()]:
            await interaction.response.send_message(f"List `{list_name}` does not exist.", ephemeral=True)
            return

        if member.id not in [user[0] for user in self.database_manager.get_users()]:
            await interaction.response.send_message(f"User @{member.display_name} does not exist. Please contact an admin to add you.", ephemeral=True)
            return

        if place in [entry[2] for entry in self.database_manager.get_list_entries(list_name)]:
            await interaction.response.send_message(f"Place {place} is already taken in list `{list_name}`.", ephemeral=True)
            return
        
        if not self.verify_place(place):
            await interaction.response.send_message(f"Please provide a valid place (1-{self.settings_manager.get('max_place', 25)}).", ephemeral=True)
            return

        self.database_manager.add_list_entry(list_name, member.id, place)
        await interaction.response.send_message(f"Successfully assigned @{member.display_name} to list `{list_name}` at position {place}.")

    @app_commands.command(name="remove-from-list", description="Remove a user from a list.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(list_name=list_name_autocomplete)
    async def remove_from_list(self, interaction: discord.Interaction, list_name: str, member: discord.Member):
        if list_name not in [lst[1] for lst in self.database_manager.get_lists()]:
            await interaction.response.send_message(f"List `{list_name}` does not exist.", ephemeral=True)
            return

        if member.id not in [user[0] for user in self.database_manager.get_users()]:
            await interaction.response.send_message(f"User @{member.display_name} does not exist.", ephemeral=True)
            return

        self.database_manager.remove_list_entry(list_name, member.id)
        await interaction.response.send_message(f"Successfully removed @{member.display_name} from list `{list_name}`.")

    @app_commands.command(name="view-list", description="View entries in a list.")
    @app_commands.autocomplete(list_name=list_name_autocomplete)
    async def view_list(self, interaction: discord.Interaction, list_name: str):
        if list_name not in [lst[1] for lst in self.database_manager.get_lists()]:
            await interaction.response.send_message(f"List `{list_name}` does not exist.", ephemeral=True)
            return
        
        entries = self.database_manager.get_list_entries(list_name)
        if not entries:
            await interaction.response.send_message(f"List `{list_name}` is empty.")
            return
        
        entries_sorted = sorted(entries, key=lambda x: x[2])  # Sort by place
        entry_lines = [f"{entry[2]}. {entry[1]}" for entry in entries_sorted]
        response = f"Entries in list `{list_name}`:\n```" + "\n".join(entry_lines) + "```"
        
        await interaction.response.send_message(response)

