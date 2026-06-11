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
        "guaranteed": True,
    },
    "gun": {
        "id": "gun",
        "name": "Pistole",
        "emoji": "🔫",
        "description": "Těžká služební pistole. Nabitá. Doufejme, že ji nebudeš potřebovat.",
        "tags": ["zbraň"],
        "rarity": "rare",
        "guaranteed": True,
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
            "reward_items": [
                {"id": "canister",   "count": 3},
                {"id": "lantern",    "count": 1},
                {"id": "gun",        "count": 1},
            ],
            "reward_text": "Otevřeš těžké okované víko. Uvnitř leží kanystry, baterka a pistole.\n\n🛢️ 3× Kanystr  🪔 Lucerna  🔫 Pistole",
        },
    ],
    "dark_corridor": [
        {
            "id": "use_flashlight",
            "label": "🪔 Rozsvítit lucernu",
            "requires_item": "lantern",
            "one_time": True,
            "progress_key": "lit",
            "progress_max": 1,
            "reward_item": None,
            "reward_count": 0,
            "reward_text": "Baterka ozáří místnost chladným světlem.\n\nV rohu sedí tvor, připomínající děsivého mimozemského savce. Nehýbe se, ale pozoruje. Něco hlídá…",
            "triggers_room_update": True,
        },
        {
            "id": "approach_creature",
            "label": "👁️ Přiblížit se k tvorovi",
            "requires_progress_key": "lit",
            "requires_progress_value": 1,
            "hide_if_key": "creature_dead",
            "hide_if_value": 1,
            "reward_item": None,
            "reward_count": 0,
            "reward_text": "Přiblížíš se opatrně. Tvor otočí hlavu — vydá hluboké, nízkofrekvenční zavrčení. Tvoje srdce přeskočí.",
        },
        {
            "id": "shoot_creature",
            "label": "🔫 Zastřelit tvora",
            "requires_progress_key": "lit",
            "requires_progress_value": 1,
            "requires_item": "gun",
            "hide_if_key": "creature_dead",
            "hide_if_value": 1,
            "one_time": True,
            "progress_key": "creature_dead",
            "progress_max": 1,
            "reward_items": [{"id": "canister", "count": 1}],
            "reward_text": "Výstřel rozburácí tiché chodby. Tvor se skácí. V jeho tlamě byl kanystr s benzínem.\n\n🛢️ Získal jsi **1× Kanystr benzínu**!",
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

    def __init__(self, game_id: str, member: discord.Member, room_name: str,
                 room_id: str = None, room_state: dict = None, room_view=None):
        super().__init__(timeout=60)
        self.game_id = game_id
        self.member = member
        self.room_name = room_name
        self.room_id = room_id or room_name
        self.room_state = room_state if room_state is not None else {}
        self.room_view = room_view   # reference pro update embed po rozsvícení
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

        # Zkontroluj tmu — ve tmě průzkum nefunguje
        from .darkness import is_dark
        if is_dark(self.room_id, self.room_state):
            embed = discord.Embed(
                title="🌑 Je tu moc tma...",
                description="*Nevidíš na krok. Bez světla tu nic nenajdeš.*",
                color=0x111111,
            )
            self._add_room_action_buttons()
            await interaction.response.edit_message(embed=embed, view=self)
            return

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

    def _refresh_action_buttons(self):
        """Odstraní stará action tlačítka a přidá nová podle aktuálního stavu."""
        to_remove = [
            item for item in self.children
            if getattr(item, "custom_id", "").startswith("lab2_room_action_")
        ]
        for item in to_remove:
            self.remove_item(item)
        self._add_room_action_buttons()

    def _add_room_action_buttons(self):
        """Přidá tlačítka room-specific akcí podle aktuálního stavu místnosti."""
        actions = ROOM_ACTIONS.get(self.room_id, [])
        if not actions:
            return
        state = get_state(self.game_id, self.member)

        for action in actions:
            enabled = True
            hint = ""
            prog_key = action.get("progress_key")
            prog_max = action.get("progress_max", 0)
            current_prog = self.room_state.get(prog_key, 0) if prog_key else 0

            # One-time akce: skryj pokud už byla použita
            if action.get("one_time") and prog_key:
                if current_prog >= prog_max:
                    continue

            # Akce která plní progress: skryj když je plný
            if prog_key and prog_max and not action.get("one_time"):
                if current_prog >= prog_max:
                    continue

            # hide_if_key: skryj akci pokud jiný progress dosáhl hodnoty (např. tvor je mrtvý)
            hide_key = action.get("hide_if_key")
            hide_val = action.get("hide_if_value", 1)
            if hide_key and self.room_state.get(hide_key, 0) >= hide_val:
                continue

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
                    hint = f"Potřebuješ {ITEMS[req_item]['emoji']} {ITEMS[req_item]['name']} (nemáš)"

            # Podmínka: jiný progress musí dosáhnout hodnoty
            req_prog_key = action.get("requires_progress_key")
            req_prog_val = action.get("requires_progress_value", 0)
            if req_prog_key and req_prog_val > 0:
                cur = self.room_state.get(req_prog_key, 0)
                if cur < req_prog_val:
                    enabled = False
                    hint = f"Generátor potřebuje palivo ({cur}/{req_prog_val})"

            label = action["label"] if enabled else f"🔒 {action['label'].lstrip('🛢️🚪🪓📦🔦👁️🔫').strip()} — {hint}"
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

            # Přidej odměny — podporuje reward_items (list) i reward_item (string)
            for entry in action.get("reward_items", []):
                for _ in range(entry.get("count", 1)):
                    state.inventory.append(entry["id"])
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
                # Přidej progress info jen pro generátor (ne pro lit/creature_dead)
                if prog_key == "generator_fuel":
                    reward_text = action["reward_text"] + f"\n\n⛽ Generátor: **{current}/{prog_max}**"
                else:
                    reward_text = action["reward_text"]
            else:
                reward_text = action["reward_text"]

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
                from .basic_menu import _escape_broadcast
                await _escape_broadcast(interaction, self.game_id, interaction.user)
                return

            # Refreshni action tlačítka
            self._refresh_action_buttons()
            await interaction.response.edit_message(embed=embed, view=self)

            # Pokud akce rozsvítí místnost, aktualizuj hlavní room embed
            if action.get("triggers_room_update") and self.room_view:
                if self.room_view.message:
                    new_embed = self.room_view._create_embed()
                    await self.room_view.message.edit(embed=new_embed, view=self.room_view)
        return callback