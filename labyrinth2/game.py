"""
game.py
Herní logika místností s kompasovým systémem a vláknovým pohybem.

Každá skupina hráčů ve stejné místnosti sdílí jedno Discord vlákno.
P�i rozdělení u dveří vznikají nová vlákna pro každou podskupinu.
"""

import discord
import random
from collections import Counter

from .player_state import init_game
from .basic_menu import BasicMenuView, check_and_send_kill_prompt
from .thread_manager import create_thread, move_group_to_room, archive_thread

# channel_id -> RoomView  (pro /roll příkaz)
active_rooms: dict[int, "RoomView"] = {}

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

DIRECTION_EMOJI  = {"N": "⬆️", "S": "⬇️", "W": "⬅️", "E": "➡️"}
DIRECTION_LABEL  = {"N": "Sever", "S": "Jih", "W": "Západ", "E": "Východ"}
DOOR_COLORS = {
    0: ("🔴", "Červené"),
    1: ("🔵", "Modré"),
    2: ("🟢", "Zelené"),
    3: ("🟡", "Žluté"),
}


# ── Souřadnicové pomocné funkce ───────────────────────────────────────────────

def parse_coord(room_name: str) -> tuple[str, int]:
    return room_name[0], int(room_name[1:])

def format_coord(col: str, row: int) -> str:
    return f"{col}{row}"

def col_index(col: str) -> int:
    return ALPHABET.index(col)

def get_available_directions(room_name: str, rows: int, cols: int) -> list[str]:
    col, row = parse_coord(room_name)
    cidx = col_index(col)
    dirs = []
    if row > 1:        dirs.append("N")
    if row < rows:     dirs.append("S")
    if cidx > 0:       dirs.append("W")
    if cidx < cols-1:  dirs.append("E")
    return dirs

def neighbor_in_direction(room_name: str, direction: str) -> str:
    col, row = parse_coord(room_name)
    cidx = col_index(col)
    if direction == "N": return format_coord(col, row - 1)
    if direction == "S": return format_coord(col, row + 1)
    if direction == "W": return format_coord(ALPHABET[cidx - 1], row)
    if direction == "E": return format_coord(ALPHABET[cidx + 1], row)

def opposite_direction(d: str) -> str:
    return {"N": "S", "S": "N", "W": "E", "E": "W"}[d]

