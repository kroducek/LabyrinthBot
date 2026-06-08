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
from .rooms import get_random_room_id, get_room_data, get_unique_room_ids

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# game_id -> { room_name -> room_id }   (předgenerovaná mapa typů místností)
game_room_map: dict[str, dict[str, str]] = {}
# game_id -> { room_name -> dict }      (sdílený stav místnosti, např. palivo generátoru)
game_room_state: dict[str, dict[str, dict]] = {}


def give_murderer_start_items(game_id: str, players: list):
    """Dá vrahu startovní předměty pro testování. Volej po init_game."""
    from .player_state import get_state
    for p in players:
        state = get_state(game_id, p)
        if getattr(state, "is_murderer", False):
            for _ in range(3):
                state.inventory.append("canister")
            break


def generate_room_map(game_id: str, rows: int, cols: int) -> dict[str, str]:
    """Předgeneruje typy místností pro celou mapu. Unique místnosti se přiřadí náhodně."""
    if game_id in game_room_map:
        return game_room_map[game_id]

    room_map: dict[str, str] = {}

    # Collect non-corner coords
    non_corner = []
    for r in range(1, rows + 1):
        for ci in range(cols):
            is_corner = (r in (1, rows)) and (ci in (0, cols - 1))
            coord = f"{ALPHABET[ci]}{r}"
            if is_corner:
                room_map[coord] = "labyrinth_hub"
            else:
                non_corner.append(coord)

    # Přiřaď unique místnosti (např. exit_room) náhodně
    unique_ids = get_unique_room_ids()
    unique_coords = random.sample(non_corner, min(len(unique_ids), len(non_corner)))
    for coord, uid in zip(unique_coords, unique_ids):
        room_map[coord] = uid

    # Zbytek náhodně
    for coord in non_corner:
        if coord not in room_map:
            room_map[coord] = get_random_room_id(exclude_hub=True)

    game_room_map[game_id] = room_map
    game_room_state[game_id] = {}
    return room_map


def get_room_id_for(game_id: str, room_name: str, map_rows: int, map_cols: int) -> str:
    """Vrátí room_id pro konkrétní souřadnici — generuje mapu pokud ještě neexistuje."""
    room_map = generate_room_map(game_id, map_rows, map_cols)
    return room_map.get(room_name, "labyrinth_hub")


