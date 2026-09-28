import pygame
import pygame_gui

from scripts.game_structure import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.screens.enums import GameScreen
from scripts.ui.elements.image_button import UIImageButton
from scripts.ui.elements.surface_image_button import UISurfaceImageButton
from scripts.ui.generate_button import ButtonStyles, get_button_dict
from scripts.ui.scale import ui_scale, ui_scale_value, ui_scale_offset
from scripts.ui.windows.window_base_class import GameWindow


class JoinDarkForestWindow(GameWindow):
    """Confirms that a cat permanently joins the Dark Forest."""

    def __init__(self, cat):
        super().__init__(
            ui_scale(pygame.Rect((250, 190), (500, 260))),
        )
        self.the_cat = cat

        # Use a Dark Forest-styled crimson close button for this warning window.
        self.back_button.kill()
        close_rect = ui_scale(pygame.Rect((0, 0), (22, 22)))
        close_rect.topright = ui_scale_offset((-5, 7))
        self.back_button = UIImageButton(
            close_rect,
            "",
            object_id="#join_df_close_button",
            starting_height=10,
            container=self,
            anchors={"top": "top", "right": "right"},
        )

        # Give this confirmation window a darker Dark Forest appearance.
        # The regular GameWindow keeps its shared fade, while this custom
        # panel provides a black background and a muted red frame.
        if self.box:
            self.box.kill()
        window_rect = ui_scale(pygame.Rect((244, 184), (512, 272)))
        df_panel = pygame.Surface(window_rect.size, pygame.SRCALPHA)
        df_panel.fill((8, 6, 8, 255))
        pygame.draw.rect(df_panel, (105, 25, 30, 255), df_panel.get_rect(), ui_scale_value(3))
        pygame.draw.rect(
            df_panel,
            (45, 10, 14, 255),
            df_panel.get_rect().inflate(-ui_scale_value(8), -ui_scale_value(8)),
            ui_scale_value(2),
        )
        self.box = pygame_gui.elements.UIImage(
            window_rect,
            df_panel,
            starting_height=self.layer,
            manager=MANAGER,
        )

        self.heading = pygame_gui.elements.UITextBox(
            "windows.join_dark_forest_title",
            ui_scale(pygame.Rect((20, 12), (460, 50))),
            object_id="#join_df_title",
            manager=MANAGER,
            container=self,
        )

        self.warning = pygame_gui.elements.UITextBox(
            "windows.join_dark_forest_warning",
            ui_scale(pygame.Rect((25, 65), (450, 110))),
            object_id="#text_box_30_horizcenter_red",
            manager=MANAGER,
            container=self,
        )

        self.confirm_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((75, 203), (165, 36))),
            "windows.join_dark_forest_confirm",
            get_button_dict(ButtonStyles.DARK_FOREST, (165, 36)),
            MANAGER,
            container=self,
            object_id="#join_df_confirm_button",
        )

        self.cancel_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((260, 203), (165, 36))),
            "buttons.cancel",
            get_button_dict(ButtonStyles.DARK_FOREST, (165, 36)),
            MANAGER,
            container=self,
            object_id="#join_df_cancel_button",
        )

    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.confirm_button:
                if not self.the_cat.bound_to_df:
                    self.the_cat.join_df()
                profile = game.all_screens.get(GameScreen.PROFILE)
                if profile:
                    # Close the dangerous-tab controls before rebuilding the
                    # profile. This prevents the old Join button from being
                    # left behind when the cat becomes permanently bound.
                    self.kill()
                    profile.close_current_tab()
                    profile.clear_profile()
                    profile.build_profile()
                    profile.update_disabled_buttons_and_text()
                else:
                    self.kill()
            elif event.ui_element == self.cancel_button:
                self.kill()

        return super().process_event(event)
