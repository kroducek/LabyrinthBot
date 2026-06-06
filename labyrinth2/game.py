"""
game.py
Herní logika místností s kompasovým systémem.

Souřadnicový systém:
  - Sloupce = písmena A, B, C... (osa X, západ→východ)
  - Řádky   = čísla 1, 2, 3...  (osa Y, sever→jih)
  - Příklad 4x4: A1 B1 C1 D1
                 A2 B2 C2 D2
                 A3 B3 C3 D3
                 A4 B4 C4 D4

Dveře:
  - Sever (N) = row - 1   (existuje jen pokud row > 1)
  - Jih   (S) = row + 1   (existuje jen pokud row < rows)
  - Západ (W) = col - 1   (existuje jen pokud col_idx > 0)
  - Východ(E) = col + 1   (existuje jen pokud col_idx < cols-1)

Počet kostek:
  - Rohová místnost    → 2 stěny
  - Okrajová místnost  → 3 stěny
  - Vnitřní místnost   → 4 stěny
"""

import discord
import random

from .player_state import init_game
from .basic_menu import BasicMenuView, check_and_send_kill_prompt

# channel_id -> RoomView
active_rooms = {}

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

DIRECTION_EMOJI = {"N": "⬆️", "S": "⬇️", "W": "⬅️", "E": "➡️"}
DIRECTION_LABEL = {"N": "Sever", "S": "Jih", "W": "Západ", "E": "Východ"}
DOOR_COLORS = {
    0: ("🔴", "Červené"),
    1: ("🔵", "Modré"),
    2: ("🟢", "Zelené"),
    3: ("🟡", "Žluté"),
}


# ── Souřadnicové pomocné funkce ───────────────────────────────────────────────

def parse_coord(room_name: str) -> tuple[str, int]:
    """'B3' → ('B', 3)"""
    return room_name[0], int(room_name[1:])

def format_coord(col: str, row: int) -> str:
    return f"{col}{row}"

def col_index(col: str) -> int:
    return ALPHABET.index(col)

def get_available_directions(room_name: str, rows: int, cols: int) -> list[str]:
    """Vrátí seřazený seznam směrů (N/S/W/E) které existují z dané místnosti."""
    col, row = parse_coord(room_name)
    cidx = col_index(col)
    dirs = []
    if row > 1:        dirs.append("N")
    if row < rows:     dirs.append("S")
    if cidx > 0:       dirs.append("W")
    if cidx < cols-1:  dirs.append("E")
    return dirs  # max 4, rohová 2, okrajová 3

def neighbor_in_direction(room_name: str, direction: str) -> str:
    """Vrátí souřadnici sousední místnosti daným směrem."""
    col, row = parse_coord(room_name)
    cidx = col_index(col)
    if direction == "N": return format_coord(col, row - 1)
    if direction == "S": return format_coord(col, row + 1)
    if direction == "W": return format_coord(ALPHABET[cidx - 1], row)
    if direction == "E": return format_coord(ALPHABET[cidx + 1], row)

def opposite_direction(d: str) -> str:
    return {"N": "S", "S": "N", "W": "E", "E": "W"}[d]

def dice_sides(room_name: str, rows: int, cols: int) -> int:
    """Počet stran kostek = počet dostupných směrů."""
    return len(get_available_directions(room_name, rows, cols))


# ── RoomView ──────────────────────────────────────────────────────────────────

