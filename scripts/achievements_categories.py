"""Achievement category and collection helpers for DespairGen."""

from pathlib import Path
import html
import ujson

from scripts.housekeeping.datadir import get_data_dir


LIFEGEN = "lifegen"
DESPAIRGEN = "despairgen"
CANON_ENCOUNTER = "canon_encounter"

_METADATA_PATH = Path(__file__).resolve().parents[1] / "resources" / "dicts" / "despairgen_achievement_metadata.json"


def _load_metadata():
    try:
        with open(_METADATA_PATH, "r", encoding="utf-8") as f:
            data = ujson.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def metadata_for(achievement_id):
    return _load_metadata().get(str(achievement_id), {})


def category_of(achievement):
    """Return the explicit category, defaulting legacy achievements to Lifegen."""
    if isinstance(achievement, dict):
        return achievement.get("category", achievement.get("source", LIFEGEN))
    return LIFEGEN


def filter_by_category(achievements, category):
    """Return only achievements belonging to the selected category."""
    return [a for a in achievements if category_of(a) == category]


def format_despairgen_title(achievement_id, title):
    """Format special DespairGen achievement titles without affecting descriptions."""
    meta = metadata_for(achievement_id)
    title_color = meta.get("title_color")
    if title_color:
        return f'<font color="{title_color}">{html.escape(str(title))}</font>'

    gradient = meta.get("title_gradient")
    gradients = {
        "fire_to_starclan_blue": (("#D62828", 0.00), ("#F4511E", 0.18), ("#FF8F00", 0.36), ("#FFD54F", 0.50), ("#FFE8A3", 0.64), ("#9DD8FF", 0.78), ("#64B5F6", 0.90), ("#4F6FD8", 1.00)),
        "fire": (("#7A1010", 0.00), ("#D62828", 0.22), ("#F4511E", 0.45), ("#FF8F00", 0.70), ("#FFE66D", 1.00)),
        "green_to_fire": (("#315A3A", 0.00), ("#5F8F50", 0.35), ("#B8783A", 0.68), ("#F36B24", 1.00)),
        "purple_to_red": (("#24102F", 0.00), ("#5B2A86", 0.28), ("#8E2346", 0.62), ("#D62828", 1.00)),
        "black_to_red": (("#101010", 0.00), ("#32113F", 0.35), ("#741A3A", 0.68), ("#D62828", 1.00)),
        "red_to_black_white": (("#D62828", 0.00), ("#FFFFFF", 0.48), ("#4A1111", 0.62), ("#101010", 1.00)),
        "dark_forest_hidden": (("#6E3B8A", 0.00), ("#24102F", 0.38), ("#101010", 0.70), ("#8E2346", 1.00)),
        "starclan_hidden": (("#FFF3B0", 0.00), ("#FFFFFF", 0.38), ("#9DD8FF", 0.70), ("#F4E7A3", 1.00)),
        "sinister_red_black": (("#B71C1C", 0.00), ("#4A1111", 0.35), ("#101010", 0.72), ("#D62828", 1.00)),
        "judgment_gray_red": (("#D9D9D9", 0.00), ("#777777", 0.38), ("#4A1111", 0.72), ("#D62828", 1.00)),
        # Pseudo-outline treatment for sinister hidden achievements: red at the
        # edges of the title with a near-black center. The pygame_gui rich-text
        # renderer does not support true text strokes/borders.
        "black_with_red_edges": (("#D62828", 0.00), ("#101010", 0.18), ("#050505", 0.50), ("#101010", 0.82), ("#D62828", 1.00)),
        "trans_flag": (("#5BCEFA", 0.00), ("#F5A9B8", 0.25), ("#FFFFFF", 0.50), ("#F5A9B8", 0.75), ("#5BCEFA", 1.00)),
    }
    gradient_stops = gradients.get(gradient)
    if not gradient_stops:
        return html.escape(str(title))
    stops = tuple((pos, color) for color, pos in gradient_stops)

    text = str(title)
    if not text:
        return ""
    last = max(len(text) - 1, 1)
    rendered = []
    for index, character in enumerate(text):
        position = index / last
        for stop_index in range(len(stops) - 1):
            left_pos, left_color = stops[stop_index]
            right_pos, right_color = stops[stop_index + 1]
            if position <= right_pos:
                span = (position - left_pos) / (right_pos - left_pos) if right_pos > left_pos else 0
                def rgb(value):
                    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
                left_rgb = rgb(left_color)
                right_rgb = rgb(right_color)
                color = "#" + "".join(
                    f"{round(left_rgb[channel] + (right_rgb[channel] - left_rgb[channel]) * span):02X}"
                    for channel in range(3)
                )
                break
        else:
            color = stops[-1][1]
        safe_character = html.escape(character)
        rendered.append(f'<font color="{color}">{safe_character}</font>')
    return "".join(rendered)


def format_despairgen_description(achievement_id, description):
    """Apply optional DespairGen-specific description styling."""
    meta = metadata_for(achievement_id)
    description_color = meta.get("description_color")
    if description_color:
        return f'<font color="{description_color}">{html.escape(str(description))}</font>'
    return html.escape(str(description))


def despairgen_sort_key(achievement_id):
    """Keep canon collections together and ordered independently of achievement IDs."""
    meta = metadata_for(achievement_id)
    category = meta.get("category", "miscellaneous")
    collection = meta.get("collection", "")
    order = meta.get("collection_order", 0)

    if category == CANON_ENCOUNTER:
        domain_order = {"starclan": 0, "dark_forest": 1}.get(collection, 2)
        return (0, domain_order, int(order), str(achievement_id))
    return (1, 0, 0, str(achievement_id))
