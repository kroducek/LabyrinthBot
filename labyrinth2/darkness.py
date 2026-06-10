"""
darkness.py
Mechanika tmy — místnosti bez osvětlení omezují průzkum.

Tmavé místnosti:
- Hráči vidí jen podstavec s kostkami, popis je nahrazen tmou
- Průzkum vrátí "Je tu moc tma..." místo náhodného lootu
- Akce pro rozsvícení jsou dostupné po průzkumu

Rozsvícení se ukládá do room_state["lit"] = 1 (sdílený stav místnosti).
"""

# Množina room_id které začínají ve tmě
DARK_ROOMS: set[str] = {"dark_corridor"}


def is_dark(room_id: str, room_state: dict) -> bool:
    """Vrátí True pokud je místnost aktuálně tmavá (dosud nerozsvícená)."""
    return room_id in DARK_ROOMS and not room_state.get("lit", False)