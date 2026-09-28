"""Small, non-blocking notifications for newly unlocked DespairGen achievements."""

from collections import deque

import pygame
import pygame_gui

from scripts.game_structure.screen_settings import MANAGER
from scripts.ui.scale import ui_scale, ui_scale_value

_queue = deque()
_active = None


class AchievementNotification:
    """A small auto-dismissing achievement toast."""

    DISPLAY_SECONDS = 2.2
    FADE_DURATION = 0.5

    def __init__(self):
        self.remaining = self.DISPLAY_SECONDS
        width, height = 330, 82
        rect = ui_scale(pygame.Rect((0, 0), (width, height)))
        # Place the toast in the bottom-right, just above the version watermark.
        # The source-build watermark occupies the bottom edge of the 800x700 viewport,
        # so keeping the toast 10px above that area leaves the version visible.
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

        # Fade the notification text quickly at the end of its short display time.
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


def queue_achievement_notification():
    """Queue one generic toast for a newly unlocked achievement."""
    _queue.append(True)


def update_achievement_notifications(time_delta):
    """Advance the toast queue; call once per main-loop frame."""
    global _active

    if _active is not None and not _active.update(time_delta):
        _active = None

    if _active is None and _queue:
        _queue.popleft()
        _active = AchievementNotification()
