"""
thread_manager.py
Správa vláken pro jednotlivé skupiny hráčů pohybující se labyrintem.

Logika:
- Každá skupina hráčů ve stejné místnosti = jedno vlákno
- Název vlákna: "🚪 B3 — Honza, Pavel"
- Při rozdělení skupiny: každá podskupina dostane nové vlákno
- Při opuštění místnosti: vlákno se archivuje "📁 A1→B2 [opuštěno]"
- game_threads: game_id -> { frozenset(user_ids) -> thread }
"""

import discord
from typing import Optional

# game_id -> { frozenset(user_ids) -> discord.Thread }
game_threads: dict[str, dict[frozenset, discord.Thread]] = {}


def _thread_name(room_name: str, players: list[discord.Member]) -> str:
    names = ", ".join(p.display_name for p in players[:3])
    if len(players) > 3:
        names += f" +{len(players) - 3}"
    return f"🚪 {room_name} — {names}"


def _group_key(players: list[discord.Member]) -> frozenset:
    return frozenset(p.id for p in players)


def get_thread(game_id: str, players: list[discord.Member]) -> Optional[discord.Thread]:
    """Vrátí vlákno pro danou skupinu hráčů, pokud existuje."""
    return game_threads.get(game_id, {}).get(_group_key(players))


async def create_thread(
    channel: discord.TextChannel,
    game_id: str,
    players: list[discord.Member],
    room_name: str,
) -> discord.Thread:
    """Vytvoří nové vlákno pro skupinu hráčů v dané místnosti."""
    name = _thread_name(room_name, players)
    thread = await channel.create_thread(
        name=name,
        type=discord.ChannelType.public_thread,
        auto_archive_duration=1440,  # 24h
    )

    if game_id not in game_threads:
        game_threads[game_id] = {}
    game_threads[game_id][_group_key(players)] = thread

    # Tagni hráče ve vlákně
    mentions = " ".join(p.mention for p in players)
    await thread.send(
        f"{mentions}\n*Vstoupili jste do místnosti **{room_name}**. Toto vlákno sleduje váš postup.*"
    )
    return thread


async def move_group_to_room(
    parent_channel: discord.TextChannel,
    game_id: str,
    old_players: list[discord.Member],   # původní skupina (před rozdělením)
    subgroup: list[discord.Member],       # tato podskupina
    from_room: str,
    to_room: str,
    direction_label: str,
) -> discord.Thread:
    """
    Přesune podskupinu hráčů do nové místnosti.
    - Pokud je podskupina celá původní skupina → přejmenuje stávající vlákno
    - Pokud je to část skupiny → vytvoří nové vlákno
    Původní vlákno (pokud se skupina rozdělila) archivuje.
    """
    old_key = _group_key(old_players)
    new_key = _group_key(subgroup)
    threads = game_threads.get(game_id, {})
    old_thread: Optional[discord.Thread] = threads.get(old_key)

    # Celá skupina šla stejným směrem — pouze pošli zprávu, vlákno nepřejmenovávej
    if set(p.id for p in subgroup) == set(p.id for p in old_players):
        if old_thread:
            if game_id not in game_threads:
                game_threads[game_id] = {}
            game_threads[game_id].pop(old_key, None)
            game_threads[game_id][new_key] = old_thread

            mentions = " ".join(p.mention for p in subgroup)
            await old_thread.send(
                f"{mentions}\n"
                f"*Skupina prošla **{direction_label}em** do místnosti **{to_room}**.*"
            )
            return old_thread
        else:
            return await create_thread(parent_channel, game_id, subgroup, to_room)

    # Skupina se rozdělila → nové vlákno pro tuto podskupinu
    new_thread = await create_thread(parent_channel, game_id, subgroup, to_room)

    # Archivuj původní vlákno pokud v něm nikdo nezůstane
    # (zjistíme po zpracování všech podskupin — voláno z game.py)
    return new_thread


async def archive_thread(game_id: str, players: list[discord.Member], room_name: str):
    """Archivuje vlákno skupiny po opuštění místnosti."""
    key = _group_key(players)
    thread = game_threads.get(game_id, {}).get(key)
    if thread:
        try:
            await thread.edit(archived=True, locked=False)
        except discord.HTTPException:
            pass
        game_threads.get(game_id, {}).pop(key, None)


def cleanup_game(game_id: str):
    """Vyčistí všechna vlákna hry ze slovníku (při konci hry)."""
    game_threads.pop(game_id, None)