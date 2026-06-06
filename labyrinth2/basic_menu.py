"""
basic_menu.py
Hlavní herní menu zobrazené na embedu místnosti.
Tlačítka: Inventář hráče | Moje možnosti | Prozkoumat místnost

Vrahova mechanika:
- Tlačítko Zabít NENÍ součástí hlavního menu
- Když hráč vstoupí do místnosti a jsou tam právě 2 živí hráči (vrah + oběť),
  vrahovi se automaticky pošle ephemeral embed s tlačítkem Zabít
- Podmínka: vrah musí mít equipnutou zbraň
"""

import discord
from .player_state import get_state
from .items import ITEMS, SearchView
from .equip import InventoryView, inventory_embed
from .stats import StatsView


async def check_and_send_kill_prompt(
    channel: discord.TextChannel,
    game_id: str,
    players: list[discord.Member],
    room_name: str,
    room_view,  # RoomView reference pro aktualizaci hráčů
):
    """
    Zavolej po každém vstupu do místnosti nebo změně hráčů.
    Pokud jsou v místnosti právě 2 živí hráči a jeden z nich je vrah
    s equipnutou zbraní → pošle mu ephemeral embed s tlačítkem Zabít.
    """
    alive = [p for p in players if get_state(game_id, p).alive]
    if len(alive) != 2:
        return

    murderer = next(
        (p for p in alive if get_state(game_id, p).is_murderer), None
    )
    if murderer is None:
        return

    state = get_state(game_id, murderer)
    victim = next(p for p in alive if p.id != murderer.id)

    weapon_name = None
    weapon_emoji = "🔪"
    if state.equipped and "zbraň" in ITEMS.get(state.equipped, {}).get("tags", []):
        weapon_name = ITEMS[state.equipped]["name"]
        weapon_emoji = ITEMS[state.equipped]["emoji"]

    if weapon_name is None:
        # Nemá zbraň – neposílej prompt (ale mohl by si ji equipnout přes inventář)
        return

    embed = discord.Embed(
        title="🩸 Příležitost",
        description=(
            f"*Jsi sám v místnosti **{room_name}** s {victim.mention}.*\n\n"
            f"V ruce svíráš {weapon_emoji} **{weapon_name}**.\n"
            f"Nikdo se nedívá..."
        ),
        color=0x8B0000,
    )

    view = KillView(game_id, murderer, victim, room_name, room_view)

    # Ephemeral zprávy nelze poslat přes channel.send — musíme použít followup
    # Proto KillView čeká na interakci přes speciální tlačítko které triggeruje DM-like flow.
    # Místo toho pošleme DM vrahovi s tlačítkem.
    try:
        await murderer.send(embed=embed, view=view)
    except discord.Forbidden:
        # Pokud má vrah zavřené DM, fallback: ephemeral přes dummy interakci nejde,
        # tak aspoň poznačíme – v produkci lze řešit přes persistent view + channel.send ephemeral
        pass


class BasicMenuView(discord.ui.View):
    """
    Hlavní view připnutý k embedu místnosti.
    game_id    – unikátní ID hry (např. channel_id jako str)
    players    – všichni hráči v místnosti
    room_name  – název místnosti (např. 'B3')
    """

    def __init__(self, game_id: str, players: list[discord.Member], room_name: str):
        super().__init__(timeout=None)
        self.game_id = game_id
        self.players = players
        self.room_name = room_name

    # ── 1. Inventář ──────────────────────────────────────────────────────────

    @discord.ui.button(label="🎒 Inventář", style=discord.ButtonStyle.secondary,
                       custom_id="lab2_menu_inventory", row=0)
    async def inventory_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("*Nejsi v této místnosti.*", ephemeral=True)
            return

        view = InventoryView(self.game_id, interaction.user)
        embed = inventory_embed(self.game_id, interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ── 2. Moje možnosti ─────────────────────────────────────────────────────

    @discord.ui.button(label="⚙️ Moje možnosti", style=discord.ButtonStyle.secondary,
                       custom_id="lab2_menu_stats", row=0)
    async def stats_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("*Nejsi v této místnosti.*", ephemeral=True)
            return

        view = StatsView(self.game_id, interaction.user, self.players)
        embed = discord.Embed(
            title="⚙️ Moje možnosti",
            description="*Soukromý panel pouze pro tebe.*",
            color=0x2B2D31,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ── 3. Prozkoumat místnost ───────────────────────────────────────────────

    @discord.ui.button(label="🔍 Prozkoumat místnost", style=discord.ButtonStyle.primary,
                       custom_id="lab2_menu_explore", row=0)
    async def explore_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("*Nejsi v této místnosti.*", ephemeral=True)
            return

        view = SearchView(self.game_id, interaction.user, self.room_name)
        embed = discord.Embed(
            title=f"🔍 Průzkum — {self.room_name}",
            description="*Rozhlédneš se po místnosti a začneš prohledávat každý kout...*",
            color=0x2B2D31,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class KillView(discord.ui.View):
    """
    View poslaný vrahovi do DM.
    Zobrazuje tlačítko Zabít s jasnou obětí (jsou jen 2 v místnosti).
    """

    def __init__(self, game_id: str, murderer: discord.Member,
                 victim: discord.Member, room_name: str, room_view):
        super().__init__(timeout=60)
        self.game_id = game_id
        self.murderer = murderer
        self.victim = victim
        self.room_name = room_name
        self.room_view = room_view

    @discord.ui.button(label="🔪 Zabít", style=discord.ButtonStyle.danger, custom_id="lab2_dm_kill")
    async def kill_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.murderer.id:
            await interaction.response.send_message("*Tohle není tvoje akce.*", ephemeral=True)
            return

        victim_state = get_state(self.game_id, self.victim)
        if not victim_state.alive:
            await interaction.response.send_message("*Tato osoba je již mrtvá.*", ephemeral=True)
            return

        # Ověř že jsou stále oba v místnosti
        if self.victim not in self.room_view.players:
            await interaction.response.send_message(
                "*Oběť už opustila místnost. Příležitost zmizela.*", ephemeral=True
            )
            return

        # Zabití
        victim_state.alive = False
        self.room_view.players = [p for p in self.room_view.players if p.id != self.victim.id]
        button.disabled = True

        # Potvrzení vrahovi do DM
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="✅ Hotovo",
                description=f"*{self.victim.display_name} byl umlčen.*",
                color=0x8B0000,
            ),
            view=self,
        )

        # Veřejné oznámení do herního kanálu
        # Kanál najdeme přes guild — game_id je channel_id
        guild = self.murderer.guild
        if guild:
            channel = guild.get_channel(int(self.game_id))
            if channel:
                embed = discord.Embed(
                    title="💀 Někdo byl nalezen mrtvý",
                    description=(
                        f"*{self.victim.mention} byl nalezen mrtvý "
                        f"v místnosti **{self.room_name}**...*\n\n"
                        f"Tma pohltila další duši."
                    ),
                    color=0x8B0000,
                )
                await channel.send(embed=embed)

    @discord.ui.button(label="Přehodnotit", style=discord.ButtonStyle.secondary, custom_id="lab2_dm_cancel")
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="👁️ Přehodnotil jsi to",
                description="*Tentokrát jsi nechal oběť žít. Příležitost se může vrátit...*",
                color=0x2B2D31,
            ),
            view=None,
        )