"""
basic_menu.py
Hlavní herní menu místnosti.
Tlačítka: Inventář | Moje možnosti | Prozkoumat místnost | Mapa
"""

import discord
from .player_state import get_state
from .items import ITEMS, SearchView
from .equip import InventoryView, inventory_embed
from .stats import StatsView

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIRECTION_EMOJI = {"N": "⬆️", "S": "⬇️", "W": "⬅️", "E": "➡️"}
DIRECTION_LABEL = {"N": "Sever", "S": "Jih", "W": "Západ", "E": "Východ"}


def _parse_coord(room_name: str) -> tuple[str, int]:
    return room_name[0], int(room_name[1:])

def _neighbor(room_name: str, direction: str, rows: int, cols: int) -> str | None:
    col, row = _parse_coord(room_name)
    cidx = ALPHABET.index(col)
    if direction == "N": return f"{col}{row-1}" if row > 1 else None
    if direction == "S": return f"{col}{row+1}" if row < rows else None
    if direction == "W": return f"{ALPHABET[cidx-1]}{row}" if cidx > 0 else None
    if direction == "E": return f"{ALPHABET[cidx+1]}{row}" if cidx < cols-1 else None

def _map_embed(room_name: str, map_rows: int, map_cols: int) -> discord.Embed:
    """Ephemeral mapa — ukáže hráči jeho pozici a okolní místnosti."""
    col, row = _parse_coord(room_name)

    lines = []
    for direction in ["N", "S", "W", "E"]:
        neighbor = _neighbor(room_name, direction, map_rows, map_cols)
        if neighbor:
            lines.append(
                f"{DIRECTION_EMOJI[direction]} **{DIRECTION_LABEL[direction]}** → `{neighbor}`"
            )
        else:
            lines.append(f"{DIRECTION_EMOJI[direction]} **{DIRECTION_LABEL[direction]}** → *zeď*")

    # Malá ASCII mapa 3x3 okolí
    def cell(c: str, r: int) -> str:
        name = f"{c}{r}"
        if name == room_name:
            return "[ ]"   # ty
        return f" {name} " if 1 <= r <= map_rows and 0 <= ALPHABET.index(c) < map_cols else "    "

    cidx = ALPHABET.index(col)
    rows_ascii = []
    for dr in [-1, 0, 1]:
        r = row + dr
        row_cells = []
        for dc in [-1, 0, 1]:
            ci = cidx + dc
            if 0 <= ci < map_cols and 1 <= r <= map_rows:
                c = ALPHABET[ci]
                marker = "◉  " if f"{c}{r}" == room_name else f"{c}{r} "
                row_cells.append(marker)
            else:
                row_cells.append("   ")
        rows_ascii.append(" | ".join(row_cells))
    ascii_map = "\n".join(rows_ascii)

    embed = discord.Embed(
        title=f"🧭 Mapa — jsi v `{room_name}`",
        description=(
            f"```\n{ascii_map}\n```\n"
            + "\n".join(lines)
        ),
        color=0x2B2D31,
    )
    embed.set_footer(text="◉ = tvoje pozice  |  mapa zobrazuje bezprostřední okolí")
    return embed


async def check_and_send_kill_prompt(
    channel: discord.TextChannel,
    game_id: str,
    players: list[discord.Member],
    room_name: str,
    room_view,
):
    """Pošle vrahovi DM s tlačítkem Zabít, pokud jsou v místnosti jen 2 živí."""
    alive = [p for p in players if get_state(game_id, p).alive]
    if len(alive) != 2:
        return

    murderer = next((p for p in alive if get_state(game_id, p).is_murderer), None)
    if murderer is None:
        return

    state = get_state(game_id, murderer)
    victim = next(p for p in alive if p.id != murderer.id)

    if not state.equipped or "zbraň" not in ITEMS.get(state.equipped, {}).get("tags", []):
        return

    weapon = ITEMS[state.equipped]

    embed = discord.Embed(
        title="🩸 Příležitost",
        description=(
            f"*Jsi sám v místnosti **{room_name}** s {victim.mention}.*\n\n"
            f"V ruce svíráš {weapon['emoji']} **{weapon['name']}**.\n"
            f"Nikdo se nedívá..."
        ),
        color=0x8B0000,
    )
    view = KillView(game_id, murderer, victim, room_name, room_view)
    try:
        await murderer.send(embed=embed, view=view)
    except discord.Forbidden:
        pass


