"""
items.py
Definice předmětů a hledací mechanika.
"""

import discord
import random
from .player_state import get_state

# ── Definice předmětů ────────────────────────────────────────────────────────

ITEMS: dict[str, dict] = {
    "lantern": {
        "id": "lantern",
        "name": "Lucerna",
        "emoji": "🪔",
        "description": "Stará olejová lucerna. Osvětluje i ta nejtemnější zákoutí.",
        "tags": ["světlo"],
        "rarity": "common",
    },
    "knife": {
        "id": "knife",
        "name": "Nůž",
        "emoji": "🔪",
        "description": "Ostrý kapesní nůž. Může posloužit jako zbraň i nástroj.",
        "tags": ["zbraň", "nástroj"],
        "rarity": "common",
    },
    "gold_coin": {
        "id": "gold_coin",
        "name": "Zlatá mince",
        "emoji": "🪙",
        "description": "Lesklá zlatá mince s neznámým erbem. Možná má nějakou hodnotu.",
        "tags": ["cennost"],
        "rarity": "rare",
    },
    "lighter": {
        "id": "lighter",
        "name": "Zapalovač",
        "emoji": "🔥",
        "description": "Opotřebovaný zapalovač. Stále funkční – světlo i nástroj v jednom.",
        "tags": ["světlo", "nástroj"],
        "rarity": "common",
    },
    "axe": {
        "id": "axe",
        "name": "Sekera",
        "emoji": "🪓",
        "description": "Těžká dřevorubecká sekera. Smrtící zbraň, ale i praktický nástroj.",
        "tags": ["zbraň", "nástroj"],
        "rarity": "uncommon",
    },
    "wood": {
        "id": "wood",
        "name": "Dřevo",
        "emoji": "🪵",
        "description": "Kus dřeva odlomený ze starého stromu. Surový materiál – k čemu se hodí, to záleží na tobě.",
        "tags": ["materiál"],
        "rarity": "common",
        "room_exclusive": ["plant_room"],
    },
    "canister": {
        "id": "canister",
        "name": "Kanystr benzínu",
        "emoji": "🛢️",
        "description": "Těžký kanystr plný benzínu. Cítíš ostrý zápach paliva. Někde se to bude hodit.",
        "tags": ["materiál", "palivo"],
        "rarity": "uncommon",
        "guaranteed": True,   # nespawnuje se náhodně, jen garantovaně na určených místech
    },
}

WEAPONS = {iid: item for iid, item in ITEMS.items() if "zbraň" in item["tags"]}

# Váhy pro rarity
RARITY_WEIGHT = {"common": 60, "uncommon": 30, "rare": 10}


def random_item_id(room_name: str = None) -> str:
    ids = [
        iid for iid, item in ITEMS.items()
        if not item.get("guaranteed", False)                          # nikdy náhodně
        and (
            "room_exclusive" not in item
            or (room_name is not None and room_name in item["room_exclusive"])
        )
    ]
    weights = [RARITY_WEIGHT[ITEMS[i]["rarity"]] for i in ids]
    return random.choices(ids, weights=weights, k=1)[0]


def item_embed(item_id: str) -> discord.Embed:
    item = ITEMS[item_id]
    tags_str = ", ".join(item["tags"])
    embed = discord.Embed(
        title=f"{item['emoji']} {item['name']}",
        description=item["description"],
        color=0x8B6914 if item["rarity"] == "rare" else 0x2B2D31,
    )
    embed.add_field(name="Vlastnosti", value=tags_str, inline=True)
    embed.add_field(name="Vzácnost", value=item["rarity"].capitalize(), inline=True)
    return embed


# ── View pro průzkum místnosti ────────────────────────────────────────────────

