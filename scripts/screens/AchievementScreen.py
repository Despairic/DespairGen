# pylint: disable=line-too-long
"""Achievement display for Lifegen and persistent DespairGen achievements."""

import logging

import pygame
import pygame_gui

from scripts.cat.cats import Cat
from scripts.game_structure import game
from scripts.game_structure.game.settings import game_setting_get
from scripts.game_structure.localization import load_lang_resource
from scripts.game_structure.screen_settings import MANAGER
from scripts.ui.scale import ui_scale
from scripts.ui.theme import get_text_box_theme
from scripts.lifegen_utility import check_achievements
from scripts.despairgen_achievements import load_unlocked
from scripts.achievements_categories import (
    LIFEGEN,
    DESPAIRGEN,
    despairgen_sort_key,
    format_despairgen_title,
    format_despairgen_description,
)
from .Screens import Screens

logger = logging.getLogger(__name__)


class AchievementScreen(Screens):
    """Display either Clan-scoped Lifegen or persistent DespairGen achievements."""

    def screen_switches(self):
        super().screen_switches()
        self.show_menu_buttons()
        self.show_mute_buttons()
        self.update_heading_text(game.clan.your_cat.status.get_group_heading_text())

        self.category = getattr(self, "category", LIFEGEN)
        self._build_screen()

    def _build_screen(self):
        a_txt = load_lang_resource("achievements.json")
        dg_txt = load_lang_resource("despairgen_achievements.json")

        if self.category == LIFEGEN:
            check_achievements(Cat)
            entries = []
            for entry in game.clan.achievements:
                achievement_id = str(entry[0])
                if achievement_id in a_txt:
                    entries.append((achievement_id, a_txt[achievement_id]))
            title = "Lifegen Achievements"
        else:
            entries = [(key, value) for key, value in dg_txt.items()]
            unlocked = set(load_unlocked())
            entries = [(key, value) for key, value in entries if key in unlocked]
            entries.sort(key=lambda item: despairgen_sort_key(item[0]))
            title = "DespairGen Achievements"

        self.heading = pygame_gui.elements.UITextBox(
            f"<u>{title}</u>",
            ui_scale(pygame.Rect((0, 140), (600, 500))),
            manager=MANAGER,
            object_id=get_text_box_theme("#text_box_40_horizcenter"),
            anchors={"centerx": "centerx"},
        )

        self.lifegen_button = pygame_gui.elements.UIButton(
            relative_rect=ui_scale(pygame.Rect((155, 175), (140, 32))),
            text="Lifegen",
            manager=MANAGER,
        )
        self.despairgen_button = pygame_gui.elements.UIButton(
            relative_rect=ui_scale(pygame.Rect((305, 175), (140, 32))),
            text="DespairGen",
            manager=MANAGER,
        )

        catname_colour = "#B5A17B" if game_setting_get('dark mode') else "#605546"
        del catname_colour
        if entries:
            stats_text = "".join(
                f"\n <b>{format_despairgen_title(achievement_id, value[0])}</b> - {format_despairgen_description(achievement_id, value[1])}"
                if self.category == DESPAIRGEN
                else f"\n <b>{value[0]}</b> - {value[1]}"
                for achievement_id, value in entries
            )
        else:
            stats_text = "\nNo achievements earned yet."

        self.stats_box = pygame_gui.elements.UITextBox(
            stats_text,
            ui_scale(pygame.Rect((0, 215), (600, 455))),
            manager=MANAGER,
            object_id=get_text_box_theme("#text_box_30_horizcenter"),
            anchors={"centerx": "centerx"},
        )

    def _switch_category(self, category):
        self.category = category
        self.stats_box.kill()
        self.heading.kill()
        self.lifegen_button.kill()
        self.despairgen_button.kill()
        self._build_screen()

    def exit_screen(self):
        for name in ("stats_box", "heading", "lifegen_button", "despairgen_button"):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.kill()
                delattr(self, name)

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == getattr(self, "lifegen_button", None):
                self._switch_category(LIFEGEN)
                return
            if event.ui_element == getattr(self, "despairgen_button", None):
                self._switch_category(DESPAIRGEN)
                return
            self.menu_button_pressed(event)

    def on_use(self):
        super().on_use()
