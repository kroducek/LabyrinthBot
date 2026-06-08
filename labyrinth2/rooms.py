import random

ROOMS = {
    "labyrinth_hub": {
        "id": "labyrinth_hub",
        "name": "Labyrinth Hub",
        "description": "Magické dveře, nad kterými visí runová tabule. Moderní osvětlené prostředí. Uprostřed místnosti stojí podestál.",
    },
    "dark_corridor": {
        "id": "dark_corridor",
        "name": "Zatemnělá chodba",
        "description": "Temná místnost, kde není vidět na krok. Cítíš chladný průvan ze stěn. Někde blízko kape voda.",
    },
    "abandoned_shrine": {
        "id": "abandoned_shrine",
        "name": "Opuštěná svatyně",
        "description": "Stěny jsou lemovány starými rozbitými sochami. Zem je pokryta prachem a rozbitým sklem.",
        "spawn_weight": 10,
    },
    "plant_room": {
        "id": "plant_room",
        "name": "Stromová komnata",
        "description": "Místnost je stejná jako ta na začátku, ale středem prostupuje mohutný strom. Jeho kořeny trhají kamennou dlažbu a větve sahají ke stropu. Do kmene byl ručně vytesán otvor — uvnitř spočívá kamenný podstavec s kostkami.",
        "spawn_weight": 90,
        "loot_table": ["wood"],   # předměty navíc k výchozímu lootu
    },
}

# Váhy spawnu místností (výchozí = 10 pokud není uvedeno)
def _room_weight(room_id: str) -> int:
    return ROOMS[room_id].get("spawn_weight", 10)

def get_room_data(room_id: str) -> dict:
    return ROOMS.get(room_id, ROOMS["labyrinth_hub"])

def get_random_room_id(exclude_hub: bool = True) -> str:
    pool = [r for r in ROOMS.keys() if not (exclude_hub and r == "labyrinth_hub")]
    if not pool:
        return "labyrinth_hub"
    weights = [_room_weight(r) for r in pool]
    return random.choices(pool, weights=weights, k=1)[0]