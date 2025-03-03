from dataclasses import dataclass
import json
from typing import Any, Dict

from Options import Choice, DeathLink, DefaultOnToggle, ExcludeLocations, NamedRange, OptionDict, \
    OptionGroup, PerGameCommonOptions, Range, Removed, Toggle

## Game Options

### Enemies

class RandomizeEnemiesOption(DefaultOnToggle):
    """Randomize enemy and boss placements."""
    display_name = "Randomize Enemies"


class ScaleEnemiesOption(DefaultOnToggle):
    """Scale randomized enemy stats to match the areas in which they appear.

    Disabling this will tend to make the early game much more difficult and the late game much
    easier.

    This is ignored unless enemies are randomized.
    """
    display_name = "Scale Enemies"

class ReduceHarmlessEnemiesOption(Toggle):
    """Reduce the frequency that "harmless" enemies appear.

    Enable this to add a bit of extra challenge. This severely limits the number of enemies that are
    slow to aggro, slow to attack, and do very little damage that appear in the enemy pool.

    This is ignored unless enemies are randomized.
    """
    display_name = "Reduce Harmless Enemies"


class RandomEnemyPresetOption(OptionDict):
    """The YAML preset for the static enemy randomizer.

    See the static randomizer documentation in `randomizer\\presets\\README.txt` for details.
    Include this as nested YAML. For example:

    .. code-block:: YAML

      random_enemy_preset:
        RemoveSource: Ancient Wyvern; Darkeater Midir
        DontRandomize: Iudex Gundyr
    """
    display_name = "Random Enemy Preset"
    supports_weighting = False
    default = {}

    valid_keys = ["Description", "RecommendFullRandomization", "RecommendNoEnemyProgression",
                  "OopsAll", "Boss", "Miniboss", "Basic", "BuffBasicEnemiesAsBosses",
                  "DontRandomize", "RemoveSource", "Enemies"]

    @classmethod
    def get_option_name(cls, value: Dict[str, Any]) -> str:
        return json.dumps(value)


## Item & Location

class SekiroExcludeLocations(ExcludeLocations):
    """Prevent these locations from having an important item."""
    default = frozenset({})


class ExcludedLocationBehaviorOption(Choice):
    """How to choose items for excluded locations in DS3.

    - **Allow Useful:** Excluded locations can't have progression items, but they can have useful
      items.
    - **Forbid Useful:** Neither progression items nor useful items can be placed in excluded
      locations.
    - **Do Not Randomize:** Excluded locations always contain the same item as in vanilla Sekiro.

    A "progression item" is anything that's required to unlock another location in some game. A
    "useful item" is something each game defines individually, usually items that are quite
    desirable but not strictly necessary.
    """
    display_name = "Excluded Locations Behavior"
    option_allow_useful = 1
    option_forbid_useful = 2
    option_do_not_randomize = 3
    default = 2


class MissableLocationBehaviorOption(Choice):
    """Which items can be placed in locations that can be permanently missed.

    - **Allow Useful:** Missable locations can't have progression items, but they can have useful
      items.
    - **Forbid Useful:** Neither progression items nor useful items can be placed in missable
      locations.
    - **Do Not Randomize:** Missable locations always contain the same item as in vanilla Sekiro.

    A "progression item" is anything that's required to unlock another location in some game. A
    "useful item" is something each game defines individually, usually items that are quite
    desirable but not strictly necessary.
    """
    display_name = "Missable Locations Behavior"
    option_allow_useful = 1
    option_forbid_useful = 2
    option_do_not_randomize = 3
    default = 2


@dataclass
class SekiroOptions(PerGameCommonOptions):
    # Game Options
    death_link: DeathLink
    # Enemies
    randomize_enemies: RandomizeEnemiesOption
    scale_enemies: ScaleEnemiesOption
    reduce_harmless_enemies: ReduceHarmlessEnemiesOption
    random_enemy_preset: RandomEnemyPresetOption

    # Item & Location
    exclude_locations: SekiroExcludeLocations
    excluded_location_behavior: ExcludedLocationBehaviorOption
    missable_location_behavior: MissableLocationBehaviorOption


option_groups = [
    OptionGroup("Enemies", [
        RandomizeEnemiesOption,
        ScaleEnemiesOption,
        ReduceHarmlessEnemiesOption,
        RandomEnemyPresetOption,
    ]),
    OptionGroup("Item & Location Options", [
        ExcludedLocationBehaviorOption,
        MissableLocationBehaviorOption,
    ])
]
