from scripts.clan_package.settings.clan_settings import get_clan_setting
from scripts.cat.enums import CatRank
from scripts.achievements_categories import format_despairgen_title


def get_role_name_color(cat):
    """Return an RGB color for a cat's name based on their role."""

    if not get_clan_setting("colored role names"):
        return None

    role_colors = {
        CatRank.LEADER: (255, 215, 0),                # Gold
        CatRank.DEPUTY: (255, 127, 0),                # Artyclick Orange
        CatRank.MEDICINE_CAT: (166, 251, 178),        #Light Mint Green
        CatRank.WARRIOR: (205, 92, 92),               # Warm red
        CatRank.MEDIATOR: (33, 171, 205),             # Ball Blue
        CatRank.ELDER: (147, 112, 219),               # Purple
        CatRank.QUEEN: (255, 105, 180),               # Hot pink
        CatRank.APPRENTICE: (187, 63, 63),            # Dull red
        CatRank.MEDICINE_APPRENTICE: (143, 254, 9),   # Acid Green
        CatRank.MEDIATOR_APPRENTICE: (145, 214, 232), # Jeans Blue
        CatRank.QUEENS_APPRENTICE: (250, 174, 212),   # Powder Pink
    }

    return role_colors.get(cat.status.rank)


def get_colored_name(cat):
    """Return a cat's display name, including canon-ghost gradients when applicable."""

    name = str(cat.name)

    # Canon guiding ghosts use their achievement metadata for their unique
    # per-character name gradient. This takes priority over role coloring.
    canon_achievement_id = getattr(cat, "canon_achievement_id", None)
    if getattr(cat, "is_canon_guide", False) and canon_achievement_id:
        return format_despairgen_title(canon_achievement_id, name)

    color = get_role_name_color(cat)

    if color:
        hex_color = "#{:02X}{:02X}{:02X}".format(*color)
        return f'<font color="{hex_color}">{name}</font>'

    return name


def get_canon_name_color(cat):
    """Return the leading color of a canon ghost's gradient for plain UILabels."""
    gradients = {
        "DG003": "#D62828",  # Bluestar
        "DG004": "#7A1010",  # Firestar
        "DG005": "#315A3A",  # Spottedleaf
        "DG006": "#24102F",  # Brokenstar
        "DG007": "#101010",  # Tigerstar
        "DG008": "#D62828",  # Scourge
    }
    if not getattr(cat, "is_canon_guide", False):
        return None
    color = gradients.get(getattr(cat, "canon_achievement_id", None))
    if not color:
        return None
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
