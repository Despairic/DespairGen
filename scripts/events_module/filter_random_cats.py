import random

from scripts.game_structure import game
from scripts.cat.enums import CatGroup, CatRank, CatAge
from scripts.cat.cats import Cat, BACKSTORIES
from scripts.lifegen_utility import get_cluster
from scripts.clan_package.settings import get_clan_setting

# pylint: disable=consider-using-dict-items

# LIFEGEN FILE!
# this script deals with filtering the "cats" blocks used in dialogue, lg events, and lg patrols.

possible_cats_dict = {}

def choose_random_cats(
        cats_block: dict={},
        rel_block: list=[],
        your_cat: Cat=None,
        the_cat: Cat=None,
        cat_dict={},
        key=""
        ):
    """
    Selects random cats for LG stuff!
    :param block: A dictionary containing content to be filtered. This is the "cats" block, not its parent.
    :param block: A dictionary containing relationships to be filtered for. This is the "relationships" block, not its parent.
    :param your_cat: Cat object for your cat.
    :param the_cat: Cat object for the talking cat. Outside of dialogue, this is None.
    :param cat_dict: Dict containing existing abbrevs and Cat objects as key-value pairs.
    :param key: Optional content key to pass for debugging.

    """
    # Keep this cache local to a single selection. The previous module-level
    # dictionary could retain candidate lists from earlier conversations and
    # made every dialogue check carry stale state.
    possible_cats_dict = {}
    chosen_cat_dict = {}
    abbrevs = []

    # Do not scan the entire Clan for the two fixed dialogue anchors.
    # y_c and t_c are already known objects, so validating all cats for them
    # was needlessly expensive and was the main source of dialogue-opening
    # latency in large Clans. Random abbreviations (r_c, etc.) still use the
    # complete cat list exactly as before.
    all_cats = Cat.all_cats_list

    # Fast path for ordinary dialogue blocks with random cats but no
    # relationship constraints. The old implementation built a full list of
    # every eligible Clan cat for each r_c entry. With thousands of dialogue
    # blocks, that could mean millions of repeated filter checks before a
    # single conversation appeared. Rejection sampling picks a uniformly
    # random eligible cat without scanning the whole Clan in the common case.
    random_abbrevs = []
    if cats_block:
        random_abbrevs = [
            abbrev for abbrev in cats_block
            if abbrev not in ("y_c", "t_c") and abbrev not in cat_dict
        ]
        # The fast path is safe only after the fixed dialogue anchors have
        # passed every filter.  Previously it jumped straight to random r_c
        # selection whenever an entry contained r_c, completely skipping the
        # rank/standing/faith/etc. checks for y_c and t_c.  That made
        # role-exclusive dialogue (e.g. medicine-cat-only lines) leak to
        # warriors and other incompatible players.
        fixed_anchor_valid = True
        for anchor, anchor_cat in (("y_c", your_cat), ("t_c", the_cat)):
            if anchor in cats_block:
                if anchor_cat is None:
                    fixed_anchor_valid = False
                    break
                if not _validate_cat(
                    anchor,
                    cats_block,
                    [anchor_cat],
                    your_cat,
                    the_cat
                ):
                    fixed_anchor_valid = False
                    break

        if (
            fixed_anchor_valid
            and not rel_block
            and random_abbrevs
            and all(abbrev.startswith("r_c:") for abbrev in random_abbrevs)
        ):
            return _choose_random_cats_fast(
                cats_block, random_abbrevs, your_cat, the_cat, cat_dict, all_cats
            )

    if cats_block:
        # Avoid mutating the dialogue resource in-place when a missing y_c is
        # supplied by the selector.
        cats_block = dict(cats_block)
        if "y_c" not in cats_block:
            cats_block["y_c"] = {}

        for abbrev in cats_block:
            abbrevs.append(abbrev)
            if abbrev == "y_c":
                candidates = [your_cat] if your_cat is not None else []
            elif abbrev == "t_c":
                candidates = [the_cat] if the_cat is not None else []
            else:
                candidates = all_cats

            possible_cats_dict[abbrev] = _validate_cat(
                abbrev,
                cats_block,
                candidates,
                your_cat,
                the_cat
                )
            if not possible_cats_dict[abbrev]:
                return {}

    for abbrev, cat_object in cat_dict.items():
        if abbrev not in possible_cats_dict:
            possible_cats_dict[abbrev] = [cat_object]

    # filter rel uses all abbrevs to make choices based on relationships
    # chosen cat dict is the selected cats! one cat object per abbrev!
    chosen_cat_dict = __filter_relationships(
        abbrevs,
        rel_block,
        possible_cats_dict,
        your_cat,
        the_cat,
        cat_dict
        )
    # except Exception as e:
    #     print("WARNING: Error with filtering for", key)
    #     print(e)
    return chosen_cat_dict

