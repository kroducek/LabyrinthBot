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
        "room_exclusive": ["plant_room"],   # spawnuje se jen v těchto místnostech
    },
}

WEAPONS = {iid: item for iid, item in ITEMS.items() if "zbraň" in item["tags"]}

# Váhy pro rarity
RARITY_WEIGHT = {"common": 60, "uncommon": 30, "rare": 10}


def random_item_id(room_name: str = None) -> str:
    ids = [
        iid for iid, item in ITEMS.items()
        if "room_exclusive" not in item
        or (room_name is not None and room_name in item["room_exclusive"])
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

class SearchView(discord.ui.View):
    """Ephemeral view – hráč hledá předměty v místnosti."""

    def __init__(self, game_id: str, member: discord.Member, room_name: str):
        super().__init__(timeout=60)
        self.game_id = game_id
        self.member = member
        self.room_name = room_name
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

        await interaction.response.edit_message(embed=embed, view=self)