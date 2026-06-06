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
    }
}

def get_room_data(room_id: str) -> dict:
    return ROOMS.get(room_id, ROOMS["labyrinth_hub"])

def get_random_room_id(exclude_hub: bool = True) -> str:
    choices = [r for r in ROOMS.keys() if not (exclude_hub and r == "labyrinth_hub")]
    if not choices:
        return "labyrinth_hub"
    return random.choice(choices)