def _choose_random_cats_fast(cats_block, random_abbrevs, your_cat, the_cat, cat_dict, all_cats):
    """Fast-path random-cat selection for dialogue without relationships.

    Avoids constructing and repeatedly mutating a full Clan-sized candidate list
    for every dialogue block. The common case uses random index sampling; the
    exact filter remains as a fallback for restrictive dialogue conditions.
    """
    chosen = {"y_c": your_cat, "t_c": the_cat}
    chosen.update(cat_dict)
    selected_ids = {
        cat.ID for cat in (your_cat, the_cat, *cat_dict.values()) if cat is not None
    }
    cat_count = len(all_cats)

    for abbrev in random_abbrevs:
        block = {abbrev: cats_block[abbrev]}
        found = None

        # Most dialogue restrictions are common. Sample directly from the master
        # list instead of first building a new list containing nearly every cat.
        attempts = min(64, cat_count)
        for _ in range(attempts):
            if cat_count == 0:
                break
            candidate = all_cats[random.randrange(cat_count)]
            if candidate.ID in selected_ids:
                continue
            if _validate_cat(abbrev, block, [candidate], your_cat, the_cat):
                found = candidate
                break

        # Exact fallback preserves correctness for rare/restrictive conditions.
        if found is None:
            candidates = [cat for cat in all_cats if cat.ID not in selected_ids]
            valid = _validate_cat(abbrev, block, candidates, your_cat, the_cat)
            if not valid:
                return {}
            found = random.choice(valid)

        chosen[abbrev] = found
        selected_ids.add(found.ID)

    return chosen


def _validate_cat(abbrev, cat_block, possible_cats, your_cat, the_cat):
    """
    Validates each cat block.
    Helper functions will narrow down the possible cat options.
    For r_c, a final choice is made at the end.
    For t_c and y_c, if the_cat or your_cat are not in the possible cat options,
    the dialogue is filtered out.
    """
    new_possible_cats = []

    # filtering functions!
    for cat in possible_cats:
        if not __filter_dead(
            cat_block[abbrev],
            cat,
            allow_dead_player=(abbrev == "y_c" and your_cat is not None and your_cat.dead and the_cat is not None and not the_cat.dead)
        ):
            continue
        if not __filter_age(cat_block[abbrev], cat, the_cat if abbrev == "y_c" else your_cat):
            continue
        if not __filter_rank(cat_block[abbrev], cat):
            continue

        if not __filter_group(cat_block[abbrev], cat, your_cat, the_cat):
            continue
        if not __filter_standing(cat_block[abbrev], cat, your_cat):
            continue

        if not __filter_skill(cat_block[abbrev], cat):
            continue
        if not __filter_cluster(cat_block[abbrev], cat):
            continue
        if not __filter_backstory(cat_block[abbrev], cat):
            continue
        if not __filter_faith(cat_block[abbrev], cat):
            continue

        if not __filter_conditions(cat_block[abbrev], cat):
            continue

        if "focus_cat" in cat_block[abbrev]:
            if cat_block[abbrev]["focus_cat"] and cat.ID != game.clan.focus_cat:
                continue
            elif not cat_block[abbrev]["focus_cat"] and cat.ID == game.clan.focus_cat:
                continue

        new_possible_cats.append(cat)

    if abbrev == "t_c" and the_cat not in new_possible_cats:
        return []
    if abbrev == "y_c" and your_cat not in new_possible_cats:
        return []

    possible_cat_dict = {}
    possible_cat_dict[abbrev] = new_possible_cats

    return new_possible_cats

    # ---------------------------------------------------------------------- #
    #                          CAT FILTERING FUNCTIONS                       #
    # ---------------------------------------------------------------------- #

