"""
stats.py
Soukromé hráčské možnosti – zobrazuje se jen danému hráči (ephemeral).
Připraveno pro navázání na classy v budoucnu.
"""

import discord
from .player_state import get_state
from .items import ITEMS


class StatsView(discord.ui.View):
    """Ephemeral panel 'Moje možnosti' – soukromá hráčská tlačítka."""

    def __init__(self, game_id: str, member: discord.Member, room_players: list[discord.Member]):
        super().__init__(timeout=60)
        self.game_id = game_id
        self.member = member
        self.room_players = room_players

    @discord.ui.button(label="📊 Můj stav", style=discord.ButtonStyle.secondary, custom_id="lab2_my_status")
    async def my_status_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("*Tohle není tvůj panel.*", ephemeral=True)
            return

        state = get_state(self.game_id, self.member)
        equipped_str = (
            f"{ITEMS[state.equipped]['emoji']} {ITEMS[state.equipped]['name']}"
            if state.equipped else "*nic*"
        )
        role_str = "🔪 **Vrah**" if state.is_murderer else "👤 Nevinný"

        embed = discord.Embed(
            title=f"📊 Stav hráče — {self.member.display_name}",
            color=0x8B0000 if state.is_murderer else 0x2B2D31,
        )
        embed.add_field(name="Role", value=role_str, inline=True)
        embed.add_field(name="Stav", value="💚 Naživu" if state.alive else "💀 Mrtvý", inline=True)
        embed.add_field(name="Equipnuto", value=equipped_str, inline=True)
        embed.add_field(name="Předměty v inventáři", value=str(len(state.inventory)), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="👥 Hráči v místnosti", style=discord.ButtonStyle.secondary, custom_id="lab2_room_players")
    async def room_players_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("*Tohle není tvůj panel.*", ephemeral=True)
            return

        lines = [f"↼‶)ᕗ {p.mention}" for p in self.room_players if p.id != self.member.id]
        desc = "\n".join(lines) if lines else "*Jsi tu sám.*"

        embed = discord.Embed(
            title="👥 Ostatní v místnosti",
            description=desc,
            color=0x2B2D31,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Placeholder pro budoucí classy ───────────────────────────────────────
    @discord.ui.button(label="🎭 Schopnost třídy", style=discord.ButtonStyle.primary,
                       custom_id="lab2_class_ability", disabled=True)
    async def class_ability_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("*Schopnosti tříd budou dostupné brzy.*", ephemeral=True)