def dice_sides(room_name: str, rows: int, cols: int) -> int:
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
        came_from: str = None,
        parent_channel: discord.TextChannel = None,
        thread: discord.Thread = None,
    ):
        super().__init__(timeout=None)
        self.players = list(players)          # kopie, ne reference
        self.room_name = room_name
        self.room_id = room_id or room_name
        self.map_rows = map_rows
        self.map_cols = map_cols
        self.game_id = game_id or room_name
        self.came_from = came_from
        self.parent_channel = parent_channel  # původní lobby kanál
        self.thread = thread                  # vlákno této skupiny
        self.choices: dict[int, str] = {}     # user_id -> direction
        self.directions: list[tuple[str, int]] = []
        self.message: discord.Message = None

    @property
    def send_target(self) -> discord.abc.Messageable:
        """Kam posílat zprávy — vlákno pokud existuje, jinak kanál."""
        return self.thread or self.parent_channel

    def _create_embed(self) -> discord.Embed:
        dirs = get_available_directions(self.room_name, self.map_rows, self.map_cols)
        sides = len(dirs)
        corner_note = " *(rohová)*" if sides == 2 else (" *(okrajová)*" if sides == 3 else "")

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
        dir_lines = []
        for d in dirs:
            neighbor = neighbor_in_direction(self.room_name, d)
            dir_lines.append(f"{DIRECTION_EMOJI[d]} **{DIRECTION_LABEL[d]}** → `{neighbor}`")
        embed.add_field(name="🧭 Východy", value="\n".join(dir_lines), inline=False)
        return embed

    def _waiting_embed(self) -> discord.Embed:
        """Embed zobrazující kdo už si vybral dveře a kdo čeká."""
        lines = []
        for p in self.players:
            if p.id in self.choices:
                d = self.choices[p.id]
                lines.append(f"✅ {p.display_name} → {DIRECTION_EMOJI[d]} {DIRECTION_LABEL[d]}")
            else:
                lines.append(f"⏳ {p.display_name} — čeká...")
        embed = discord.Embed(
            title=f"🚪 Místnost [{self.room_name}] — čekáme",
            description="\n".join(lines),
            color=0x2B2D31,
        )
        return embed

    def _build_menu(self) -> "BasicMenuView":
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
                f"Tato místnost má **{sides} průchodů** — kostky mají **{sides} stěn**.\n\n"
                f"👉 **Použij příkaz `/roll {sides}`** pro hození {n_players} kostkami!"
            ),
            color=0x2B2D31,
        )

        await interaction.response.edit_message(view=self)
        await self.send_target.send(embed=embed)
        active_rooms[interaction.channel_id] = self

    def apply_roll_and_show_doors(self, rolls: list[int]):
        available = get_available_directions(self.room_name, self.map_rows, self.map_cols)
        caps = rolls[:len(available)]
        while len(caps) < len(available):
            caps.append(1)

        self.directions = list(zip(available, caps))

        for i, (direction, cap) in enumerate(self.directions):
            emoji, _ = DOOR_COLORS[i]
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

            # Zaznamenej volbu, sniž kapacitu
            self.directions[door_index] = (direction, cap - 1)
            self.choices[interaction.user.id] = direction

            # Aktualizuj label
            new_cap = cap - 1
            neighbor = neighbor_in_direction(self.room_name, direction)
            emoji, _ = DOOR_COLORS[door_index]
            for item in self.children:
                if getattr(item, "custom_id", "") == f"lab2_door_{door_index}":
                    item.label = f"{emoji} {DIRECTION_LABEL[direction]} → {neighbor} [{new_cap}]"
                    if new_cap == 0:
                        item.disabled = True
                    break

            # Všichni zvolili?
            if len(self.choices) < len(self.players):
                # Ukaž waiting embed
                await interaction.response.edit_message(
                    embed=self._waiting_embed(), view=self
                )
                return

            # ── Všichni zvolili → rozdělení do skupin ────────────────────────
            await interaction.response.edit_message(
                content=f"*Skupina opouští místnost {self.room_name}...*",
                embed=None, view=None,
            )

            # Seskup hráče podle zvoleného směru
            groups: dict[str, list[discord.Member]] = {}
            for player in self.players:
                d = self.choices[player.id]
                groups.setdefault(d, []).append(player)

            original_players = list(self.players)

            for chosen_dir, subgroup in groups.items():
                next_room_name = neighbor_in_direction(self.room_name, chosen_dir)

                # Přesuň skupinu do vlákna (přejmenuj nebo vytvoř nové)
                new_thread = await move_group_to_room(
                    parent_channel=self.parent_channel,
                    game_id=self.game_id,
                    old_players=original_players,
                    subgroup=subgroup,
                    from_room=self.room_name,
                    to_room=next_room_name,
                    direction_label=DIRECTION_LABEL[chosen_dir],
                )

                next_view = RoomView(
                    players=subgroup,
                    room_name=next_room_name,
                    map_rows=self.map_rows,
                    map_cols=self.map_cols,
                    game_id=self.game_id,
                    came_from=opposite_direction(chosen_dir),
                    parent_channel=self.parent_channel,
                    thread=new_thread,
                )
                menu_view = next_view._build_menu()

                msg = await new_thread.send(
                    embed=next_view._create_embed(), view=next_view
                )
                next_view.message = msg
                await new_thread.send(view=menu_view)

                await check_and_send_kill_prompt(
                    new_thread, next_view.game_id,
                    next_view.players, next_view.room_name, next_view,
                )

        return callback