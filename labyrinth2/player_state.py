"""
player_state.py
Centrální herní stav – sdílí se napříč všemi moduly.
"""

from dataclasses import dataclass, field
from typing import Optional
import discord

@dataclass
class PlayerState:
    member: discord.Member
    inventory: list[str] = field(default_factory=list)   # list item_id
    equipped: Optional[str] = None                        # item_id nebo None
    is_murderer: bool = False
    alive: bool = True

# game_id -> { user_id -> PlayerState }
game_states: dict[str, dict[int, PlayerState]] = {}

def get_state(game_id: str, member: discord.Member) -> PlayerState:
    if game_id not in game_states:
        game_states[game_id] = {}
    if member.id not in game_states[game_id]:
        game_states[game_id][member.id] = PlayerState(member=member)
    return game_states[game_id][member.id]

def init_game(game_id: str, players: list[discord.Member]):
    """Inicializuje hru – přiřadí náhodně vraha a dá mu zbraň."""
    from .items import ITEMS, WEAPONS

    game_states[game_id] = {p.id: PlayerState(member=p) for p in players}

    murderer = players[__import__("random").randint(0, len(players) - 1)]
    state = game_states[game_id][murderer.id]
    state.is_murderer = True

    # Vrahovi automaticky dáme náhodnou zbraň
    weapon_ids = [iid for iid, item in ITEMS.items() if "zbraň" in item["tags"]]
    if weapon_ids:
        chosen = __import__("random").choice(weapon_ids)
        state.inventory.append(chosen)
        state.equipped = chosen