# ── Views ─────────────────────────────────────────────────────────────────────

class BasicMenuView(discord.ui.View):
    def __init__(self, game_id: str, players: list[discord.Member],
                 room_name: str, map_rows: int = 4, map_cols: int = 4,
                 room_id: str = None, room_state: dict = None):
        super().__init__(timeout=None)
        self.game_id = game_id
        self.players = players
        self.room_name = room_name
        self.room_id = room_id or room_name
        self.room_state = room_state or {}
        self.map_rows = map_rows
        self.map_cols = map_cols

    @discord.ui.button(label="🎒 Inventář", style=discord.ButtonStyle.secondary,
                       custom_id="lab2_menu_inventory", row=0)
    async def inventory_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("*Nejsi v této místnosti.*", ephemeral=True)
            return
        view = InventoryView(self.game_id, interaction.user)
        embed = inventory_embed(self.game_id, interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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

    @discord.ui.button(label="🔍 Prozkoumat místnost", style=discord.ButtonStyle.primary,
                       custom_id="lab2_menu_explore", row=0)
    async def explore_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("*Nejsi v této místnosti.*", ephemeral=True)
            return
        view = SearchView(self.game_id, interaction.user, self.room_name, room_id=self.room_id, room_state=self.room_state)
        embed = discord.Embed(
            title=f"🔍 Průzkum — {self.room_name}",
            description="*Rozhlédneš se po místnosti a začneš prohledávat každý kout...*",
            color=0x2B2D31,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🗺️ Mapa", style=discord.ButtonStyle.secondary,
                       custom_id="lab2_menu_map", row=1)
    async def map_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("*Nejsi v této místnosti.*", ephemeral=True)
            return
        embed = _map_embed(self.room_name, self.map_rows, self.map_cols)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class KillView(discord.ui.View):
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

        if self.victim not in self.room_view.players:
            await interaction.response.send_message(
                "*Oběť už opustila místnost. Příležitost zmizela.*", ephemeral=True
            )
            return

        victim_state.alive = False
        self.room_view.players = [p for p in self.room_view.players if p.id != self.victim.id]
        button.disabled = True

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="✅ Hotovo",
                description=f"*{self.victim.display_name} byl umlčen.*",
                color=0x8B0000,
            ),
            view=self,
        )

        # Pošli oznámení do vlákna skupiny (nebo fallback na parent kanál)
        target = getattr(self.room_view, 'send_target', None)
        if target:
            await target.send(embed=discord.Embed(
                title="💀 Někdo byl nalezen mrtvý",
                description=(
                    f"*{self.victim.mention} byl nalezen mrtvý "
                    f"v místnosti **{self.room_name}**...*\n\nTma pohltila další duši."
                ),
                color=0x8B0000,
            ))

async def _escape_broadcast(interaction: discord.Interaction, game_id: str, escaped_player):
    """Broadcastuje útěk hráče do všech vláken hry."""
    from .thread_manager import game_threads
    threads = game_threads.get(game_id, {})
    embed = discord.Embed(
        title="🚨 ÚTĚK Z LABYRINTU",
        description=(
            f"**{escaped_player.display_name}** nastartoval generátor a otevřel kovové dveře!\n\n"
            f"*{escaped_player.mention} úspěšně utekl z labyrintu...*"
        ),
        color=0xFFD700,
    )
    for thread in threads.values():
        try:
            await thread.send(embed=embed)
        except Exception:
            pass


    @discord.ui.button(label="Přehodnotit", style=discord.ButtonStyle.secondary,
                       custom_id="lab2_dm_cancel")
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="👁️ Přehodnotil jsi to",
                description="*Tentokrát jsi nechal oběť žít...*",
                color=0x2B2D31,
            ),
            view=None,
        )