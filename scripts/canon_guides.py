"""Rare canon guiding-ghost support for DespairGen v0.6.1.1."""
import json
import random

CHANCE = 0.005
RESOURCE_PATH = "resources/dicts/guides/canon_guides.json"


def load_canon_guides(resource_path=RESOURCE_PATH):
    with open(resource_path, encoding="utf8") as f:
        data = json.load(f)
    return (
        float(data.get("chance", CHANCE)),
        data.get("starclan", []),
        data.get("dark_forest", []),
    )


_TEST_CYCLE_INDEX = {"starclan": 0, "dark_forest": 0}

def rare_canon_guide(domain, resource_path=RESOURCE_PATH):
    """Return a canon guide using the normal rare-roll chance."""
    chance, starclan, dark_forest = load_canon_guides(resource_path)
    pool = starclan if domain == "starclan" else dark_forest

    if random.random() >= chance or not pool:
        return None

    selected = random.choice(pool)

    from scripts.despairgen_achievements import unlock
    if domain == "starclan":
        unlock("DG001")
    elif domain == "dark_forest":
        unlock("DG002")
    achievement_id = selected.get("achievement_id")
    if achievement_id:
        unlock(achievement_id)
    return selected