def __filter_dead(abbrev_block, cat, allow_dead_player=False):
    # LifeGen intentionally allows a dead MC to initiate dialogue with a living
    # cat.  This is a compatibility rule for the player's own y_c only; it does
    # not make arbitrary dead cats eligible for living-cat dialogue.  Explicit
    # residence restrictions still apply below, so StarClan/DF-specific lines
    # cannot leak across afterlife boundaries.
    if allow_dead_player and cat.dead:
        if "min_max_dead_moons" in abbrev_block:
            if (
                abbrev_block["min_max_dead_moons"][0] > cat.dead_for or
                abbrev_block["min_max_dead_moons"][1] < cat.dead_for
            ):
                return False

        if "residence" in abbrev_block and "any" not in abbrev_block["residence"]:
            residence = abbrev_block["residence"]
            if (
                cat.status.group_ID == CatGroup.DARK_FOREST_ID and "df" not in residence
            ) or (
                cat.status.group_ID == CatGroup.STARCLAN_ID and "sc" not in residence
            ) or (
                cat.status.group_ID == CatGroup.UNKNOWN_RESIDENCE_ID and "ur" not in residence
            ):
                return False
        return True

    if "min_max_dead_moons" in abbrev_block:
        if (
            abbrev_block["min_max_dead_moons"][0] > cat.dead_for or
            abbrev_block["min_max_dead_moons"][1] < cat.dead_for
        ):
            return False
    if "residence" in abbrev_block:
        if not cat.dead:
            return False
        else:
            if "any" not in abbrev_block["residence"]:
                if (
                    "df" not in abbrev_block["residence"] and
                    cat.status.group_ID == CatGroup.DARK_FOREST_ID
                    ):
                    return False
                elif (
                    "sc" not in abbrev_block["residence"] and
                    cat.status.group_ID == CatGroup.STARCLAN_ID
                    ):
                    return False
                elif (
                    "ur" not in abbrev_block["residence"] and
                    cat.status.group_ID == CatGroup.UNKNOWN_RESIDENCE_ID
                    ):
                    return False
    else:
        if cat.dead:
            return False
    return True

def __filter_group(abbrev_block, cat, your_cat, the_cat=None):
    # LifeGen allowed a dead player to converse with a living cat. In the
    # current dialogue schema, the default group filter would reject that
    # living target because the player's afterlife group differs from the
    # Clan group. Preserve the old behavior only for the fixed t_c target;
    # other LifeGen systems still use the normal group filtering.
    if (
        the_cat is not None and
        cat == the_cat and
        your_cat is not None and
        your_cat.dead and
        not the_cat.dead and
        "group" not in abbrev_block and
        "residence" not in abbrev_block
    ):
        # The normal group check would reject a living Clan cat because the
        # dead MC's group is StarClan/DF.  Only bypass that implicit check;
        # explicit group/residence restrictions remain authoritative.
        return True

    if "group" in abbrev_block:
        if (
            (
                cat.status.group and
                cat.status.group not in abbrev_block["group"]
            ) or
            (
                not cat.status.group and
                "none" not in abbrev_block["group"]
            ) or
            (
                cat.status.is_other_clancat and
                "other_clan" not in abbrev_block["group"]
            ) or
            (
                f"not_{cat.status.group}" in abbrev_block["group"]
            ) or 
            (
                f"-{cat.status.group}" in abbrev_block["group"]
            ) or 
            (
                "your_group" in abbrev_block["group"] and
                not cat.status.group == your_cat.status.group
            )
        ):
            return False
    else:
        if "residence" not in abbrev_block and cat.status.group != your_cat.status.group:
            return False
    return True

def __filter_standing(abbrev_block, cat, your_cat):
    """Filter a cat by their standing with the player's current group.

    Shunned is a real dialogue state, not a probabilistic modifier.  Dialogue
    blocks that explicitly require a standing must match that standing, while
    blocks without a standing restriction remain available to the normal
    dialogue selector.
    """
    if "standing" not in abbrev_block:
        return True

    standing_found = False
    standing_dict = {
        "member": cat.status.is_member(your_cat.status.group_ID),
        "lost": cat.status.is_lost(your_cat.status.group_ID),
        "exiled": cat.status.is_exiled(your_cat.status.group_ID),
        "shunned": cat.status.is_shunned(your_cat.status.group_ID),
        "daylight": cat.status.is_daylight_warrior(your_cat.status.group_ID),
        "forgiven": cat.status.is_forgiven(),
        "near": cat.status.is_near(your_cat.status.group_ID),
        "outsider": cat.status.is_outsider
    }
    for tag in abbrev_block["standing"]:
        if tag in standing_dict and standing_dict[tag]:
            standing_found = True
            break
    if not standing_found:
        return False

    return True

