"""Persistent, client-side DespairGen achievements."""

from pathlib import Path
from collections import deque
import ujson

from scripts.housekeeping.datadir import get_data_dir
from scripts.game_structure.game.save_load import safe_save

ACHIEVEMENT_FILE = "despairgen_achievements.json"

# UI test build only: expose every currently implemented DespairGen achievement.
# This flag is intentionally confined to this test build and must be disabled for release builds.
TEST_UNLOCK_ALL_ACHIEVEMENTS = False
TEST_ACHIEVEMENT_IDS = [f"DG{i:03d}" for i in range(1, 14)]


def _path():
    return Path(get_data_dir()) / ACHIEVEMENT_FILE


def load_unlocked():
    path = _path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = ujson.load(f)
        unlocked = data.get("unlocked", []) if isinstance(data, dict) else data
        unlocked = list(dict.fromkeys(str(x) for x in unlocked))
        if TEST_UNLOCK_ALL_ACHIEVEMENTS:
            return list(dict.fromkeys(unlocked + TEST_ACHIEVEMENT_IDS))
        return unlocked
    except (OSError, ValueError, TypeError):
        return []


def unlock(achievement_id):
    """Persist an achievement independently of the current Clan save."""
    unlocked = load_unlocked()
    achievement_id = str(achievement_id)
    if achievement_id in unlocked:
        return False
    unlocked.append(achievement_id)
    safe_save(_path(), {"unlocked": unlocked}, check_integrity=True)
    try:
        queue_achievement_notification()
    except (ImportError, RuntimeError):
        # Achievement persistence must never fail just because the UI is unavailable.
        pass
    return True


def is_unlocked(achievement_id):
    return str(achievement_id) in load_unlocked()


def check_true_self_achievement(cat):
    """Unlock Be Your True Self! when the player manually makes their MC trans."""
    if cat is None:
        return
    try:
        from scripts.game_structure import game
        player_cat = getattr(getattr(game, "clan", None), "your_cat", None)
        if player_cat is None or getattr(cat, "ID", None) != getattr(player_cat, "ID", None):
            return
        if getattr(cat, "genderalign", None) in ("trans male", "trans female"):
            unlock("DG014")
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return


def check_clan_faith_achievements():
    """Unlock hidden faith achievements the instant a clan reaches 100% alignment."""
    try:
        from scripts.game_structure import game
        clan = getattr(game, "clan", None)
        if clan is None:
            return
        faith = clan.get_clan_faith()
        if faith.get("starclan") == 100:
            unlock("DG010")
        if faith.get("dark_forest") == 100:
            unlock("DG009")
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return


def check_incest_achievement(cat_from, cat_to):
    """Unlock the hidden achievement when a normally prohibited blood relation is made mates.

    This intentionally checks the relationship at the moment the mate bond is created,
    rather than trying to detect source-code edits directly. If the normal relationship
    rules have been bypassed or modified and a relationship the game would ordinarily
    prohibit is actually formed, the achievement is awarded.
    """
    if cat_from is None or cat_to is None:
        return
    try:
        from scripts.clan_package.settings import get_clan_setting
        if cat_from.is_related(
            cat_to, get_clan_setting("first cousin mates")
        ) or cat_to.is_related(
            cat_from, get_clan_setting("first cousin mates")
        ):
            unlock("DG013")
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return


def check_murder_achievements(victim, murderer=None):
    """Unlock hidden murder achievements only when the player actually made the kill."""
    if victim is None or murderer is None:
        return
    try:
        from scripts.game_structure import game

        player_cat = getattr(getattr(game, "clan", None), "your_cat", None)
        if player_cat is None or getattr(murderer, "ID", None) != getattr(player_cat, "ID", None):
            return

        from scripts.cat.enums import CatRank
        if victim.age.is_baby() or victim.status.rank in (CatRank.NEWBORN, CatRank.KITTEN):
            unlock("DG011")
        elif victim.status.rank == CatRank.ELDER:
            unlock("DG012")
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return


# Achievement notification UI is kept in this core achievement module so the release
# does not depend on importing a separate notification submodule at runtime.
_notification_queue = deque()
_active_notification = None


def queue_achievement_notification():
    """Queue one generic toast for a newly unlocked achievement."""
    _notification_queue.append(True)


class _AchievementNotification:
    DISPLAY_SECONDS = 2.2
    FADE_DURATION = 0.5

    def __init__(self):
        import pygame
        import pygame_gui
        from scripts.game_structure.screen_settings import MANAGER
        from scripts.ui.scale import ui_scale, ui_scale_value

        self.remaining = self.DISPLAY_SECONDS
        width, height = 330, 82
        rect = ui_scale(pygame.Rect((0, 0), (width, height)))
        rect.bottomright = (ui_scale_value(782), ui_scale_value(650))

        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            manager=MANAGER,
            object_id="#despairgen_achievement_notification",
        )
        self.title = pygame_gui.elements.UITextBox(
            "<b>Achievement Unlocked!</b>",
            ui_scale(pygame.Rect((12, 9), (306, 27))),
            manager=MANAGER,
            container=self.panel,
            object_id="#despairgen_achievement_notification_title",
        )
        self.text = pygame_gui.elements.UITextBox(
            "You've unlocked a DespairGen Achievement!<br><font color='#B5A17B'>Check the Achievement tab for details.</font>",
            ui_scale(pygame.Rect((12, 35), (306, 39))),
            manager=MANAGER,
            container=self.panel,
            object_id="#despairgen_achievement_notification_text",
        )

    def update(self, time_delta):
        self.remaining -= time_delta
        if self.remaining <= self.FADE_DURATION:
            alpha = max(0, min(255, int(255 * self.remaining / self.FADE_DURATION)))
            self.title.set_text_alpha(alpha)
            self.text.set_text_alpha(alpha)
        if self.remaining <= 0:
            self.kill()
            return False
        return True

    def kill(self):
        if self.panel is not None:
            self.panel.kill()
            self.panel = None


def update_achievement_notifications(time_delta):
    """Advance the toast queue; call once per main-loop frame."""
    global _active_notification
    if _active_notification is not None and not _active_notification.update(time_delta):
        _active_notification = None
    if _active_notification is None and _notification_queue:
        _notification_queue.popleft()
        _active_notification = _AchievementNotification()
