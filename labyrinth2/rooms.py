import random

ROOMS = {
    "labyrinth_hub": {
        "id": "labyrinth_hub",
        "name": "Labyrinth Hub",
        "description": "Magické dveře, nad kterými visí runová tabule. Moderní osvětlené prostředí. Uprostřed místnosti stojí podestál.",
    },
    "start_room": {
        "id": "start_room",
        "name": "Vstupní komnata",
        "description": "Rohová místnost s kamennou podlahou a pochodněmi na stěnách. V rohu stojí masivní okovaná truhla — vypadá, jako by tu čekala na někoho.",
        "spawn_weight": 0,   # přiřazuje se explicitně na rohové souřadnice
    },
    "dark_corridor": {
        "id": "dark_corridor",
        "name": "Zatemnělá chodba",
        "description": "Temná místnost, kde není vidět na krok. Cítíš chladný průvan ze stěn. Někde blízko kape voda.",
        "spawn_weight": 50,
    },
    "abandoned_shrine": {
        "id": "abandoned_shrine",
        "name": "Opuštěná svatyně",
        "description": "Stěny jsou lemovány starými rozbitými sochami. Zem je pokryta prachem a rozbitým sklem.",
        "spawn_weight": 50,
    },
    "plant_room": {
        "id": "plant_room",
        "name": "Stromová komnata",
        "description": "Místnost je stejná jako ta na začátku, ale středem prostupuje mohutný strom. Jeho kořeny trhají kamennou dlažbu a větve sahají ke stropu. Do kmene byl ručně vytesán otvor — uvnitř spočívá kamenný podstavec s kostkami.",
        "spawn_weight": 50,
        "loot_table": ["wood"],
    },
    "exit_room": {
        "id": "exit_room",
        "name": "Strojovna úniku",
        "description": "Uprostřed místnosti stojí starý rezavý generátor obrostlý kabely. Vedle něj se tyčí masivní kovové dveře s elektrickým zámkem. Na generátoru svítí červená kontrolka — palivová nádrž je prázdná.",
        "spawn_weight": 0,    # nespawnuje náhodně — přiřazuje se explicitně jako unique
        "unique": True,       # v celé mapě může být nejvýše jedna
    },
}

# Váhy spawnu místností (výchozí = 50 pokud není uvedeno)
def _room_weight(room_id: str) -> int:
    return ROOMS[room_id].get("spawn_weight", 50)

def get_room_data(room_id: str) -> dict:
    return ROOMS.get(room_id, ROOMS["start_room"])

def get_random_room_id(exclude_hub: bool = True) -> str:
    """Vrátí náhodné room_id — vylučuje hub, start_room a unique místnosti."""
    pool = [
        r for r in ROOMS.keys()
        if r not in ("labyrinth_hub", "start_room")
        and not ROOMS[r].get("unique", False)
        and _room_weight(r) > 0
    ]
    if not pool:
        return "start_room"
    weights = [_room_weight(r) for r in pool]
    return random.choices(pool, weights=weights, k=1)[0]

def get_unique_room_ids() -> list[str]:
    """Vrátí seznam všech unique místností které se musí přiřadit explicitně."""
    return [rid for rid, r in ROOMS.items() if r.get("unique", False)]