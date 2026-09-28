import random

from scripts.game_structure import game, constants
from scripts.special_dates import get_special_date
from scripts.game_structure.game.switches import switch_get_value, Switch
from scripts.game_structure.localization import load_lang_resource
from scripts.cat.enums import CatRank, CatAge, CatGroup
from scripts.cat.cats import Cat
from scripts.cat.pelts import Pelt
from scripts.events_module.consequences import unpack_rel_block


from scripts.events_module.filter_random_cats import choose_random_cats

# pylint: disable=consider-using-dict-items

class Dialogue():
    def __init__(
        self,
        cat: Cat,
        you: Cat
    ):
        self.cat = cat
        self.you = you
        self.debug = constants.CONFIG["lifegen"]["debug"]["debug_ensure_dialogue"]
        self.cat_dict = {}

        # holds a cat dict for each dialogue key
        self.dialogue_cat_dict = {}

    def load_texts(self):
        """
        Loads dialogue depending on rank, group, age
        """

        resource_dir = "lifegen_talk"
        possible_texts = {}

        special_date = get_special_date()

        if switch_get_value(Switch.talk_category) == "insult":
            possible_texts.update(load_lang_resource(f"{resource_dir}/insults.json"))
        elif switch_get_value(Switch.talk_category) == "flirt":
            possible_texts.update(load_lang_resource(f"{resource_dir}/flirt.json"))
        else:
            possible_texts.update(
                load_lang_resource(
                    f"{resource_dir}/{self.cat.status.rank.replace(' ', '_')}.json"
                    )
                )
            if self.cat.status.is_outsider:
                possible_texts.update(load_lang_resource(f"{resource_dir}/general_outsider.json"))
            else:
                if self.cat.status.rank != CatRank.NEWBORN:
                    # newborns will no longer participate in nuanced discussion

                    if not self.cat.status.rank.is_baby() and not self.you.status.rank.is_baby():
                        possible_texts.update(
                            load_lang_resource(
                                f"{resource_dir}/general_no_kit.json"
                                )
                            )
                    if self.cat.age != CatAge.NEWBORN and self.you.age != CatAge.NEWBORN:
                        possible_texts.update(
                            load_lang_resource(
                                f"{resource_dir}/general_no_newborn.json"
                                )
                            )
                    if not self.cat.status.rank.is_baby() and self.you.status.rank.is_baby():
                        possible_texts.update(
                            load_lang_resource(
                                f"{resource_dir}/general_you_kit.json"
                                )
                            )
                    if game.clan.focus:
                        possible_texts.update(
                            load_lang_resource(
                                f"{resource_dir}/focuses/{game.clan.focus}.json"
                                )
                            )
                    if special_date:
                        possible_texts.update(
                            load_lang_resource(
                                f"{resource_dir}/focuses/{special_date.patrol_tag}.json"
                                )
                            )
                    if constants.CONFIG['fun']['april_fools']:
                        possible_texts.update(
                            load_lang_resource(
                                f"{resource_dir}/focuses/aprilfools.json"
                                )
                            )
        
        # uncomment below to limit dialogue range
        # this can cut down on dialogue delay, but also cause some meow errors

        # dialogue_range = 200
        # shuffled_dict = dict(random.sample(list(possible_texts.items()), len(possible_texts)))
        # new_dict = {}
        # count = 0
        # for key, dialogue in shuffled_dict.items():
        #     if count >= dialogue_range:
        #         break
        #     new_dict[key] = dialogue
        #     count += 1
        # possible_texts = new_dict

        # DEBUG
        # possible_texts = load_lang_resource("lifegen_talk/TEST.json")
        return possible_texts

    def filter_dialogue(self, possible_texts, flirt):
        """
        Filters possible dialogue for selection.
        Season, biome, camp, and frequency are addressed here. Cats are validated later.
        """

        flirt_success = self.get_flirt_success()

        possible_dialogue = {}
        for key, block in possible_texts.items():
            if "season" in block:
                if (
                    game.clan.current_season not in block["season"] and
                    game.clan.current_season.lower() not in block["season"]
                    ):
                    continue
            if "biome" in block:
                if (
                    block["biome"] and
                    game.clan.biome not in block["biome"] and
                    game.clan.biome.lower() not in block["biome"]
                    ):
                    continue
            if "camp" in block:
                if block["camp"] and game.clan.camp_bg not in block["camp"]:
                    continue

            if "frequency" in block:
                count = block["frequency"]
                for other_block in block:
                    if other_block in ["season", "biome", "camp", "relationships"]:
                        count += 1
                for i in range(count):
                    possible_dialogue.update({key: block})
            else:
                print("Warning: Dialogue", key, "has no frequency.")
                possible_dialogue.update({key: block})
            
            if flirt:
                if "tags" in block:
                    if "reject" in block["tags"] and flirt_success:
                        continue
                    elif "accept" in block["tags"] and not flirt_success:
                        continue
                else:
                    if not flirt_success:
                        continue

        return possible_dialogue

    def get_cat_dict(self):
        """
        Returns the cat dict for use in TalkScreen
        """
        return self.cat_dict

    @staticmethod
    def _anchor_rank_matches(cat, rank_block):
        """Return True only when an explicit dialogue rank block matches cat."""
        if not rank_block or "any" in rank_block:
            return True

        raw_rank = getattr(getattr(cat, "status", None), "rank", None)
        raw_rank = getattr(raw_rank, "value", str(raw_rank))
        normalized_rank = str(raw_rank).replace(" ", "_")

        # Negative rank tags are exclusions.
        if (
            f"not_{raw_rank}" in rank_block
            or f"not_{normalized_rank}" in rank_block
            or f"-{raw_rank}" in rank_block
            or f"-{normalized_rank}" in rank_block
        ):
            return False

        # Special LifeGen role tags are additional constraints.
        if "df_trainee" in rank_block and not getattr(cat, "joined_df", False):
            return False
        if "not_df_trainee" in rank_block and getattr(cat, "joined_df", False):
            return False
        if "guide" in rank_block and cat not in (game.clan.instructor, game.clan.demon):
            return False

        special = {"df_trainee", "not_df_trainee", "guide"}
        positive = [
            tag for tag in rank_block
            if isinstance(tag, str)
            and not tag.startswith("not_")
            and not tag.startswith("-")
            and tag not in special
        ]
        if not positive:
            return True
        return str(raw_rank) in positive or normalized_rank in positive

    def _dialogue_anchors_match(self, dialogue_block):
        """Final identity guard for fixed y_c/t_c dialogue anchors.

        Dialogue resources are allowed to describe the player or target with
        explicit rank/residence restrictions. Those restrictions must never be
        satisfied by a different cat object or by faith alone. This guard is
        intentionally kept in Dialogue as a last line of defense because both
        y_c and t_c are fixed objects, not randomly selected cats.
        """
        cats = dialogue_block.get("cats", {})
        for abbrev, anchor in (("y_c", self.you), ("t_c", self.cat)):
            block = cats.get(abbrev)
            if not block:
                continue

            if "rank" in block and not self._anchor_rank_matches(anchor, block["rank"]):
                return False

            if "residence" in block:
                residence = block["residence"] or []
                if "any" not in residence:
                    if not anchor.dead:
                        return False
                    expected = {
                        CatGroup.DARK_FOREST_ID: "df",
                        CatGroup.STARCLAN_ID: "sc",
                        CatGroup.UNKNOWN_RESIDENCE_ID: "ur",
                    }.get(anchor.status.group_ID)
                    if expected and expected not in residence:
                        return False

        return True

    def _player_state_matches(self, dialogue_block):
        """Match explicit MC state restrictions without blocking generic dialogue."""
        y_block = dialogue_block.get("cats", {}).get("y_c", {})
        residence = y_block.get("residence", [])
        if not residence or "any" in residence:
            return True

        afterlife_tags = {"df", "sc", "ur"}
        if self.you.dead:
            expected = {
                CatGroup.DARK_FOREST_ID: "df",
                CatGroup.STARCLAN_ID: "sc",
                CatGroup.UNKNOWN_RESIDENCE_ID: "ur",
            }.get(self.you.status.group_ID)

            if expected and any(tag in residence for tag in afterlife_tags):
                return expected in residence
            return True

        if any(tag in residence for tag in afterlife_tags):
            return False
        return True

    def _player_standing_matches(self, dialogue_block):
        """Return whether a dialogue block matches the MC's current standing.

        Standing restrictions are independent of the afterlife state handled by
        ``_player_state_matches``.  A shunned-only block must never be shown to
        an unshunned player, while mixed ``member``/``shunned`` entries remain
        valid for either intended state.
        """
        y_block = dialogue_block.get("cats", {}).get("y_c", {})
        standing = y_block.get("standing")
        if not standing:
            return True

        player_group = self.you.status.group_ID
        player_shunned = self.you.status.is_shunned(player_group)

        if player_shunned:
            return "shunned" in standing
        return "shunned" not in standing or "member" in standing

    def choose_dialogue(self, possible_dialogue, flirt=False):
        """
        Makes a final selection.
        Returns the key and the dict object.
        """
        possible_dialogue = self.filter_dialogue(possible_dialogue, flirt)

        # Never bypass dialogue restrictions by falling back to an unfiltered
        # resource.  A failed restrictive selection must remain restrictive;
        # otherwise role-specific dialogue can leak back in through general.json.
        if not possible_dialogue:
            fallback = load_lang_resource("lifegen_talk/general.json")
            possible_dialogue = self.filter_dialogue(fallback, flirt)

        possible_dialogue_keys = list(possible_dialogue.keys())

        # Avoid immediately repeating dialogue when there are enough options.
        # The old implementation only removed repeated keys from a temporary
        # list; the actual selection loop still iterated over the full dict.
        # Build the candidate pool once so the repeat-avoidance rule actually
        # affects the dialogue that can be selected.
        if len(possible_dialogue_keys) > 2:
            filtered_keys = [
                key
                for key in possible_dialogue_keys
                if key not in game.clan.talks or key == self.debug
            ]
            if filtered_keys:
                possible_dialogue = {
                    key: possible_dialogue[key] for key in filtered_keys
                }
                possible_dialogue_keys = filtered_keys

        debug_valid = False
        chosen_key = None
        chosen_cat_dict = {}
        if self.debug:
            if constants.CONFIG["lifegen"]["debug"]["debug_dialogue_override_filtering"]:
                print(f"Debug: Dialogue set to {self.debug} with overridden filtering.")
                chosen_key = self.debug
                
                # assembling a new "cats" block with empty constraints for purely random cats
                debugged_cats_block = {}
                for cat in possible_dialogue[chosen_key]["cats"]:
                    debugged_cats_block[cat] = {}

                # pick cats
                chosen_cat_dict = choose_random_cats(
                    cats_block=debugged_cats_block,
                    rel_block=[],
                    your_cat=self.you,
                    the_cat=self.cat,
                    cat_dict=self.cat_dict
                )
                debug_valid = True
            elif self.debug in possible_dialogue_keys:
                print(f"Debug: Dialogue set to {self.debug}")
                chosen_key = self.debug

                chosen_cat_dict = choose_random_cats(
                    cats_block=possible_dialogue[chosen_key]['cats'],
                    rel_block=(
                        possible_dialogue[chosen_key]['relationships']
                        if "relationships" in possible_dialogue[chosen_key]
                        else []
                        ),
                    your_cat=self.you,
                    the_cat=self.cat,
                    cat_dict=self.cat_dict
                )
                if chosen_cat_dict:
                    debug_valid = True

            if debug_valid:
                self._populate_cat_dict(chosen_key, chosen_cat_dict)

        if not debug_valid:
            # if the debug dialogue failed OR debug isnt set at all
            # so, normal dialogue
            if self.debug:
                print(
                    f"Debugged Dialogue ID ({self.debug}) is not in possible dialogue options." +
                    " Set debug_dialogue_override_filtering to true to override filtering."
                    )
                # Validate cat constraints first, then choose from the valid
            # dialogue using the dialogue frequency/weight. This prevents a
            # generic valid line from winning merely because it appeared first
            # after shuffling.
            valid_dialogue = []
            for key, dialogue_block in possible_dialogue.items():
                if not self._dialogue_anchors_match(dialogue_block):
                    continue
                if not self._player_state_matches(dialogue_block):
                    continue
                if not self._player_standing_matches(dialogue_block):
                    continue
                chosen_cat_dict = choose_random_cats(
                    cats_block=dialogue_block['cats'],
                    rel_block=dialogue_block['relationships'] if "relationships" in dialogue_block else [],
                    your_cat=self.you,
                    the_cat=self.cat,
                    cat_dict=self.cat_dict
                )
                if not chosen_cat_dict:
                    continue

                weight = dialogue_block.get("frequency", 1)
                if not isinstance(weight, (int, float)) or weight <= 0:
                    weight = 1

                # Specific dialogue should be favored over completely generic
                # dialogue, matching the intent of the LifeGen selector.
                for field in ("relationships", "season", "biome", "camp", "tags"):
                    if field in dialogue_block and dialogue_block[field]:
                        weight += 1
                if "focus" in dialogue_block or "connected" in dialogue_block:
                    weight += 3

                valid_dialogue.append((key, chosen_cat_dict, weight))

            if valid_dialogue:
                # A dead MC talking to a living cat is a distinct dialogue
                # state, not a preference.  If the target is alive, ordinary
                # living-to-living dialogue must never be selected: it makes the
                # living target behave as though the MC were still alive.
                # Require an explicit y_c afterlife residence matching the MC.
                # This still allows role/relationship/condition filters to
                # narrow the afterlife-specific pool further.
                if self.you.dead and self.cat is not None and not self.cat.dead:
                    expected = {
                        CatGroup.DARK_FOREST_ID: "df",
                        CatGroup.STARCLAN_ID: "sc",
                        CatGroup.UNKNOWN_RESIDENCE_ID: "ur",
                    }.get(self.you.status.group_ID)
                    if expected:
                        afterlife_dialogue = [
                            item for item in valid_dialogue
                            if expected in (
                                possible_dialogue[item[0]]
                                .get("cats", {})
                                .get("y_c", {})
                                .get("residence", [])
                            )
                        ]
                        # Do not fall back to normal living dialogue. If no
                        # afterlife-specific line survived the other filters,
                        # the selector should report no valid dialogue rather
                        # than pretending this is an ordinary conversation.
                        valid_dialogue = afterlife_dialogue
                elif self.you.dead:
                    # Dead-to-dead conversations already use the existing
                    # afterlife preference behavior, since the target's own
                    # residence can be part of the dialogue restriction.
                    expected = {
                        CatGroup.DARK_FOREST_ID: "df",
                        CatGroup.STARCLAN_ID: "sc",
                        CatGroup.UNKNOWN_RESIDENCE_ID: "ur",
                    }.get(self.you.status.group_ID)
                    if expected:
                        afterlife_dialogue = [
                            item for item in valid_dialogue
                            if expected in (
                                possible_dialogue[item[0]]
                                .get("cats", {})
                                .get("y_c", {})
                                .get("residence", [])
                            )
                        ]
                        if afterlife_dialogue:
                            valid_dialogue = afterlife_dialogue

                # When the player is shunned, use shunned-aware dialogue as the
                # active pool whenever one exists. Generic dialogue remains a
                # fallback only when the current pool has no shunned-specific
                # lines.
                if self.you.status.is_shunned(self.you.status.group_ID):
                    shunned_dialogue = [
                        item for item in valid_dialogue
                        if "shunned" in (
                            possible_dialogue[item[0]]
                            .get("cats", {})
                            .get("y_c", {})
                            .get("standing", [])
                        )
                    ]
                    if shunned_dialogue:
                        valid_dialogue = shunned_dialogue

                # The afterlife-state filter above can legitimately empty the
                # pool after the initial validation pass.  Do not call
                # random.choices() on an empty list; let the safe fallback below
                # handle that case instead.
                if valid_dialogue:
                    keys = [item[0] for item in valid_dialogue]
                    weights = [item[2] for item in valid_dialogue]
                    chosen_key = random.choices(keys, weights=weights, k=1)[0]
                    chosen_cat_dict = next(
                        item[1] for item in valid_dialogue if item[0] == chosen_key
                    )
                    self._populate_cat_dict(chosen_key, chosen_cat_dict)
            if not chosen_key:
                # Never fall back to ordinary living dialogue when a dead MC is
                # speaking to a living cat.  That fallback was the final leak:
                # all of the state filters could correctly reject normal lines,
                # only for the selector to replace the result with general.json.
                # A dead-to-living conversation must remain in the afterlife
                # dialogue domain.
                if self.you.dead and self.cat is not None and not self.cat.dead:
                    chosen_key = None
                    self.cat_dict = {}
                    return chosen_key, {
                        "intro": [
                            "[Your ghostly form flickers in the shadows, a reminder that you no longer belong to the living world.]"
                        ]
                    }

                # none possible within the attempt range :(
                possible_dialogue = load_lang_resource("lifegen_talk/general.json")
                chosen_key = "general"

        if chosen_key != "general":
            self.cat_dict = self.dialogue_cat_dict[chosen_key]
            game.clan.talks.append(chosen_key)
        else:
            self.cat_dict = {
                "t_c": self.cat,
                "y_c": self.you
            }

        return chosen_key, possible_dialogue[chosen_key]


    # ---------------------------------------------------------------------- #
    #                                HELPERS                                 #
    # ---------------------------------------------------------------------- #

    def _populate_cat_dict(self, key, possible_cats_dict):
        self.dialogue_cat_dict[key] = possible_cats_dict
    
    def get_flirt_success(self):
        if self.you.ID not in self.cat.relationships:
            return False
        if self.cat.relationships[self.you.ID].romance < 20:
            return False
        return True

    # ---------------------------------------------------------------------- #
    #                            SCENE EFFECTS                               #
    # ---------------------------------------------------------------------- #

    def handle_scene_effects(self, current_scene, dialogue_object, cat_dict):
        """
        Handles scene effects such as accessories, relationship changes, and more.
        """
        if f"{current_scene}_scene_effects" not in dialogue_object:
            return
        scene_effects = dialogue_object[f"{current_scene}_scene_effects"]

        inventory_block = scene_effects["inventory"] if "inventory" in scene_effects else {}
        relationship_block = scene_effects["relationships"] if "relationships" in scene_effects else {}
        dark_forest_block = scene_effects["dark_forest"] if "dark_forest" in scene_effects else {}

        # inventory
        # try:
        if inventory_block:
            for cat_abbrev in inventory_block["cats_to"]:
                cat_to_object = cat_dict[cat_abbrev] if cat_abbrev in cat_dict else None
                if not cat_to_object:
                    return
                if inventory_block["addition"] == "choice":
                    chosen_accessory = random.choice(inventory_block["accessory"])
                    if chosen_accessory in Pelt.lifegen_acc_categories:
                        cat_to_object.pelt.inventory.append(random.choice(Pelt.lifegen_acc_categories[chosen_accessory]))
                    else:
                        cat_to_object.pelt.inventory.append(random.choice(chosen_accessory))
                elif inventory_block["addition"] == "all":
                    for acc in inventory_block["accessory"]:
                        if acc in Pelt.lifegen_acc_categories:
                            cat_to_object.pelt.inventory.append(random.choice(Pelt.lifegen_acc_categories[acc]))
                        else:
                            cat_to_object.pelt.inventory.append(acc)

        if relationship_block:
            unpack_rel_block(Cat, relationship_block, self, dialogue_dict=cat_dict)
        
        if dark_forest_block:
            if "join" in dark_forest_block:
                for abbrev in dark_forest_block["join"]:
                    cat_dict[abbrev].join_df()
            if "leave" in dark_forest_block:
                for abbrev in dark_forest_block["leave"]:
                    cat_dict[abbrev].leave_df()
                    
        # except Exception as e:
        #     print("ERROR with dialogue scene effects:", e)
        #     return