def __filter_age(abbrev_block, cat, anchor=None):
    if "age" not in abbrev_block:
        return True

    age_block = abbrev_block["age"]

    if f"not_{cat.age}" in age_block:
        return False
    if "not_kitten" in age_block and cat.age == CatAge.NEWBORN:
        return False
    if f"-{cat.age}" in age_block:
        return False

    positive_tags = [
        tag for tag in age_block
        if not (isinstance(tag, str) and (tag.startswith("not_") or tag.startswith("-")))
    ]
    if not positive_tags:
        return True

    # exact age-stage match
    if cat.age in age_block:
        return True

    # relative-age keywords, compared by life stage against the other cat in the
    # dialogue (the "anchor"): in a t_c/r_c block the anchor is y_c, in a y_c block
    # it's t_c. Requires an anchor, so these only work in dialogue.
    if anchor is not None and (
        "older" in age_block or "younger" in age_block or "sameage" in age_block
    ):
        age_order = list(CatAge)
        try:
            cat_idx = age_order.index(cat.age)
            anchor_idx = age_order.index(anchor.age)
        except ValueError:
            return False
        if "older" in age_block and cat_idx > anchor_idx:
            return True
        if "younger" in age_block and cat_idx < anchor_idx:
            return True
        if "sameage" in age_block and cat_idx == anchor_idx:
            return True

    return False

def __filter_rank(abbrev_block, cat):
    """Filter a cat against the dialogue ``rank`` block.

    Rank blocks can contain more than one kind of restriction.  In particular,
    ``df_trainee`` / ``not_df_trainee`` and ``guide`` are *additional role
    constraints*, not replacements for the ordinary rank check.  The previous
    implementation used an ``elif`` chain, so a special role token could skip
    the actual rank test.  That allowed dialogue such as ``["warrior",
    "df_trainee"]`` to match any DF trainee regardless of rank.

    Positive ordinary ranks are alternatives to one another (OR), while all
    special/negative constraints are cumulative (AND).
    """
    if "rank" not in abbrev_block:
        return True

    rank_block = abbrev_block["rank"] or []
    raw_rank = getattr(cat.status.rank, "value", str(cat.status.rank))
    raw_rank = str(raw_rank)
    normalized_rank = raw_rank.replace(" ", "_")

    # Explicit negative rank constraints always win.
    if (
        f"not_{raw_rank}" in rank_block
        or f"not_{normalized_rank}" in rank_block
        or f"-{raw_rank}" in rank_block
        or f"-{normalized_rank}" in rank_block
    ):
        return False

    # Special role constraints are independent of the ordinary rank list.
    if "df_trainee" in rank_block and not cat.joined_df:
        return False
    if "not_df_trainee" in rank_block and cat.joined_df:
        return False
    if "guide" in rank_block and cat not in (game.clan.instructor, game.clan.demon):
        return False

    # ``any`` means that there is no positive ordinary-rank restriction.
    # Special constraints above still apply.
    if "any" in rank_block:
        return True

    special_tokens = {"df_trainee", "not_df_trainee", "guide"}
    positive_ranks = [
        tag for tag in rank_block
        if isinstance(tag, str)
        and not tag.startswith("not_")
        and not tag.startswith("-")
        and tag not in special_tokens
    ]

    # A block containing only special constraints has already been fully
    # validated above.
    if not positive_ranks:
        return True

    # Ordinary ranks are alternatives: at least one must match.
    return raw_rank in positive_ranks or normalized_rank in positive_ranks

def __filter_skill(abbrev_block, cat):
    if "skill" not in abbrev_block:
        return True
    skill_met = False
    # A skill requirement is NEGATIVE (the cat must NOT have the skill) if it uses
    # tier -1 (e.g. "OMEN,-1") or a leading "-" on the path (e.g. "-OMEN,0").
    # Positive requirements need one match; every negative requirement must be met.
    # Negative and positive tags can be combined, e.g. ["LORE,1", "OMEN,-1"].
    pos_skills = 0
    neg_skills = 0
    neg_skills_met = 0
    for tag in abbrev_block["skill"]:
        parts = tag.split(",")
        path = parts[0]
        negative = False
        if path.startswith("-"):
            path = path[1:]
            negative = True
        try:
            tier = int(parts[1]) if len(parts) > 1 else 0
        except ValueError:
            print(f"WARNING: Invalid skill tag ({tag})")
            continue
        if tier == -1:
            negative = True

        # negatives are checked against meets_skill_requirement(path, -1),
        # which returns True when the cat lacks the skill
        try:
            meets = cat.skills.meets_skill_requirement(path, -1 if negative else tier)
        except KeyError:
            print(f"WARNING: Invalid skill path in tag ({tag})")
            continue

        if negative:
            neg_skills += 1
            if meets:
                neg_skills_met += 1
        else:
            pos_skills += 1
            if meets:
                skill_met = True

    # only require a positive match if positive skills were actually requested
    if pos_skills > 0 and not skill_met:
        return False
    if neg_skills > 0 and neg_skills != neg_skills_met:
        return False
    return True

