import html

import pygame

from scripts.game_structure.screen_settings import MANAGER
from scripts.ui.elements.text_box_tweaked import UITextBoxTweaked
from scripts.ui.windows.window_base_class import GameWindow
from scripts.ui.scale import ui_scale


class TimeskipProfilerWindow(GameWindow):
    """Displays the optional v0.6.1.1 moon-skip performance profile."""

    def __init__(self, profile_data):
        super().__init__(
            ui_scale(pygame.Rect((110, 90), (580, 520))),
            window_display_title="Timeskip Performance",
            click_outside_to_close=False,
        )

        self.profile_data = profile_data or {}
        self.profile_text = UITextBoxTweaked(
            self._build_profile_text(),
            ui_scale(pygame.Rect((18, 45), (544, 455))),
            object_id="#text_box_30",
            line_spacing=0.95,
            starting_height=2,
            container=self,
            manager=MANAGER,
        )

    def _build_profile_text(self):
        data = self.profile_data
        total = data.get("total", 0.0)
        cat_count = data.get("cats", 0)
        cat_total = data.get("cat_total", 0.0)
        cat_avg = data.get("cat_avg", 0.0)

        lines = [
            "<b>Moon skip complete</b>",
            "",
            f"<b>Total time:</b> {total:.3f}s",
            f"<b>Cats processed:</b> {cat_count}",
            f"<b>Cat processing:</b> {cat_total:.3f}s",
            f"<b>Average per cat:</b> {cat_avg:.4f}s",
            "",
            "<b>Moon stages</b>",
        ]

        for name, elapsed in data.get("stages", []):
            lines.append(f"{html.escape(str(name))}: {elapsed:.3f}s")

        cat_sections = data.get("cat_sections", [])
        if cat_sections:
            lines.extend(["", "<b>Cat processing breakdown</b>"])
            for name, elapsed in cat_sections:
                lines.append(f"{html.escape(str(name))}: {elapsed:.3f}s")

        slowest = data.get("slowest_cats", [])
        if slowest:
            lines.extend(["", "<b>10 slowest cats</b>"])
            for elapsed, name, cat_id in slowest:
                lines.append(
                    f"{html.escape(str(name))} #{html.escape(str(cat_id))}: {elapsed:.3f}s"
                )

        return "<br>".join(lines)
