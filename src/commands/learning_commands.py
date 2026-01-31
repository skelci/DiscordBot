from discord.ext import commands
import discord
from discord import app_commands, Interaction
import random
import io
from enum import IntEnum

class Lang(IntEnum):
    ENG = 0
    SLO = 1

class LearningCommands(commands.Cog):
    def __init__(self, database_manager):
        self.database_manager = database_manager
        self.active_sessions = {} # user_id -> {'word_data': tuple, 'lang': Lang}
        self.learning_factor = 1.5

    def bind_to_tree(self, tree):
        tree.add_command(self.create_learning_list)
        tree.add_command(self.add_words_bulk)
        tree.add_command(self.clear_words)
        tree.add_command(self.set_learning_list)
        tree.add_command(self.view_learning_list)
        tree.add_command(self.learn)
        tree.add_command(self.guess)
        tree.add_command(self.leaderboard)
        tree.add_command(self.view_stats)
        tree.add_command(self.edit_word)

    async def learning_list_autocomplete(
        self,
        interaction: Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        lists = self.database_manager.get_learning_lists()
        return [
            app_commands.Choice(name=lst, value=lst)
            for lst in lists if current.lower() in lst.lower()
        ][:25]

    @app_commands.command(name="create-learning-list", description="Create a new learning list.")
    async def create_learning_list(self, interaction: Interaction, name: str):
        try:
            self.database_manager.create_learning_list(name)
            await interaction.response.send_message(f"Learning list `{name}` created.")
        except Exception as e:
            await interaction.response.send_message(f"Error creating list: {e}", ephemeral=True)

    @app_commands.command(name="add-words-bulk", description="Add words to a list. Format: eng-slo|eng-slo... (use | or newlines)")
    @app_commands.autocomplete(list_name=learning_list_autocomplete)
    async def add_words_bulk(self, interaction: Interaction, list_name: str, content: str):
        # Taking content as string might hit limits if very large, but 250 words might fit in 6000 chars.
        # Format: eng-slo
        words_to_add = []
        # Support both newlines (if pasted) and | (for manual entry)
        lines = content.replace('|', '\n').split('\n')
        for line in lines:
            if not line.strip(): continue
            parts = line.split('-')
            if len(parts) == 2:
                eng = parts[0].strip().lower()
                slo = parts[1].strip().lower()
                words_to_add.append((eng, slo))
        
        if not words_to_add:
            await interaction.response.send_message("No valid words found. Use 'eng-slo' format.", ephemeral=True)
            return

        try:
            self.database_manager.add_learning_words_bulk(list_name, words_to_add)
            await interaction.response.send_message(f"Added {len(words_to_add)} words to `{list_name}`.")
        except Exception as e:
            await interaction.response.send_message(f"Error adding words: {e}", ephemeral=True)

    @app_commands.command(name="clear-words", description="Remove all words from a learning list.")
    @app_commands.autocomplete(list_name=learning_list_autocomplete)
    async def clear_words(self, interaction: Interaction, list_name: str):
        try:
            self.database_manager.clear_learning_list(list_name)
            await interaction.response.send_message(f"All words removed from list `{list_name}`.")
        except Exception as e:
            await interaction.response.send_message(f"Error clearing list: {e}", ephemeral=True)

    @app_commands.command(name="set-learning-list", description="Set your current learning list.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.autocomplete(list_name=learning_list_autocomplete)
    async def set_learning_list(self, interaction: Interaction, list_name: str):
        try:
            self.database_manager.set_user_learning_list(interaction.user.id, list_name)
            await interaction.response.send_message(f"Current learning list set to `{list_name}`.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error setting list: {e}", ephemeral=True)

    @app_commands.command(name="view-learning-list", description="View all words in a learning list.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.autocomplete(list_name=learning_list_autocomplete)
    async def view_learning_list(self, interaction: Interaction, list_name: str):
        words = self.database_manager.get_learning_words(list_name)
        if not words:
            await interaction.response.send_message(f"List `{list_name}` is empty or does not exist.", ephemeral=True)
            return
        
        lines = [f"{eng} - {slo}" for eng, slo in words]
        full_text = "\n".join(lines)
        
        if len(full_text) > 1900:
            file = discord.File(io.BytesIO(full_text.encode()), filename=f"{list_name}.txt")
            await interaction.response.send_message(f"List `{list_name}` is too long to display directly. See attachment.", file=file)
        else:
            await interaction.response.send_message(f"**Words in `{list_name}`**:\n```\n{full_text}\n```")

    def _get_random_word(self, words_with_scores):
        # words_with_scores: list of (id, eng, slo, score)
        if not words_with_scores:
            return None, None
        
        learned_sum = sum(w[3] for w in words_with_scores)
        rnd_num = random.random() * learned_sum
        
        for word_data in words_with_scores:
            # word_data: (id, eng, slo, score)
            rnd_num -= word_data[3]
            if rnd_num <= 0:
                lang = Lang.ENG if random.random() < 0.5 else Lang.SLO
                return word_data, lang
        
        # Fallback
        return words_with_scores[-1], (Lang.ENG if random.random() < 0.5 else Lang.SLO)

    async def _send_next_word(self, interaction: Interaction, message_text=""):
        user_id = interaction.user.id
        list_name = self.database_manager.get_user_learning_list(user_id)
        if not list_name:
            msg = "You haven't selected a learning list. Use `/set-learning-list`."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        words_data = self.database_manager.get_learning_words_with_scores(user_id, list_name)
        if not words_data:
            msg = f"List `{list_name}` is empty."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        word_data, lang = self._get_random_word(words_data)
        self.active_sessions[user_id] = {'word_data': word_data, 'lang': lang}

        # word_data: (id, eng, slo, score)
        word_to_show = word_data[1] if lang == Lang.ENG else word_data[2]  
        lang_str = "ENG" if lang == Lang.ENG else "SLO"
        
        text = f"{message_text}\n**Translate ({lang_str}):** `{word_to_show}`"
        
        if interaction.response.is_done():
            await interaction.followup.send(text)
        else:
            await interaction.response.send_message(text)

    @app_commands.command(name="learn", description="Start learning words.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def learn(self, interaction: Interaction):
        await self._send_next_word(interaction, "Starting learning session!")

    @app_commands.command(name="guess", description="Submit an answer.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def guess(self, interaction: Interaction, answer: str, last: bool = False):
        user_id = interaction.user.id
        session = self.active_sessions.get(user_id)
        
        if not session:
            await interaction.response.send_message("No active learning session. Use `/learn` to start.", ephemeral=True)
            return

        word_data = session['word_data'] # (id, eng, slo, score)
        original_lang = session['lang']
        
        # Logic from Words.check_word
        # If displayed ENG, answer should be SLO.
        # If displayed SLO, answer should be ENG.
        
        correct = False
        correct_answer = ""
        
        word_eng = word_data[1]
        word_slo = word_data[2]
        
        if original_lang == Lang.ENG:
            # Displayed ENG, user typed SLO?
            if answer.lower().strip() == word_slo.lower().strip():
                correct = True
            correct_answer = word_slo
        else:
            # Displayed SLO, user typed ENG?
            if answer.lower().strip() == word_eng.lower().strip():
                correct = True
            correct_answer = word_eng

        # Update Score
        current_score = word_data[3]
        new_score = current_score / self.learning_factor if correct else current_score * self.learning_factor
        # Note: In the user script: 
        # self.__cache[word_key] /= self.learning_factor if correct else 1 / self.learning_factor
        # if correct: score /= 1.5
        # if wrong: score /= (1/1.5) -> score *= 1.5
        
        self.database_manager.update_word_score(user_id, word_data[0], new_score)
        
        result_msg = f"**{'Correct!' if correct else 'Wrong!'}**\n"
        if not correct:
            result_msg += f"Your answer: {answer}\nCorrect answer: {correct_answer}\n"
        
        result_msg += f"Learned Score: {1/new_score:.2f}" # Display inverse as "Learned" like the script does? 
        # Script: f'Learned: {1 / self.__cache[word_key]}'

        if last:
            del self.active_sessions[user_id]
            await interaction.response.send_message(result_msg + "\nSession ended.")
        else:
            # Send result then next word
            # We need to send the next word. We can reuse _send_next_word but passed the result message prefix.
            await self._send_next_word(interaction, result_msg)

    @app_commands.command(name="leaderboard", description="Show the leaderboard for a learning list.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.autocomplete(list_name=learning_list_autocomplete)
    async def leaderboard(self, interaction: Interaction, list_name: str):
        try:
            results = self.database_manager.get_learning_leaderboard(list_name)
            if not results:
                await interaction.response.send_message(f"No data found for list `{list_name}`.", ephemeral=True)
                return
            
            # results: [(user_id, name, total_score), ...]
            
            lines = [f"**Leaderboard for `{list_name}`**"]
            for i, (uid, name, score) in enumerate(results, 1):
                display_name = name if name else f"<@{uid}>"
                if not name: 
                     # If name isn't in our DB, we could try to resolve it from the interaction's guild or client
                     pass

                lines.append(f"{i}. {display_name}: {score:.2f} pts")
            
            await interaction.response.send_message("\n".join(lines))
        except Exception as e:
            await interaction.response.send_message(f"Error fetching leaderboard: {e}", ephemeral=True)

    @app_commands.command(name="stats", description="View your learning stats for a list.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.autocomplete(list_name=learning_list_autocomplete)
    async def view_stats(self, interaction: Interaction, list_name: str):
        try:
            # words_data: [(id, eng, slo, score), ...]
            words_data = self.database_manager.get_learning_words_with_scores(interaction.user.id, list_name)
            
            if not words_data:
                await interaction.response.send_message(f"No words found in list `{list_name}`.", ephemeral=True)
                return

            total_words = len(words_data)
            # score in DB is "weight" (lower is better learned).
            # Learned Score = 1/weight.
            # "Not learned yet" means Learned Score <= 1.0 (so weight >= 1.0).
            
            learned_scores = [1/w[3] for w in words_data]
            
            not_learned_count = sum(1 for s in learned_scores if s <= 1.000001)
            avg_score = sum(learned_scores) / total_words
            min_score = min(learned_scores)
            max_score = max(learned_scores)

            embed = discord.Embed(title=f"Learning Stats: {list_name}", color=discord.Color.blue())
            embed.add_field(name="Total Words", value=str(total_words), inline=True)
            embed.add_field(name="Words To Learn", value=str(not_learned_count), inline=True)
            embed.add_field(name="Avg Score", value=f"{avg_score:.2f}", inline=True)
            embed.add_field(name="Min Score", value=f"{min_score:.2f}", inline=True)
            embed.add_field(name="Max Score", value=f"{max_score:.2f}", inline=True)
            
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"Error fetching stats: {e}", ephemeral=True)

    @app_commands.command(name="edit-word", description="Edit or replace a word translation in a list.")
    @app_commands.autocomplete(list_name=learning_list_autocomplete)
    async def edit_word(self, interaction: Interaction, list_name: str, word: str, new_eng: str = None, new_slo: str = None):
        if not new_eng and not new_slo:
            await interaction.response.send_message("You must provide at least one new value (new_eng or new_slo).", ephemeral=True)
            return

        try:
            final_eng, final_slo = self.database_manager.update_learning_word(list_name, word, new_eng, new_slo)
            await interaction.response.send_message(f"Updated word in `{list_name}`.\nNew entry: **{final_eng} - {final_slo}**")
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