def __filter_cluster(abbrev_block, cat):
    if "cluster" not in abbrev_block:
        return True
    cluster1, cluster2 = get_cluster(cat.personality.trait)
    if (
        cluster1 not in abbrev_block["cluster"] and
        cluster2 not in abbrev_block["cluster"] and
        cat.personality.trait not in abbrev_block["cluster"]
    ):
        return False

    return True

def __filter_backstory(abbrev_block, cat):

    if "backstory" not in abbrev_block:
        return True

    backstory_tag_dict = {
        "formerlyaloner": "loner_backstories",
        "formerlyarogue": "rogue_backstories",
        "formerlyakittypet": "kittypet_backstories",
        "half-Clan": "half_clan_backstories",
        "clanborn": "clanborn_backstories",
        "clanfounder": "clan_founder_backstories",
        "guide": "clan_guide_backstories",
        "formerlyanoutsider": "outsider_backstories",
        "outsiderroots": "outsider_roots_backstories",
        "fromanotherclan": "former_clancat_backstories",
        "orphaned": "orphaned_backstories",
        "abandoned": "abandoned_backstories",
        "dead": "dead_cat_backstories",
        "starclan": "starclan_backstories",
        "df": "df_backstories",
        "fromstarclan": "oldstarclan_backstories",
        "ancientspirit": "oldstarclan_backstories"
    }

    backstory_found = False
    for tag in abbrev_block["backstory"]:
        if tag in backstory_tag_dict:
            if cat.backstory in (
                BACKSTORIES["backstory_categories"][backstory_tag_dict[tag]]
                ):
                backstory_found = True
                break
            if f"-{cat.backstory}" in (
                BACKSTORIES["backstory_categories"][backstory_tag_dict[tag]]
                ):
                break
        elif tag == cat.backstory:
            backstory_found = True
            break
    if not backstory_found:
        return False

    return True

def __filter_faith(abbrev_block, cat):
    if "min_max_faith" not in abbrev_block:
        return True
    if (
        abbrev_block["min_max_faith"][0] > cat.faith or
        abbrev_block["min_max_faith"][1] < cat.faith
    ):
        return False
    return True

def __filter_conditions(abbrev_block, cat):
    blind_tagged = False
    deaf_tagged = False

    condition_true = False
    reg_tagged = False

    exclusive_conditions = ["pregnant", "grief stricken"]

    condition_block = abbrev_block["condition"] if "condition" in abbrev_block else []
    for tag in condition_block:
        if isinstance(tag, list):
            for condition in tag:
                if (
                    condition not in cat.illnesses and
                    condition not in cat.injuries and
                    condition not in cat.permanent_condition
                ):
                    return False
        elif isinstance(tag, str):
            if ":" in tag:
                attributes = tag.split(":")
                condition = attributes[0]
                born_with = attributes[1]
                exclusive = "false"

                if condition == "blind":
                    blind_tagged = True

                if condition == "deaf":
                    deaf_tagged = True

                if len(attributes) > 2:
                    exclusive = attributes[2]

                # exclusionary
                if condition == "not" and (
                    born_with in cat.illnesses or
                    born_with in cat.injuries or
                    born_with in cat.permanent_condition
                ):
                    return False

                # gen injury/illness
                if condition == "injury" and born_with == "any":
                    if not cat.is_injured():
                        return False
                if condition == "illness" and born_with == "any":
                    if not cat.is_ill():
                        return False
                if condition == "injury" and born_with == "none":
                    if cat.is_injured():
                        return False
                if condition == "illness" and born_with == "none":
                    if cat.is_ill():
                        return False

                # now blind/deaf
                if exclusive == "true" and condition not in cat.permanent_condition:
                    return False

                if born_with == "true":
                    if not (
                        condition in cat.permanent_condition and
                        cat.permanent_condition[condition]["born_with"] is True
                    ):
                        return False
                elif born_with == "false":
                    if not (
                        condition in cat.permanent_condition and
                        cat.permanent_condition[condition]["born_with"] is False
                    ):
                        return False
            else:
                if tag == "hearing":
                    if "deaf" in cat.permanent_condition:
                        deaf_tagged = False
                        return False
                elif tag in exclusive_conditions:
                    if not (
                        tag in cat.permanent_condition or
                        tag in cat.injuries or
                        tag in cat.illnesses
                    ):
                        return False
                else:
                    reg_tagged = True
                    if (
                        tag in cat.permanent_condition or
                        tag in cat.injuries or
                        tag in cat.illnesses
                    ):
                        condition_true = True
                        break

    if "blind" in cat.permanent_condition and not blind_tagged:
        return False
    if (
            (
                "deaf" in cat.permanent_condition and
                cat.permanent_condition["deaf"]["born_with"] is True
            )
            and not deaf_tagged
        ):
        return False

    if reg_tagged and not condition_true:
        return False

    return True