def get_room_state(game_id: str, room_name: str) -> dict:
    """Vrátí sdílený stav místnosti (vytvoří prázdný pokud neexistuje)."""
    states = game_room_state.setdefault(game_id, {})
    return states.setdefault(room_name, {})

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
        # Pokud room_id není zadáno, načti z předgenerované mapy hry
        if room_id is None:
            gid = game_id or room_name
            room_id = get_room_id_for(gid, room_name, map_rows, map_cols)
        self.room_id = room_id
        self.map_rows = map_rows
        self.map_cols = map_cols
        self.game_id = game_id or room_name
        self.came_from = came_from
        self.parent_channel = parent_channel  # původní lobby kanál
        self.thread = thread                  # vlákno této skupiny
        self.choices: dict[int, str] = {}     # user_id -> direction
        self.directions: list[tuple[str, int]] = []
        self.message: discord.Message = None
        self.room_state: dict = get_room_state(self.game_id, room_name)

    @property
    def send_target(self) -> discord.abc.Messageable:
        """Kam posílat zprávy — vlákno pokud existuje, jinak kanál."""
        return self.thread or self.parent_channel

    def _create_embed(self) -> discord.Embed:
        dirs = get_available_directions(self.room_name, self.map_rows, self.map_cols)
        sides = len(dirs)
        corner_note = " *(rohová)*" if sides == 2 else (" *(okrajová)*" if sides == 3 else "")

        embed = discord.Embed(
            title=f"🚪 [{self.room_name}] {get_room_data(self.room_id)['name']}{corner_note}",
            description=(
                f"*{get_room_data(self.room_id)['description']}*\n\n"
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
            room_id=self.room_id,
            room_state=self.room_state,
        )

    @discord.ui.button(label="🎲 Vzít kostky na podstavci", style=discord.ButtonStyle.primary,
                       custom_id="lab2_take_dice")
    async def take_dice_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("*Nejsi v této místnosti.*", ephemeral=True)
            return

        self.remove_item(button)
        await interaction.response.edit_message(view=self)

        sides = dice_sides(self.room_name, self.map_rows, self.map_cols)

        embed = discord.Embed(
            title="🎲 Kostky sebrány",
            description=(
                f"**{interaction.user.display_name}** přistoupil k podstavci a sebral kostky.\n\n"
                f"Místnost má **{sides} průchodů** — kostky mají **{sides} stěn**.\n\n"
                "*Co uděláš s kostkami?*"
            ),
            color=0x2B2D31,
        )

        dice_view = DiceView(room_view=self, holder=interaction.user, sides=sides)
        await self.send_target.send(embed=embed, view=dice_view)

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
                    # Zakáž až po zpracování — hráč který snížil na 0 prošel jako poslední
                    if new_cap == 0 and len(self.choices) < len(self.players):
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

# ── DiceView ──────────────────────────────────────────────────────────────────

class DiceView(discord.ui.View):
    """Zobrazí se po sebrání kostek — hráč může hodit nebo položit zpět."""

    def __init__(self, room_view: "RoomView", holder: discord.Member, sides: int):
        super().__init__(timeout=None)
        self.room_view = room_view
        self.holder = holder
        self.sides = sides

    @discord.ui.button(label="🎲 Hodit s kostkami", style=discord.ButtonStyle.success,
                       custom_id="lab2_dice_roll")
    async def roll_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.holder.id:
            await interaction.response.send_message(
                "*Kostky drží někdo jiný!*", ephemeral=True
            )
            return

        rolls = [random.randint(1, self.sides) for _ in self.room_view.players]

        result_lines = "\n".join(
            f"🎲 {p.display_name}: **{r}**"
            for p, r in zip(self.room_view.players, rolls)
        )

        embed = discord.Embed(
            title="🎲 Výsledek hodu",
            description=(
                f"**{interaction.user.display_name}** hodil kostkami!\n\n"
                f"{result_lines}\n\n"
                "*Magický mechanismus podstavce rozděluje kapacitu do dveří...*"
            ),
            color=0x00FF00,
        )

        # Deaktivuj obě tlačítka
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=embed)

        # Aplikuj hod na dveře
        self.room_view.apply_roll_and_show_doors(rolls)
        room_embed = self.room_view._create_embed()
        room_embed.add_field(
            name="Dveře se otevřely",
            value="Cesta dál je volná. Jakým směrem se vydáte?",
            inline=False,
        )
        # Pošli novou zprávu s embédem přímo do vlákna — hráč nemusí scrollovat
        new_msg = await self.room_view.send_target.send(embed=room_embed, view=self.room_view)
        self.room_view.message = new_msg  # aktualizuj referenci pro budoucí edity

    @discord.ui.button(label="↩️ Položit zpět", style=discord.ButtonStyle.secondary,
                       custom_id="lab2_dice_return")
    async def return_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.holder.id:
            await interaction.response.send_message(
                "*Kostky drží někdo jiný!*", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="↩️ Kostky vráceny",
            description=(
                f"**{interaction.user.display_name}** položil kostky zpět na podstavec.\n\n"
                "*Někdo jiný si je může vzít.*"
            ),
            color=0x2B2D31,
        )

        # Deaktivuj obě tlačítka
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=embed)

        # Obnov původní RoomView (nová instance = čisté tlačítko "Vzít kostky")
        if self.room_view.message:
            fresh_view = RoomView(
                players=self.room_view.players,
                room_name=self.room_view.room_name,
                map_rows=self.room_view.map_rows,
                map_cols=self.room_view.map_cols,
                game_id=self.room_view.game_id,
                came_from=self.room_view.came_from,
                parent_channel=self.room_view.parent_channel,
                thread=self.room_view.thread,
            )
            fresh_view.message = self.room_view.message
            await self.room_view.message.edit(
                embed=fresh_view._create_embed(), view=fresh_view
            )