import random
import traceback
from copy import deepcopy

import pygame
import pygame_gui
from pygame_gui.core import ObjectID

from scripts.cat.cats import Cat
from scripts.game_structure import image_cache, constants
from scripts.game_structure.game.settings import game_setting_get
from scripts.game_structure import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.ui.theme import get_text_box_theme
from ..ui.elements.sprite_button import UISpriteButton
from ..ui.elements.image_button import UIImageButton
from ..ui.elements.surface_image_button import UISurfaceImageButton
from ..ui.scale import ui_scale, ui_scale_dimensions, ui_scale_value
from .Screens import Screens
from .enums import GameScreen
from ..clan_package.settings import get_clan_setting
from ..clan_package.settings.clan_settings import switch_clan_setting
from ..game_structure.game.switches import switch_set_value, Switch
from ..cat.enums import CatRank, CatAge, CatGroup
from ..ui.elements.save_button import UISaveButton
from ..ui.generate_button import ButtonStyles, get_button_dict


from scripts.lifegen_utility import assign_new_bg, get_current_camp


class ClanScreen(Screens):
    max_sprites_displayed = (
        400  # we don't want 100,000 sprites rendering at once. 400 is enough.
    )
    cat_buttons = []

    def create_clan_faith_panel(self, width, height):
        """Create the decorative Clan Faith panel background."""

        panel_size = ui_scale_dimensions((width, height))
        panel = pygame.Surface(panel_size, pygame.SRCALPHA)

        scale_x = panel_size[0] / width
        scale_y = panel_size[1] / height

        def point(x, y):
            return (
                int(x * scale_x),
                int(y * scale_y),
            )

        def scaled_rect(x, y, w, h):
            return pygame.Rect(
                int(x * scale_x),
                int(y * scale_y),
                int(w * scale_x),
                int(h * scale_y),
            )

        # ==================================================
        # PANEL BACKGROUND
        # ==================================================

        # Dark, slightly translucent interior
        panel.fill((24, 22, 24, 235))

        # Outer shadow/frame
        pygame.draw.rect(
            panel,
            (57, 45, 35),
            scaled_rect(0, 0, width, height),
        )

        # Outer gold border
        pygame.draw.rect(
            panel,
            (177, 148, 91),
            scaled_rect(2, 2, width - 4, height - 4),
            max(1, int(2 * scale_x)),
        )

        # Dark space between borders
        pygame.draw.rect(
            panel,
            (40, 33, 31),
            scaled_rect(6, 6, width - 12, height - 12),
            max(1, int(1 * scale_x)),
        )

        # Inner gold border
        pygame.draw.rect(
            panel,
            (117, 94, 61),
            scaled_rect(9, 9, width - 18, height - 18),
            max(1, int(1 * scale_x)),
        )

        # ==================================================
        # ORNAMENTAL CORNERS
        # ==================================================

        bright_gold = (192, 161, 99)
        dark_gold = (105, 82, 55)

        def draw_corner(x, y, x_dir, y_dir):
            # Long horizontal arm
            pygame.draw.line(
                panel,
                bright_gold,
                point(x, y),
                point(x + 18 * x_dir, y),
                max(1, int(2 * scale_x)),
            )

            # Long vertical arm
            pygame.draw.line(
                panel,
                bright_gold,
                point(x, y),
                point(x, y + 18 * y_dir),
                max(1, int(2 * scale_y)),
            )

            # Diagonal flourish
            pygame.draw.line(
                panel,
                dark_gold,
                point(x + 3 * x_dir, y + 3 * y_dir),
                point(x + 10 * x_dir, y + 10 * y_dir),
                max(1, int(1 * scale_x)),
            )

            # Diamond at the corner
            diamond = [
                point(x, y - 4 * y_dir),
                point(x + 4 * x_dir, y),
                point(x, y + 4 * y_dir),
                point(x - 4 * x_dir, y),
            ]

            pygame.draw.polygon(panel, bright_gold, diamond)
            pygame.draw.polygon(
                panel,
                (55, 43, 38),
                diamond,
                max(1, int(1 * scale_x)),
            )

        draw_corner(12, 12, 1, 1)
        draw_corner(width - 12, 12, -1, 1)
        draw_corner(12, height - 12, 1, -1)
        draw_corner(width - 12, height - 12, -1, -1)

        # ==================================================
        # DIVIDERS
        # ==================================================

        divider_color = (159, 132, 82)

        def draw_divider(y):
            # Left half
            pygame.draw.line(
                panel,
                divider_color,
                point(24, y),
                point(width / 2 - 10, y),
                max(1, int(1 * scale_y)),
            )

            # Right half
            pygame.draw.line(
                panel,
                divider_color,
                point(width / 2 + 10, y),
                point(width - 24, y),
                max(1, int(1 * scale_y)),
            )

            # Decorative center diamond
            center_x = width / 2

            diamond = [
                point(center_x, y - 4),
                point(center_x + 4, y),
                point(center_x, y + 4),
                point(center_x - 4, y),
            ]

            pygame.draw.polygon(panel, divider_color, diamond)

        draw_divider(53)
        draw_divider(142)

        # Small decorative dots beside each divider ornament
        for y in (53, 142):
            pygame.draw.circle(
                panel,
                dark_gold,
                point(width / 2 - 16, y),
                max(1, int(2 * scale_x)),
            )

            pygame.draw.circle(
                panel,
                dark_gold,
                point(width / 2 + 16, y),
                max(1, int(2 * scale_x)),
            )

        return panel        #Create the custom Clan Faith panel background.

        panel_size = ui_scale_dimensions((width, height))
        panel = pygame.Surface(panel_size, pygame.SRCALPHA)

        scale_x = panel_size[0] / width
        scale_y = panel_size[1] / height

        def scaled_rect(x, y, w, h):
            return pygame.Rect(
                int(x * scale_x),
                int(y * scale_y),
                int(w * scale_x),
                int(h * scale_y),
            )

        # Main dark panel background
        panel.fill((31, 29, 29, 245))

        # Outer gold frame
        pygame.draw.rect(
            panel,
            (151, 128, 82),
            scaled_rect(1, 1, width - 2, height - 2),
            max(1, int(2 * scale_x)),
        )

        # Dark gap between borders
        pygame.draw.rect(
            panel,
            (75, 64, 48),
            scaled_rect(5, 5, width - 10, height - 10),
            max(1, int(1 * scale_x)),
        )

        # Inner gold frame
        pygame.draw.rect(
            panel,
            (112, 94, 63),
            scaled_rect(8, 8, width - 16, height - 16),
            max(1, int(2 * scale_x)),
        )

        # Decorative corner pieces
        corner_color = (176, 150, 94)
        dark_gold = (99, 81, 54)

        corner_size = 12
        corner_inset = 8

        corners = [
            (corner_inset, corner_inset, 1, 1),
            (width - corner_inset, corner_inset, -1, 1),
            (corner_inset, height - corner_inset, 1, -1),
            (width - corner_inset, height - corner_inset, -1, -1),
        ]

        for x, y, x_dir, y_dir in corners:
            # Horizontal decorative arm
            pygame.draw.line(
                panel,
                corner_color,
                (
                    int(x * scale_x),
                    int(y * scale_y),
                ),
                (
                    int((x + corner_size * x_dir) * scale_x),
                    int(y * scale_y),
                ),
                max(1, int(2 * scale_x)),
            )

            # Vertical decorative arm
            pygame.draw.line(
                panel,
                corner_color,
                (
                    int(x * scale_x),
                    int(y * scale_y),
                ),
                (
                    int(x * scale_x),
                    int((y + corner_size * y_dir) * scale_y),
                ),
                max(1, int(2 * scale_y)),
            )

            # Small dark decorative square
            pygame.draw.rect(
                panel,
                dark_gold,
                scaled_rect(
                    x + (2 * x_dir),
                    y + (2 * y_dir),
                    4,
                    4,
                ),
            )

        # Top divider
        pygame.draw.line(
            panel,
            (143, 122, 83),
            (
                int(20 * scale_x),
                int(53 * scale_y),
            ),
            (
                int((width - 20) * scale_x),
                int(53 * scale_y),
            ),
            max(1, int(1 * scale_y)),
        )

        # Bottom divider
        pygame.draw.line(
            panel,
            (143, 122, 83),
            (
                int(20 * scale_x),
                int(142 * scale_y),
            ),
            (
                int((width - 20) * scale_x),
                int(142 * scale_y),
            ),
            max(1, int(1 * scale_y)),
        )

        return panel 

    def __init__(self, name=None):
        super().__init__(name)
        self.cats_in_camp = []
        self.taken_spaces = {}
        self.show_den_labels_text = None
        self.show_den_labels = None
        self.show_den_text = None
        self.label_toggle = None
        self.app_den_label = None
        self.clearing_label = None
        self.nursery_label = None
        self.elder_den_label = None
        self.med_den_label = None
        self.leader_den_label = None
        self.warrior_den_label = None
        self.layout = None
        self.clan_faith_display = None
        self.clan_faith_box = None
        self.clan_faith_labels = []

    def on_use(self):
        if not get_clan_setting("backgrounds"):
            self.set_bg(None)
        super().on_use()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            self.mute_button_pressed(event)
            if event.ui_element == self.save_button.unsaved_state:
                self.save_button.save_game(current_screen=self)
            if event.ui_element in self.cat_buttons:
                switch_set_value(Switch.cat, event.ui_element.return_cat_id())
                self.change_screen(GameScreen.PROFILE)
            if event.ui_element == self.label_toggle:
                switch_clan_setting("den labels")
                self.update_buttons_and_text()
            if event.ui_element == self.med_den_label:
                self.change_screen(GameScreen.MED_DEN)
            if event.ui_element == self.clearing_label:
                self.change_screen(GameScreen.MEDIATION)
            if event.ui_element == self.warrior_den_label:
                self.change_screen(GameScreen.WARRIOR_DEN)
            if event.ui_element == self.leader_den_label:
                self.change_screen(GameScreen.LEADER_DEN)
            else:
                self.menu_button_pressed(event)

        elif event.type == pygame.KEYDOWN and game_setting_get("keybinds"):
            if event.key == pygame.K_RIGHT:
                self.change_screen(GameScreen.LIST)
            elif event.key == pygame.K_LEFT:
                self.change_screen(GameScreen.EVENTS)
            elif event.key == pygame.K_SPACE:
                self.save_button.save_game(current_screen=self)

    def screen_switches(self):
        super().screen_switches()
        self.show_mute_buttons()
        self.update_camp_bg()
        switch_set_value(Switch.cat, None)

        clan_faith = game.clan.get_clan_faith()

        # Custom Clan Faith panel
        self.clan_faith_box = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((15, 445), (230, 180))),
            self.create_clan_faith_panel(230, 180),
            starting_height=1,
            manager=MANAGER,
        )

        # Clan Faith text labels

        self.clan_faith_labels = []

        # Title
        self.clan_faith_labels.append(
            pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((35, 458), (190, 25))),
                text="CLAN FAITH",
                manager=MANAGER,
                object_id="#clan_faith_title",
            )
        )

        self.clan_faith_labels[-1].change_layer(11)

        # StarClan Name
        self.clan_faith_labels.append(
            pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((35, 510), (120, 22))),
                text="Starclan:",
                manager=MANAGER,
                object_id="#clan_faith_starclan",
            )
        )

        self.clan_faith_labels[-1].change_layer(11)

        #StarClan Percentage
        self.clan_faith_labels.append(
            pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((165, 510), (55, 22))),
                text=f"{clan_faith['starclan']}%",
                manager=MANAGER,
                object_id="#clan_faith_starclan",
            )
        )

        # Neutral Name
        self.clan_faith_labels.append(
            pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((35, 535), (120, 22))),
                text="Neutral:",
                manager=MANAGER,
                object_id="#clan_faith_neutral",
            )
        )

        self.clan_faith_labels[-1].change_layer(11)

        #Neutral Percentage
        self.clan_faith_labels.append(
            pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((165, 535), (55, 22))),
                text=f"{clan_faith['neutral']}%",
                manager=MANAGER,
                object_id="#clan_faith_neutral",
            )
        )

        self.clan_faith_labels[-1].change_layer(11)

        # Dark Forest Name
        self.clan_faith_labels.append(
            pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((35, 560), (120, 22))),
                text="Dark Forest:",
                manager=MANAGER,
                object_id="#clan_faith_darkforest",
            )
        )

        self.clan_faith_labels[-1].change_layer(11)

        # Dark Forest Percentage
        self.clan_faith_labels.append(
            pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((165, 560), (55, 22))),
                text=f"{clan_faith['dark_forest']}%",
                manager=MANAGER,
                object_id="#clan_faith_darkforest",
            )
        )

        self.clan_faith_labels[-1].change_layer(11)

        # Faith state
        self.clan_faith_labels.append(
            pygame_gui.elements.UILabel(
                relative_rect=ui_scale(pygame.Rect((35, 594), (190, 25))),
                text=clan_faith['state'],
                manager=MANAGER,
                object_id="#clan_faith_state",
            )
        )

        self.clan_faith_labels[-1].change_layer(11)

        if game.clan.your_cat.status.group == CatGroup.HOUSEHOLD:
            current_bg = game.clan.household_bg
        elif game.clan.your_cat.status.group == CatGroup.LONER_GROUP:
            current_bg = game.clan.loner_group_bg
        elif game.clan.your_cat.status.group == CatGroup.ROGUE_GROUP:
            current_bg = game.clan.rogue_group_bg
        else:
            current_bg = game.clan.camp_bg


        if game.clan.biome + current_bg in constants.LAYOUTS:
            self.layout = constants.LAYOUTS[game.clan.biome + current_bg]
        else:
            self.layout = constants.LAYOUTS["default"]

        if "cat_shading" not in self.layout:
            self.layout["cat_shading"] = constants.LAYOUTS["default"]["cat_shading"]

        self.choose_cat_positions()

        self.set_disabled_menu_buttons(["camp_screen"])

        # LG EDIT
        self.update_heading_text(game.clan.your_cat.status.get_group_heading_text())
        # ---
        self.show_menu_buttons()
        Screens.menu_buttons["back_to_camp"].hide()

        # Creates and places the cat sprites.
        self.cat_buttons = []  # To contain all the buttons.

        # We have to convert the positions to something pygame_gui buttons will understand
        # This should be a temp solution. We should change the code that determines positions.
        i = 0
        all_positions = list(self.taken_spaces.values())
        used_positions = all_positions.copy()

        layers = []
        for x in self.cats_in_camp:
            layers.append(2)
            place = self.taken_spaces[x.ID]
            layers[-1] += all_positions.count(place) - used_positions.count(place)
            used_positions.remove(place)

            try:
                image = x.sprite.convert_alpha()
                try:
                    blend_layer = (
                        self.game_bgs[self.active_bg]
                        .subsurface(ui_scale(pygame.Rect(tuple(x.placement), (50, 50))))
                        .convert_alpha()
                    )
                    blend_layer = pygame.transform.box_blur(
                        blend_layer, self.layout["cat_shading"]["blur"]
                    )
                except ValueError:
                    print("LG PRINT: ValueError:", x.placement, "is out of bounds.")
                    x_diff = ui_scale_value(
                        50 + (x.placement[0] if x.placement[0] < 0 else 0)
                    )
                    y_diff = ui_scale_value(
                        50 + (x.placement[1] if x.placement[1] < 0 else 0)
                    )
                    avg_layer = self.game_bgs[self.active_bg].subsurface(
                        ui_scale(
                            pygame.Rect(
                                (
                                    x.placement[0] if x.placement[0] > 0 else 0,
                                    x.placement[1] if x.placement[1] > 0 else 0,
                                ),
                                (x_diff, y_diff),
                            )
                        )
                    )
                    blend_layer = pygame.Surface(ui_scale_dimensions((50, 50)))
                    blend_layer.fill(pygame.transform.average_color(avg_layer))

                sprite = image.copy()
                sprite.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)
                sprite.blit(blend_layer, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                image.set_alpha(self.layout["cat_shading"]["blend_strength"])
                sprite.blit(image, (0, 0), special_flags=pygame.BLEND_ALPHA_SDL2)
                sprite.set_alpha(255)

                self.cat_buttons.append(
                    UISpriteButton(
                        ui_scale(pygame.Rect(tuple(x.placement), (50, 50))),
                        sprite,
                        mask=x.sprite_mask,
                        cat_id=x.ID,
                        starting_height=layers[-1],
                    )
                )
            except:
                traceback.print_exc()
                print(f"ERROR: placing {x.name}'s sprite on Clan page")

        # Den Labels
        # Redo the locations, so that it uses layout on the Clan page
        self.warrior_den_label = UISurfaceImageButton(
            ui_scale(pygame.Rect(self.layout["warrior den"], (121, 28))),
            "screens.core.warriors_den",
            get_button_dict(ButtonStyles.ROUNDED_RECT, (121, 28)),
            object_id=ObjectID(class_id="@buttonstyles_rounded_rect", object_id=None),
            starting_height=2,
        )
        self.leader_den_label = UISurfaceImageButton(
            ui_scale(pygame.Rect(self.layout["leader den"], (112, 28))),
            "screens.core.leader_den",
            get_button_dict(ButtonStyles.ROUNDED_RECT, (112, 28)),
            object_id=ObjectID(class_id="@buttonstyles_rounded_rect", object_id=None),
            starting_height=2,
        )
        self.med_den_label = UISurfaceImageButton(
            ui_scale(pygame.Rect(self.layout["medicine den"], (151, 28))),
            "screens.core.medicine_cat_den",
            get_button_dict(ButtonStyles.ROUNDED_RECT, (151, 28)),
            object_id=ObjectID(class_id="@buttonstyles_rounded_rect", object_id=None),
            starting_height=2,
        )
        self.elder_den_label = UISurfaceImageButton(
            ui_scale(pygame.Rect(self.layout["elder den"], (103, 28))),
            "screens.core.elders_den",
            get_button_dict(ButtonStyles.ROUNDED_RECT, (103, 28)),
            object_id=ObjectID(class_id="@buttonstyles_rounded_rect", object_id=None),
        )
        self.elder_den_label.disable()
        self.nursery_label = UISurfaceImageButton(
            ui_scale(pygame.Rect(self.layout["nursery"], (80, 28))),
            "screens.core.nursery",
            get_button_dict(ButtonStyles.ROUNDED_RECT, (80, 28)),
            object_id=ObjectID(class_id="@buttonstyles_rounded_rect", object_id=None),
        )
        self.nursery_label.disable()

        self.clearing_label = UISurfaceImageButton(
            ui_scale(pygame.Rect(self.layout["clearing"], (81, 28))),
            "screens.core.clearing",
            get_button_dict(ButtonStyles.ROUNDED_RECT, (81, 28)),
            object_id=ObjectID(class_id="@buttonstyles_rounded_rect", object_id=None),
        )

        self.app_den_label = UISurfaceImageButton(
            ui_scale(pygame.Rect(self.layout["apprentice den"], (147, 28))),
            "screens.core.apprentices_den",
            get_button_dict(ButtonStyles.ROUNDED_RECT, (147, 28)),
            object_id=ObjectID(class_id="@buttonstyles_rounded_rect", object_id=None),
        )
        self.app_den_label.disable()

        # Draw the toggle and text
        self.show_den_labels = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((25, 641), (167, 34))),
            pygame.transform.scale(
                image_cache.load_image("resources/images/show_den_labels.png"),
                ui_scale_dimensions((167, 34)),
            ),
        )
        self.show_den_labels_text = pygame_gui.elements.UILabel(
            ui_scale(pygame.Rect((60, 641), (130, 34))),
            "screens.clan.show_dens",
            object_id="@buttonstyles_rounded_rect",
        )
        self.show_den_labels.disable()
        self.label_toggle = UIImageButton(
            ui_scale(pygame.Rect((25, 641), (32, 32))),
            "",
            object_id="@checked_checkbox",
        )

        self.save_button = UISaveButton(
            position=(343, 643),
        )

        self.update_buttons_and_text()

    def exit_screen(self):
        # removes the cat sprites.
        for button in self.cat_buttons:
            button.kill()
        self.cat_buttons = []

        self.taken_spaces.clear()
        self.cats_in_camp.clear()

        # Kill all other elements, and destroy the reference so they aren't hanging around
        self.save_button.kill()
        del self.save_button
        self.warrior_den_label.kill()
        del self.warrior_den_label
        self.leader_den_label.kill()
        del self.leader_den_label
        self.med_den_label.kill()
        del self.med_den_label
        self.elder_den_label.kill()
        del self.elder_den_label
        self.nursery_label.kill()
        del self.nursery_label
        self.clearing_label.kill()
        del self.clearing_label
        self.app_den_label.kill()
        del self.app_den_label
        self.label_toggle.kill()
        del self.label_toggle
        self.show_den_labels.kill()
        del self.show_den_labels
        self.show_den_labels_text.kill()
        del self.show_den_labels_text
        for label in self.clan_faith_labels:
            label.kill()

        self.clan_faith_labels.clear()
        self.clan_faith_box.kill()
        del self.clan_faith_box

        # reset save status
        switch_set_value(Switch.saved_clan, False)
        Screens.menu_buttons["back_to_camp"].show()

    def update_camp_bg(self):
        light_dark = "dark" if game_setting_get("dark mode") else "light"

        leaves = ["newleaf", "greenleaf", "leafbare", "leaffall"]
        camp_bg_base_dir, camp_nr = get_current_camp()

        if not camp_nr:
            camp_nr = "camp1"
            assign_new_bg("camp1")

        available_biome = ["Forest", "Mountainous", "Plains", "Beach"]
        biome = game.clan.biome
        if biome not in available_biome:
            biome = available_biome[0]
            game.clan.biome = biome
        biome = biome.lower()

        all_backgrounds = []
        for leaf in leaves:
            platform_dir = (
                f"{camp_bg_base_dir}/{biome}/{leaf}_{camp_nr}_{light_dark}.png"
            )
            all_backgrounds.append(platform_dir)

        self.add_bgs(
            {
                "Newleaf": pygame.transform.scale(
                    pygame.image.load(all_backgrounds[0]).convert(),
                    ui_scale_dimensions((800, 700)),
                ),
                "Greenleaf": pygame.transform.scale(
                    pygame.image.load(all_backgrounds[1]).convert(),
                    ui_scale_dimensions((800, 700)),
                ),
                "Leaf-bare": pygame.transform.scale(
                    pygame.image.load(all_backgrounds[2]).convert(),
                    ui_scale_dimensions((800, 700)),
                ),
                "Leaf-fall": pygame.transform.scale(
                    pygame.image.load(all_backgrounds[3]).convert(),
                    ui_scale_dimensions((800, 700)),
                ),
            },
            {
                "Newleaf": None,
                "Greenleaf": None,
                "Leaf-bare": None,
                "Leaf-fall": None,
            },
        )

        self.set_bg(game.clan.current_season)

    def choose_nonoverlapping_positions(self, first_choices, dens, weights=None):
        if not weights:
            weights = [1] * len(dens)

        dens = dens.copy()

        chosen_index = random.choices(range(0, len(dens)), weights=weights, k=1)[0]
        first_chosen_den = dens[chosen_index]
        while True:
            chosen_den = dens[chosen_index]
            if first_choices[chosen_den]:
                pos = random.choice(first_choices[chosen_den])
                first_choices[chosen_den].remove(pos)
                just_pos = pos[0].copy()
                if pos not in first_choices[chosen_den]:
                    # Then this is the second cat to be places here, given an offset

                    # Offset based on the "tag" in pos[1]. If "y" is in the tag,
                    # the cat will be offset down. If "x" is in the tag, the behavior depends on
                    # the presence of the "y" tag. If "y" is not present, always shift the cat left or right
                    # if it is present, shift the cat left or right 3/4 of the time.
                    if "x" in pos[1] and ("y" not in pos[1] or random.getrandbits(2)):
                        just_pos[0] += 15 * random.choice([-1, 1])
                    if "y" in pos[1]:
                        just_pos[1] += 15
                return tuple(just_pos), pos[0]
            dens.pop(chosen_index)
            weights.pop(chosen_index)
            if not dens:
                break
            # Put finding the next index after the break condition, so it won't be done unless needed
            chosen_index = random.choices(range(0, len(dens)), weights=weights, k=1)[0]

        return None, None

    def choose_cat_positions(self):
        """Determines the positions of cat on the clan screen."""
        # These are the first choices. As positions are chosen, they are removed from the options to indicate they are
        # taken.
        first_choices = deepcopy(self.layout)

        all_dens = [
            "nursery place",
            "leader place",
            "elder place",
            "medicine place",
            "apprentice place",
            "clearing place",
            "warrior place",
        ]

        # Allow two cat in the same position.
        for x in all_dens:
            first_choices[x].extend(first_choices[x])

        for x in game.clan.clan_cats:
            # if not Cat.all_cats[x].status.alive_in_player_clan:
            if not Cat.all_cats[x].status.alive_in_your_cat_group:
                continue

            base_pos = None
            # Newborns are not meant to be placed. They are hiding.
            if (
                Cat.all_cats[x].age == CatAge.NEWBORN
                or constants.CONFIG["fun"]["all_cats_are_newborn"]
                or Cat.all_cats[x].moons < 0
            ):
                if (
                    (constants.CONFIG["fun"]["all_cats_are_newborn"]
                    or constants.CONFIG["fun"]["newborns_can_roam"])
                    and Cat.all_cats[x].moons >= 0
                ):
                    # Free them
                    [
                        Cat.all_cats[x].placement,
                        base_pos,
                    ] = self.choose_nonoverlapping_positions(
                        first_choices, all_dens, [1, 100, 1, 1, 1, 100, 50]
                    )
                else:
                    continue

            if Cat.all_cats[x].status.rank in (
                CatRank.APPRENTICE,
                CatRank.MEDIATOR_APPRENTICE,
                CatRank.QUEENS_APPRENTICE
            ):
                [
                    Cat.all_cats[x].placement,
                    base_pos,
                ] = self.choose_nonoverlapping_positions(
                    first_choices, all_dens, [1, 50, 1, 1, 100, 100, 1]
                )
            elif Cat.all_cats[x].status.rank == CatRank.DEPUTY:
                [
                    Cat.all_cats[x].placement,
                    base_pos,
                ] = self.choose_nonoverlapping_positions(
                    first_choices, all_dens, [1, 50, 1, 1, 1, 50, 1]
                )

            elif Cat.all_cats[x].status.rank == CatRank.ELDER:
                [
                    Cat.all_cats[x].placement,
                    base_pos,
                ] = self.choose_nonoverlapping_positions(
                    first_choices, all_dens, [1, 1, 2000, 1, 1, 1, 1]
                )
            elif Cat.all_cats[x].status.rank == CatRank.KITTEN:
                [
                    Cat.all_cats[x].placement,
                    base_pos,
                ] = self.choose_nonoverlapping_positions(
                    first_choices, all_dens, [60, 8, 1, 1, 1, 1, 1]
                )
            elif Cat.all_cats[x].status.rank.is_any_medicine_rank():
                [
                    Cat.all_cats[x].placement,
                    base_pos,
                ] = self.choose_nonoverlapping_positions(
                    first_choices, all_dens, [20, 20, 20, 400, 1, 1, 1]
                )
            elif Cat.all_cats[x].status.rank in (CatRank.WARRIOR, CatRank.MEDIATOR, CatRank.QUEEN):
                [
                    Cat.all_cats[x].placement,
                    base_pos,
                ] = self.choose_nonoverlapping_positions(
                    first_choices, all_dens, [1, 1, 1, 1, 1, 60, 60]
                )
            elif Cat.all_cats[x].status.is_leader:
                [
                    Cat.all_cats[x].placement,
                    base_pos,
                ] = self.choose_nonoverlapping_positions(
                    first_choices, all_dens, [1, 200, 1, 1, 1, 1, 1]
                )
            # LG
            # placing outsiders if youre outside
            else:
                [
                    Cat.all_cats[x].placement,
                    base_pos,
                ] = self.choose_nonoverlapping_positions(
                    first_choices, all_dens, [1, 100, 1, 1, 1, 100, 50]
                )
            # ---
            if not Cat.all_cats[x].placement:
                # if a cat wasn't placed, it's because no spots remain
                break

            self.taken_spaces[Cat.all_cats[x].ID] = base_pos
            self.cats_in_camp.append(Cat.all_cats[x])

    def update_buttons_and_text(self):
        self.save_button.update_state()

        self.label_toggle.kill()
        if game.clan.your_cat.status.group.is_any_clan_group():
            if get_clan_setting("den labels"):
                self.label_toggle = UIImageButton(
                    ui_scale(pygame.Rect((25, 641), (34, 34))),
                    "",
                    starting_height=2,
                    object_id="@checked_checkbox",
                )
                self.warrior_den_label.show()
                self.clearing_label.show()
                self.nursery_label.show()
                self.app_den_label.show()
                self.leader_den_label.show()
                self.med_den_label.show()
                self.elder_den_label.show()
            else:
                self.label_toggle = UIImageButton(
                    ui_scale(pygame.Rect((25, 641), (34, 34))),
                    "",
                    starting_height=2,
                    object_id="@unchecked_checkbox",
                )
                self.warrior_den_label.hide()
                self.clearing_label.hide()
                self.nursery_label.hide()
                self.app_den_label.hide()
                self.leader_den_label.hide()
                self.med_den_label.hide()
                self.elder_den_label.hide()
        else:
            self.show_den_labels.hide()
            self.show_den_labels_text.hide()
            self.label_toggle.hide()
            self.warrior_den_label.hide()
            self.clearing_label.hide()
            self.nursery_label.hide()
            self.app_den_label.hide()
            self.leader_den_label.hide()
            self.med_den_label.hide()
            self.elder_den_label.hide()