def __filter_relationships(all_abbrevs, rel_block, dict_possible_cats, your_cat, the_cat, cat_dict):
    """
    Chooses final cats based on relationship constraints.
    Not a 'filter' in the same way the other filter functions are. More of a selection tool.
    """
    new_dict = {
        "y_c": your_cat,
        "t_c": the_cat
    }
    for relationship in rel_block:
        for rel_tag in relationship["relationship"]:

            # substitute for a "rel_found" bool, as, with multiple relationships,
            # you cant depend on a true or false.
            # check how many relationships are valid vs. how many we need to be.
            # if these arent the same number at the end, the dialogue will be filtered out.
            valid_rels = 0
            rels_to_check = 0

            # get our initial count before we start looping
            for FROM in relationship["cats_from"]:
                for TO in relationship["cats_to"]:
                    if TO != FROM:
                        rels_to_check += 1

            # begin 500 nested for loops!
            for FROM in relationship["cats_from"]:
                if valid_rels == rels_to_check:
                    continue
                for TO in relationship["cats_to"]:
                    if valid_rels == rels_to_check:
                        continue
                    if TO == FROM:
                        continue

                    # Grab our possible cats depending on the abbrev
                    to_cat_list = dict_possible_cats[TO].copy() if TO in dict_possible_cats else Cat.all_cats_list.copy()
                    from_cat_list = dict_possible_cats[FROM].copy() if FROM in dict_possible_cats else Cat.all_cats_list.copy()

                    # shuffle so the same cat isnt always on top
                    random.shuffle(to_cat_list)
                    random.shuffle(from_cat_list)

                    # if the cat is already here, don't replace them
                    if FROM in new_dict:
                        from_cat_list = [new_dict[FROM]]
                    if TO in new_dict:
                        to_cat_list = [new_dict[TO]]

                    # now begin finding cats
                    match_found = False
                    for from_cat in from_cat_list:
                        if valid_rels == rels_to_check:
                            continue
                        if match_found:
                            continue
                        for to_cat in to_cat_list:
                            if valid_rels == rels_to_check:
                                continue
                            if match_found:
                                continue
                            if not to_cat:
                                print("to_cat in list is None! Report to Jay!")
                                print(to_cat_list)
                                print(rel_block)
                                continue
                            rel_valid = False
                            # this will check is the abbrev and cat are valid.
                            # ensures r_c's are never your_cat or the_cat and similar checks.
                            valid = __check_valid(
                                TO, to_cat, FROM, from_cat, new_dict, your_cat, the_cat, cat_dict
                            )

                            # special logic for the different types of relationship
                            if valid:
                                if rel_tag == "mates":
                                    rel_valid = to_cat.ID in from_cat.mate
                                elif rel_tag == "non-mates":
                                    rel_valid = to_cat.ID not in from_cat.mate
                                elif rel_tag == "ex-mates":
                                    rel_valid = to_cat.ID in from_cat.previous_mates

                                elif rel_tag == "parent/child":
                                    rel_valid = (
                                        from_cat.is_parent(to_cat) or
                                        from_cat.ID in to_cat.adoptive_parents
                                        )
                                elif rel_tag == "child/parent":
                                    rel_valid = (
                                        to_cat.is_parent(from_cat) or
                                        to_cat.ID in from_cat.adoptive_parents
                                        )
                                elif rel_tag == "birth parent/birth child":
                                    rel_valid = from_cat.is_parent(to_cat)
                                elif rel_tag == "birth child/birth parent":
                                    rel_valid = to_cat.is_parent(from_cat)
                                elif rel_tag == "adoptive parent/adoptive child":
                                    rel_valid = from_cat.ID in to_cat.adoptive_parents
                                elif rel_tag == "adoptive child/adoptive parent":
                                    rel_valid = to_cat.ID in from_cat.adoptive_parents
                                elif rel_tag == "sibling's mate/mate's sibling":
                                    rel_valid = to_cat.ID in from_cat.inheritance.get_siblings_mates()
                                elif rel_tag == "mate's sibling/sibling's mate":
                                    rel_valid = from_cat.ID in to_cat.inheritance.get_siblings_mates()
                                elif rel_tag == "cousins":
                                    rel_valid = from_cat.is_cousin(to_cat)
                                elif rel_tag == "adoptive siblings":
                                    rel_valid = from_cat.ID in to_cat.inheritance.get_no_blood_siblings()
                                elif rel_tag == "parent's sibling/sibling's kit":
                                    rel_valid = from_cat.is_uncle_aunt(to_cat)
                                elif rel_tag == "strangers":
                                    rel_valid = from_cat.ID not in to_cat.relationships
                                elif rel_tag == "siblings":
                                    rel_valid = from_cat.is_sibling(to_cat)
                                elif rel_tag == "littermates":
                                    rel_valid = from_cat.is_littermate(to_cat)
                                elif rel_tag == "grandparent/grandchild":
                                    rel_valid = from_cat.is_grandparent(to_cat)
                                elif rel_tag == "grandchild/grandparent":
                                    rel_valid = to_cat.is_grandparent(from_cat)
                                elif rel_tag == "half-siblings":
                                    rel_valid = to_cat.is_half_sibling(from_cat)
                                elif rel_tag == "dead/grieving":
                                    if "grief stricken" not in to_cat.illnesses:
                                        rel_valid = False
                                    elif "grief cat" not in to_cat.illnesses["grief stricken"]:
                                        rel_valid = False
                                    elif to_cat.illnesses["grief stricken"]["grief cat"] != from_cat.ID:
                                        rel_valid = False
                                    else:
                                        rel_valid = True
                                elif rel_tag == "grieving/dead":
                                    if "grief stricken" not in from_cat.illnesses:
                                        rel_valid = False
                                    elif "grief cat" not in from_cat.illnesses["grief stricken"]:
                                        rel_valid = False
                                    elif from_cat.illnesses["grief stricken"]["grief cat"] != to_cat.ID:
                                        rel_valid = False
                                    else:
                                        rel_valid = True
                                elif rel_tag == "related":
                                    rel_valid = from_cat.is_related(to_cat, get_clan_setting("first cousin mates"))
                                elif rel_tag == "non-related":
                                    rel_valid = not from_cat.is_related(to_cat, get_clan_setting("first cousin mates"))

                                elif rel_tag == "victim/murderer":
                                    if not to_cat.history.murder:
                                        rel_valid = False
                                    elif "is_murderer" not in to_cat.history.murder:
                                        rel_valid = False
                                    else:
                                        rel_valid = False
                                        for murder in to_cat.history.murder["is_murderer"]:
                                            if murder["victim"] == from_cat.ID:
                                                rel_valid = True
                                                break

                                elif rel_tag == "murderer/victim":
                                    if not from_cat.history.murder:
                                        rel_valid = False
                                    elif "is_murderer" not in from_cat.history.murder:
                                        rel_valid = False
                                    else:
                                        rel_valid = False
                                        for murder in from_cat.history.murder["is_murderer"]:
                                            if murder["victim"] == to_cat.ID:
                                                rel_valid = True
                                                break
                                elif rel_tag == "non-related":
                                    rel_valid = from_cat.ID in to_cat.get_relatives()

                                elif rel_tag == "app/mentor":
                                    rel_valid = from_cat.ID in to_cat.apprentice
                                elif rel_tag == "mentor/app":
                                    rel_valid = to_cat.ID in from_cat.apprentice
                                elif rel_tag == "df app/df mentor":
                                    rel_valid = from_cat.ID in to_cat.df_apprentices
                                elif rel_tag == "df mentor/df app":
                                    rel_valid = to_cat.ID in from_cat.df_apprentices
                                else:
                                    # now check rel value tags, e.g. "min_like_20" / "max_romance_10"
                                    attributes = rel_tag.split("_")
                                    if "min" not in rel_tag and "max" not in rel_tag:
                                        # not a recognised relationship or rel-value tag:
                                        # warn instead of silently passing
                                        print(f"WARNING: Invalid relationship tag ({rel_tag})")
                                        rel_valid = False
                                    elif to_cat.ID not in from_cat.relationships:
                                        rel_valid = False
                                    else:
                                        rel_valid = True
                                        if "min" in rel_tag:
                                            if attributes[1] == "like":
                                                if (
                                                    from_cat.relationships[to_cat.ID].like <
                                                    int(attributes[2])
                                                    ):
                                                    rel_valid = False
                                            elif attributes[1] == "romance":
                                                if (
                                                    from_cat.relationships[to_cat.ID].romance <
                                                    int(attributes[2])
                                                    ):
                                                    rel_valid = False
                                            elif attributes[1] == "respect":
                                                if (
                                                    from_cat.relationships[to_cat.ID].respect <
                                                    int(attributes[2])
                                                    ):
                                                    rel_valid = False
                                            elif attributes[1] == "trust":
                                                if (
                                                    from_cat.relationships[to_cat.ID].trust <
                                                    int(attributes[2])
                                                    ):
                                                    rel_valid = False
                                            elif attributes[1] == "comfort":
                                                if (
                                                    from_cat.relationships[to_cat.ID].comfort <
                                                    int(attributes[2])
                                                    ):
                                                    rel_valid = False
                                            else:
                                                print(f"WARNING: Invalid relationship tag ({rel_tag})")
                                                rel_valid = False
                                        elif "max" in rel_tag:
                                            if attributes[1] == "like":
                                                if (
                                                    from_cat.relationships[to_cat.ID].like >
                                                    int(attributes[2])
                                                    ):
                                                    rel_valid = False
                                            elif attributes[1] == "romance":
                                                if (
                                                    from_cat.relationships[to_cat.ID].romance >
                                                    int(attributes[2])
                                                    ):
                                                    rel_valid = False
                                            elif attributes[1] == "respect":
                                                if (
                                                    from_cat.relationships[to_cat.ID].respect >
                                                    int(attributes[2])
                                                    ):
                                                    rel_valid = False
                                            elif attributes[1] == "trust":
                                                if (
                                                    from_cat.relationships[to_cat.ID].trust >
                                                    int(attributes[2])
                                                    ):
                                                    rel_valid = False
                                            elif attributes[1] == "comfort":
                                                if (
                                                    from_cat.relationships[to_cat.ID].comfort >
                                                    int(attributes[2])
                                                    ):
                                                    rel_valid = False
                                            else:
                                                print(f"WARNING: Invalid relationship tag ({rel_tag})")
                                                rel_valid = False

                                if rel_valid:
                                    valid_rels += 1
                                    if FROM not in new_dict:
                                        new_dict[FROM] = from_cat
                                        match_found = True
                                    if TO not in new_dict:
                                        new_dict[TO] = to_cat
                                        match_found = True

            if valid_rels != rels_to_check:
                return {}

    for abbrev in all_abbrevs:

        if abbrev not in new_dict and abbrev not in ("t_c", "y_c"):
            options = dict_possible_cats[abbrev]
            for existing_cat in new_dict:
                if new_dict[existing_cat] in options:
                    options.remove(new_dict[existing_cat])
            if not options:
                return {}
            chosen_cat = random.choice(options)
            new_dict[abbrev] = chosen_cat

    return new_dict

    # ---------------------------------------------------------------------- #
    #                                HELPERS                                 #
    # ---------------------------------------------------------------------- #