class RoomView(discord.ui.View):
    def __init__(
        self,
        players: list[discord.Member],
        room_name: str = "A1",
        room_id: str = None,
        map_rows: int = 4,
        map_cols: int = 4,
        game_id: str = None,
        came_from: str = None,   # směr odkud hráči přišli (pro zpětnou referenci)
    ):
        super().__init__(timeout=None)
        self.players = players
        self.room_name = room_name
        self.room_id = room_id or room_name
        self.map_rows = map_rows
        self.map_cols = map_cols
        self.game_id = game_id or room_name
        self.came_from = came_from   # např. "S" = přišli ze severu (= dveře na jih vedou zpět)
        self.choices = {}            # user_id -> direction
        # directions[i] = (direction_str, capacity)
        self.directions: list[tuple[str, int]] = []
        self.message: discord.Message = None

    def _create_embed(self) -> discord.Embed:
        dirs = get_available_directions(self.room_name, self.map_rows, self.map_cols)
        sides = len(dirs)
        corner_note = " *(rohová — 2 průchody)*" if sides == 2 else (
                      " *(okrajová — 3 průchody)*" if sides == 3 else "")

        embed = discord.Embed(
            title=f"🚪 Místnost [{self.room_name}]{corner_note}",
            description=(
                f"*Ocitáte se v temné, chladné místnosti {self.room_name}.*\n"
                "*Vzduch je těžký a ticho přerušuje jen vaše dýchání.*\n\n"
                "Uprostřed místnosti stojí malý kamenný podstavec s vyrytými symboly.\n\n"
                f"**Hráči zde ({len(self.players)}):** " +
                ", ".join(p.display_name for p in self.players)
            ),
            color=0x2B2D31,
        )
        # Přehled dostupných směrů
        dir_lines = []
        for d in dirs:
            neighbor = neighbor_in_direction(self.room_name, d)
            dir_lines.append(f"{DIRECTION_EMOJI[d]} **{DIRECTION_LABEL[d]}** → `{neighbor}`")
        embed.add_field(name="🧭 Východy", value="\n".join(dir_lines), inline=False)
        return embed

    def _build_menu(self) -> BasicMenuView:
        return BasicMenuView(
            game_id=self.game_id,
            players=self.players,
            room_name=self.room_name,
            map_rows=self.map_rows,
            map_cols=self.map_cols,
        )

    @discord.ui.button(label="🎲 Vzít kostky na podstavci", style=discord.ButtonStyle.primary,
                       custom_id="lab2_take_dice")
    async def take_dice_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("*Nejsi v této místnosti.*", ephemeral=True)
            return

        self.remove_item(button)

        sides = dice_sides(self.room_name, self.map_rows, self.map_cols)
        n_players = max(1, len(self.players))

        embed = discord.Embed(
            title="🎲 Házení kostkami",
            description=(
                f"**{interaction.user.display_name}** přistoupil k podstavci a vzal si kostky.\n\n"
                f"Tato místnost má **{sides} průchody** — kostky mají **{sides} stěn**.\n\n"
                f"👉 **Použij příkaz `/roll {sides}`** pro hození {n_players} kostkami!"
            ),
            color=0x2B2D31,
        )

        await interaction.response.edit_message(view=self)
        await interaction.channel.send(embed=embed)
        active_rooms[interaction.channel_id] = self

    def apply_roll_and_show_doors(self, rolls: list[int]):
        """
        rolls = výsledky hodů (jeden hod za dveře).
        Přiřadí kapacity ke směrům a zobrazí tlačítka s kompasem.
        """
        available = get_available_directions(self.room_name, self.map_rows, self.map_cols)
        # rolls může mít méně hodnot než směrů — zarovnáme
        caps = rolls[:len(available)]
        while len(caps) < len(available):
            caps.append(1)

        self.directions = [(d, c) for d, c in zip(available, caps)]

        for i, (direction, cap) in enumerate(self.directions):
            emoji, color_name = DOOR_COLORS[i]
            neighbor = neighbor_in_direction(self.room_name, direction)
            btn = discord.ui.Button(
                label=f"{emoji} {DIRECTION_LABEL[direction]} → {neighbor} [{cap}]",
                style=discord.ButtonStyle.secondary,
                custom_id=f"lab2_door_{i}",
            )
            btn.callback = self.make_door_callback(i)
            self.add_item(btn)

    def make_door_callback(self, door_index: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user not in self.players:
                await interaction.response.send_message("*Nejsi v této místnosti.*", ephemeral=True)
                return

            if interaction.user.id in self.choices:
                await interaction.response.send_message("*Své rozhodnutí už jsi učinil!*", ephemeral=True)
                return

            direction, cap = self.directions[door_index]

            if cap <= 0:
                await interaction.response.send_message(
                    "*Tato cesta je už plná! Musíš jinudy.*", ephemeral=True
                )
                return

            # Sniž kapacitu
            self.directions[door_index] = (direction, cap - 1)
            self.choices[interaction.user.id] = direction

            # Aktualizuj label tlačítka
            new_cap = cap - 1
            neighbor = neighbor_in_direction(self.room_name, direction)
            emoji, _ = DOOR_COLORS[door_index]
            for item in self.children:
                if getattr(item, "custom_id", "") == f"lab2_door_{door_index}":
                    item.label = f"{emoji} {DIRECTION_LABEL[direction]} → {neighbor} [{new_cap}]"
                    if new_cap == 0:
                        item.disabled = True
                    break

            if len(self.choices) == len(self.players):
                # Zjisti nejčastější zvolený směr (příp. prvního)
                # Každý hráč si vybral směr — seskupíme podle směru
                from collections import Counter
                direction_counts = Counter(self.choices.values())
                chosen_direction = direction_counts.most_common(1)[0][0]
                next_room_name = neighbor_in_direction(self.room_name, chosen_direction)

                next_view = RoomView(
                    self.players,
                    next_room_name,
                    map_rows=self.map_rows,
                    map_cols=self.map_cols,
                    game_id=self.game_id,
                    came_from=opposite_direction(chosen_direction),
                )
                menu_view = next_view._build_menu()

                await interaction.response.edit_message(
                    content=f"*Všichni prošli {DIRECTION_EMOJI[chosen_direction]} "
                            f"{DIRECTION_LABEL[chosen_direction]}em do místnosti {next_room_name}...*",
                    embed=None,
                    view=None,
                )
                msg = await interaction.channel.send(
                    embed=next_view._create_embed(), view=next_view
                )
                next_view.message = msg
                await interaction.channel.send(view=menu_view)
                await check_and_send_kill_prompt(
                    interaction.channel, next_view.game_id,
                    next_view.players, next_view.room_name, next_view,
                )
            else:
                await interaction.response.edit_message(view=self)

        return callback