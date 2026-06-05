"""Datová vrstva — skóre Door Labyrinth."""

import json
import os
import threading
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SCORES_FILE = os.path.join(DATA_DIR, "labyrinth_scores.json")

_lock = threading.Lock()

def load_json(path: str, default: Any = None) -> Any:
    """Bezpečně načte JSON soubor."""
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default if default is not None else {}

def save_json(path: str, data: Any) -> None:
    """Bezpečně uloží data do JSON souboru."""
    with _lock:
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def load_scores() -> dict:
    return load_json(SCORES_FILE) or {}

def save_scores(data: dict) -> None:
    save_json(SCORES_FILE, data)

def record_win(uid: str) -> None:
    scores = load_scores()
    scores[uid] = scores.get(uid, 0) + 1
    save_scores(scores)
