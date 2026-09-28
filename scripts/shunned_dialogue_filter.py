"""Hard gate for shunned dialogue.

Shunned-only dialogue must never enter the normal dialogue candidate pool.
This module provides small, dependency-free helpers for selectors.
"""

def is_shunned_dialogue(entry):
    """Return True when a dialogue entry explicitly targets shunned cats."""
    if not isinstance(entry, dict):
        return False
    fields = (
        entry.get("group"),
        entry.get("groups"),
        entry.get("tags"),
        entry.get("standing"),
        entry.get("condition"),
        entry.get("conditions"),
        entry.get("id"),
    )
    text = repr(fields).lower()
    return "shunned" in text


def allow_for_mc(entry, mc_is_shunned):
    """Hard-gate shunned dialogue before ordinary filters run."""
    targeted = is_shunned_dialogue(entry)
    if targeted:
        return bool(mc_is_shunned)
    return not bool(mc_is_shunned)
