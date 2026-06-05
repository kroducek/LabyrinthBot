import discord
from discord.ext import commands
from discord import app_commands

class LabyrinthLobby(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=None)
        self.author = author
        self.players: list[discord.Member] = [author]
        self.max_players = 12
        self.update_start_button()

    def _embed(self) -> discord.Embed:
        title = f"Labyrinth by Arion *(v.0.3)* - LOBBY {len(self.players)}/{self.max_players}"
        description = (
            "*Vstupujete do temnoty, odkud není snadného návratu...*\n"
            "*Připravte se na zkoušku důvěry a přežití.*\n\n"
            "**Seznam hráčů:**\n"
        )
        if not self.players:
            description += "*Zatím tu nikdo není...*"
        else:
            description += "\n".join(f"↼‶)ᕗ {p.mention}" for p in self.players)

        embed = discord.Embed(
            title=title,
            description=description,
            color=0x2B2D31  # Tmavá, cozy Discord barva
        )
        embed.set_footer(text="Čekáme na další odvážlivce...")
        return embed

    def update_start_button(self):
        # Dynamically updates the "Začít hru" button text and color
        start_button = discord.utils.get(self.children, custom_id="lab2_start")
        if start_button:
            start_button.label = f"Začít hru ({len(self.players)}/{self.max_players})"
            # Example conditions for readying up
            if len(self.players) == self.max_players:
                start_button.style = discord.ButtonStyle.success
            elif len(self.players) >= 6:
                start_button.style = discord.ButtonStyle.primary
            else:
                start_button.style = discord.ButtonStyle.secondary

    @discord.ui.button(label="Připojit se", style=discord.ButtonStyle.success, custom_id="lab2_join", row=0)
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            await interaction.response.send_message("*Už jsi v lobby, dobrodruhu.*", ephemeral=True)
            return
        if len(self.players) >= self.max_players:
            await interaction.response.send_message("*Lobby je plné!*", ephemeral=True)
            return
            
        self.players.append(interaction.user)
        self.update_start_button()
        await interaction.response.edit_message(embed=self._embed(), view=self)

    @discord.ui.button(label="Odejít", style=discord.ButtonStyle.danger, custom_id="lab2_leave", row=0)
    async def leave_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("*Nejsi v lobby.*", ephemeral=True)
            return
        
        self.players.remove(interaction.user)
        self.update_start_button()
        await interaction.response.edit_message(embed=self._embed(), view=self)

    @discord.ui.button(label="Začít hru (1/12)", style=discord.ButtonStyle.secondary, custom_id="lab2_start", row=0)
    async def start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("*Hru může spustit pouze zakladatel.*", ephemeral=True)
            return
        
        if len(self.players) < 2:
            await interaction.response.send_message("*Na spuštění hry je potřeba více hráčů (min. 2).*!", ephemeral=True)
            return
            
        # Zde bude inicializace hry do budoucna
        await interaction.response.edit_message(content="*Hra brzy začne... připravte se na temnotu.*", embed=None, view=None)

    @discord.ui.button(label="Pravidla", style=discord.ButtonStyle.secondary, custom_id="lab2_rules", row=1)
    async def rules_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📜 Pravidla Labyrintu",
            description=(
                "*Temnota skrývá mnohá tajemství. Zde jsou základní pravidla přežití:*\n\n"
                "**1.** Věř pouze sobě (nebo nikomu).\n"
                "**2.** Zkoumej, hledej stopy a zkus uniknout.\n"
                "**3.** Vrah je mezi vámi. Kdo to je?\n\n"
                "*(Další pravidla budou doplněna...)*"
            ),
            color=0xA9A9A9
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Classy", style=discord.ButtonStyle.secondary, custom_id="lab2_classes", row=1)
    async def classes_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎭 Dostupné Třídy",
            description=(
                "*Každý má svou roli v tomto příběhu. Jaká bude ta tvá?*\n\n"
                "**Nevinní:**\n"
                "🕵️ *Detektiv* - Zkušený vyšetřovatel\n"
                "💊 *Doktor* - Může léčit a oživovat\n"
                "👁️ *Skaut* - Rychlý průzkumník\n"
                "📡 *Technik* - Zvládá operovat s generátorem\n"
                "🃏 *Blázen* - Nevyzpytatelný element\n\n"
                "**Vrazi:**\n"
                "🎭 *Manipulátor* - Ovládá mysl ostatních\n"
                "🪤 *Pastičkář* - Klade smrtící pasti\n"
                "🔪 *Sériový vrah* - Nemilosrdný zabiják\n"
            ),
            color=0x483D8B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class LobbyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="lobby", description="Vytvoří novou Labyrinth 2.0 lobby")
    async def create_lobby(self, interaction: discord.Interaction):
        view = LabyrinthLobby(interaction.user)
        await interaction.response.send_message(embed=view._embed(), view=view)

async def setup(bot):
    await bot.add_cog(LobbyCog(bot))