# ── Room-specific akce ────────────────────────────────────────────────────────
ROOM_ACTIONS: dict[str, list[dict]] = {
    "start_room": [
        {
            "id": "admin_chest",
            "label": "📦 Otevřít truhlu",
            "one_time": True,
            "progress_key": "chest_opened",
            "progress_max": 1,
            "reward_item": "canister",
            "reward_count": 3,
            "reward_text": "Otevřeš těžké okované víko. Uvnitř leží tři kanystry s benzínem.\n\n🛢️ Získal jsi **3× Kanystr benzínu**!",
        },
    ],
    "plant_room": [
        {
            "id": "chop_wood",
            "label": "🪓 Nasekat dřevo",
            "requires_equipped_tag": "nástroj",
            "requires_equipped_hint": "Vyžaduje sekeru nebo jiný nástroj",
            "reward_item": "wood",
            "reward_count": 3,
            "reward_text": "Zasadíš ránu do kmene stromu. Třísky létají na všechny strany...\n\n🪵 Získal jsi **3× Dřevo**!",
        },
    ],
    "exit_room": [
        {
            "id": "refuel_generator",
            "label": "🛢️ Doplnit palivo do generátoru",
            "requires_item": "canister",
            "requires_item_count": 1,
            "consume_item": True,
            "reward_item": None,
            "reward_count": 0,
            "reward_text": "Přeliješ kanystr do generátoru. Hladina paliva stoupá...",
            "progress_key": "generator_fuel",   # klíč v room_state pro sledování progressu
            "progress_max": 3,
        },
        {
            "id": "open_exit",
            "label": "🚪 Spustit generátor a otevřít dveře",
            "requires_progress_key": "generator_fuel",
            "requires_progress_value": 3,
            "reward_item": None,
            "reward_count": 0,
            "reward_text": "Generátor zahřmí a zábleskne. Těžké kovové dveře se pomalu otevírají...\n\n**Svoboda je na dosah.**",
            "triggers_escape": True,
        },
    ],
}