def __check_valid(to_abbrev, to_cat, from_abbrev, from_cat, new_dict, your_cat, the_cat, cat_dict):
    """
    Checks abbrevs and cats during filtering.
    If y_c and t_c abbrevs are constrained in relationships, they're special cases.
    Reject any cats that aren't you or the_catcat when necessary,
    and don't let them become an r_c.
    """
    valid = True
    if to_abbrev == "y_c" and to_cat != your_cat:
        valid = False
    if to_abbrev == "t_c" and to_cat != the_cat:
        valid = False
    if from_abbrev == "y_c" and from_cat != your_cat:
        valid = False
    if from_abbrev == "t_c" and from_cat != the_cat:
        valid = False

    if to_abbrev != "y_c" and to_cat == your_cat:
        valid = False
    if to_abbrev != "t_c" and to_cat == the_cat:
        valid = False
    if from_abbrev != "y_c" and from_cat == your_cat:
        valid = False
    if from_abbrev != "t_c" and from_cat == the_cat:
        valid = False

    if from_abbrev in cat_dict:
        valid = False
    if to_abbrev in cat_dict:
        valid = False

    for key, value in new_dict.items():
        if value == from_cat and key != from_abbrev:
            valid = False
            break
        if value == to_cat and key != to_abbrev:
            valid = False
            break

    return valid
