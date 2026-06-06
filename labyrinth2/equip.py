"""
equip.py
Mechanika equipování předmětů z inventáře.
"""

import discord
from .player_state import get_state
from .items import ITEMS


class InventoryView(discord.ui.View):
    """Ephemeral view – zobrazí inventář a umožní equipnout předmět."""

    def __init__(self, game_id: str, member: discord.Member):
        super().__init__(timeout=60)
        self.game_id = game_id
        self.member = member
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        state = get_state(self.game_id, self.member)

        if not state.inventory:
            return  # prázdný inventář – žádná tlačítka

        # Deduplikace: unikátní předměty
        seen = set()
        for item_id in state.inventory:
            if item_id in seen:
                continue
            seen.add(item_id)
            item = ITEMS[item_id]
            is_equipped = (state.equipped == item_id)
            label = f"{'✅ ' if is_equipped else ''}{item['emoji']} {item['name']}"
            btn = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.success if is_equipped else discord.ButtonStyle.secondary,
                custom_id=f"lab2_equip_{item_id}",
            )
            btn.callback = self._make_equip_callback(item_id)
            self.add_item(btn)

    def _make_equip_callback(self, item_id: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.member.id:
                await interaction.response.send_message("*Tohle není tvůj inventář.*", ephemeral=True)
                return

            state = get_state(self.game_id, self.member)

            if state.equipped == item_id:
                # Odequipnout
                state.equipped = None
                action = f"*{ITEMS[item_id]['name']}* jsi odložil."
            else:
                state.equipped = item_id
                action = f"*{ITEMS[item_id]['name']}* jsi vzal do ruky."

            self._build_buttons()
            embed = inventory_embed(self.game_id, self.member, note=action)
            await interaction.response.edit_message(embed=embed, view=self)

        return callback


def inventory_embed(game_id: str, member: discord.Member, note: str = "") -> discord.Embed:
    state = get_state(game_id, member)

    if not state.inventory:
        desc = "*Tvůj inventář je prázdný.*"
    else:
        lines = []
        counts: dict[str, int] = {}
        for iid in state.inventory:
            counts[iid] = counts.get(iid, 0) + 1

        for iid, cnt in counts.items():
            item = ITEMS[iid]
            equipped_mark = " ✅ **[EQUIPNUTO]**" if state.equipped == iid else ""
            count_str = f" ×{cnt}" if cnt > 1 else ""
            tags = ", ".join(item["tags"])
            lines.append(
                f"{item['emoji']} **{item['name']}**{count_str}{equipped_mark}\n"
                f"  *{item['description']}*\n"
                f"  `{tags}`"
            )
        desc = "\n\n".join(lines)

    if note:
        desc += f"\n\n> {note}"

    embed = discord.Embed(
        title=f"🎒 Inventář — {member.display_name}",
        description=desc,
        color=0x2B2D31,
    )
    embed.set_footer(text="Klikni na předmět pro equipnutí / odložení.")
    return embed