class SearchView(discord.ui.View):
    """Ephemeral view – hráč hledá předměty v místnosti."""

    def __init__(self, game_id: str, member: discord.Member, room_name: str, room_id: str = None, room_state: dict = None):
        super().__init__(timeout=60)
        self.game_id = game_id
        self.member = member
        self.room_name = room_name
        self.room_id = room_id or room_name
        self.room_state = room_state or {}   # sdílený stav místnosti (fuel atd.)
        self.searched = False

    @discord.ui.button(label="🔍 Prohledat místnost", style=discord.ButtonStyle.primary, custom_id="lab2_search_room")
    async def search_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("*Tohle není tvoje akce.*", ephemeral=True)
            return

        if self.searched:
            await interaction.response.send_message("*Místnost jsi už prohledal.*", ephemeral=True)
            return

        self.searched = True
        button.disabled = True

        # 60 % šance na nález
        if random.random() < 0.60:
            found_id = random_item_id(room_name=self.room_name)
            item = ITEMS[found_id]
            state = get_state(self.game_id, self.member)
            state.inventory.append(found_id)

            embed = discord.Embed(
                title="✨ Našel jsi něco!",
                description=f"V koutech místnosti **{self.room_name}** jsi objevil:\n\n"
                            f"{item['emoji']} **{item['name']}** — *{item['description']}*\n\n"
                            f"Předmět byl přidán do tvého inventáře.",
                color=0x4CAF50,
            )
        else:
            embed = discord.Embed(
                title="🌑 Nic jsi nenašel",
                description=f"*Místnost {self.room_name} ti nevydala žádné tajemství... tentokrát.*",
                color=0x555555,
            )

        self._add_room_action_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    def _add_room_action_buttons(self):
        """Přidá tlačítka room-specific akcí pokud hráč splňuje podmínky."""
        actions = ROOM_ACTIONS.get(self.room_id, [])
        if not actions:
            return
        state = get_state(self.game_id, self.member)

        for action in actions:
            enabled = True
            hidden = False
            hint = ""

            # One-time akce: skryj pokud už byla použita (progress_key dosáhl max)
            if action.get("one_time"):
                prog_key = action.get("progress_key")
                if prog_key and self.room_state.get(prog_key, 0) >= action.get("progress_max", 1):
                    hidden = True

            if hidden:
                continue  # truhla už byla otevřena — vůbec nezobrazuj

            # Podmínka: requires_progress_value_max — akce se zobrazí jen dokud progress < max
            req_max = action.get("requires_progress_value_max")
            if req_max is not None:
                prog_key = action.get("progress_key", "")
                if self.room_state.get(prog_key, 0) > req_max:
                    continue  # přeskočit

            # Podmínka: equipnutý tag
            req_tag = action.get("requires_equipped_tag")
            if req_tag:
                eq = state.equipped
                if not eq or req_tag not in ITEMS.get(eq, {}).get("tags", []):
                    enabled = False
                    hint = action.get("requires_equipped_hint", f"Vyžaduje: {req_tag}")

            # Podmínka: item v inventáři
            req_item = action.get("requires_item")
            req_count = action.get("requires_item_count", 1)
            if req_item:
                has = state.inventory.count(req_item)
                if has < req_count:
                    enabled = False
                    hint = f"Potřebuješ {req_count}× {ITEMS[req_item]['emoji']} {ITEMS[req_item]['name']} (máš {has})"

            # Podmínka: room_state progress musí dosáhnout hodnoty
            req_prog_key = action.get("requires_progress_key")
            req_prog_val = action.get("requires_progress_value", 0)
            if req_prog_key and req_prog_val > 0:
                current = self.room_state.get(req_prog_key, 0)
                if current < req_prog_val:
                    enabled = False
                    hint = f"Generátor potřebuje palivo ({current}/{req_prog_val})"

            label = action["label"] if enabled else f"🔒 {action['label'].lstrip('🛢️🚪🪓📦').strip()} — {hint}"
            btn = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.success if enabled else discord.ButtonStyle.secondary,
                custom_id=f"lab2_room_action_{action['id']}",
                disabled=not enabled,
            )
            btn.callback = self._make_action_callback(action)
            self.add_item(btn)

    def _make_action_callback(self, action: dict):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.member.id:
                await interaction.response.send_message("*Tohle není tvoje akce.*", ephemeral=True)
                return

            state = get_state(self.game_id, self.member)

            # Spotřebuj item pokud je nastaveno
            if action.get("consume_item") and action.get("requires_item"):
                item_id = action["requires_item"]
                if item_id in state.inventory:
                    state.inventory.remove(item_id)

            # Přidej reward pokud existuje
            reward_id = action.get("reward_item")
            if reward_id:
                for _ in range(action.get("reward_count", 1)):
                    state.inventory.append(reward_id)

            # Aktualizuj room_state progress
            prog_key = action.get("progress_key")
            prog_max = action.get("progress_max", 0)
            if prog_key:
                self.room_state[prog_key] = min(
                    self.room_state.get(prog_key, 0) + 1, prog_max
                )
                current = self.room_state[prog_key]
                reward_text = action["reward_text"] + f"\n\n⛽ Generátor: **{current}/{prog_max}**"
            else:
                reward_text = action["reward_text"]

            item_data = ITEMS.get(reward_id) if reward_id else None
            embed = discord.Embed(
                title=action["label"],
                description=reward_text,
                color=0x4CAF50,
            )

            # Úspěšný útěk
            if action.get("triggers_escape"):
                embed = discord.Embed(
                    title="🚨 ÚTĚK!",
                    description=(
                        f"**{interaction.user.display_name}** nastartoval generátor!\n\n"
                        f"{reward_text}\n\n"
                        f"*{interaction.user.display_name} úspěšně utekl z labyrintu!*"
                    ),
                    color=0xFFD700,
                )
                for btn in self.children:
                    btn.disabled = True
                await interaction.response.edit_message(embed=embed, view=self)
                # Broadcast do vlákna
                from .basic_menu import _escape_broadcast
                await _escape_broadcast(interaction, self.game_id, interaction.user)
                return

            # Deaktivuj toto tlačítko po použití
            for btn in self.children:
                if getattr(btn, "custom_id", "") == f"lab2_room_action_{action['id']}":
                    btn.disabled = True
                    break

            await interaction.response.edit_message(embed=embed, view=self)
        return callback