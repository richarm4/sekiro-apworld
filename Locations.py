from typing import cast, ClassVar, Optional, Dict, List, Set
from dataclasses import dataclass

from BaseClasses import ItemClassification, Location, Region
from .Items import SekiroItemCategory, item_dictionary

# Regions in approximate order of reward, mostly measured by how high-quality the upgrade items are
# in each region.
region_order = [
    
]


@dataclass
class SekiroLocationData:
    __location_id: ClassVar[int] = 100000
    """The next location ID to use when creating location data."""

    name: str
    """The name of this location according to Archipelago.

    This needs to be unique within this world."""

    default_item_name: Optional[str]
    """The name of the item that appears by default in this location.

    If this is None, that indicates that this location is an "event" that's
    automatically considered accessed as soon as it's available. Events are used
    to indicate major game transitions that aren't otherwise gated by items so
    that progression balancing and item smoothing is more accurate for Sekiro.
    """

    ap_code: Optional[int] = None
    """Archipelago's internal ID for this location (also known as its "address")."""

    region_value: int = 0
    """The relative value of items in this location's region.

    This is used to sort locations when placing items like the base game.
    """

    static: Optional[str] = None
    """The key in the static randomizer's Slots table that corresponds to this location.

    By default, the static randomizer chooses its location based on the region and the item name.
    If the item name is unique across the whole game, it can also look it up based on that alone. If
    there are multiple instances of the same item type in the same region, it will assume its order
    (in annotations.txt) matches Archipelago's order.

    In cases where this heuristic doesn't work, such as when Archipelago's region categorization or
    item name disagrees with the static randomizer's, this field is used to provide an explicit
    association instead.
    """

    missable: bool = False
    """Whether this item is possible to permanently lose access to.

    This is also used for items that are *technically* possible to get at any time, but are
    prohibitively difficult without blocking off other checks (items dropped by NPCs on death
    generally fall into this category).

    Missable locations are always marked as excluded, so they will never contain
    progression or useful items.
    """

    npc: bool = False
    """Whether this item is contingent on killing an NPC or following their quest."""

    prominent: bool = False
    """Whether this is one of few particularly prominent places for items to appear.

    This is a small number of locations (boss drops and progression locations)
    intended to be set as priority locations for players who don't want a lot of
    mandatory checks.

    For bosses with multiple drops, only one should be marked prominent.
    """

    progression: bool = False
    """Whether this location normally contains an item that blocks forward progress."""

    boss: bool = False
    """Whether this location is a reward for defeating a full boss."""

    miniboss: bool = False
    """Whether this location is a reward for defeating a miniboss.

    The classification of "miniboss" is a bit fuzzy, but we consider them to be enemies that are
    visually distinctive in their locations, usually bigger than normal enemies, with a guaranteed
    item drop. NPCs are never considered minibosses, and some normal-looking enemies with guaranteed
    drops aren't either (these are instead classified as hidden locations)."""

    drop: bool = False
    """Whether this is an item dropped by a (non-boss) enemy.

    This is automatically set to True if miniboss, mimic, lizard, or hostile_npc is True.
    """

    shop: bool = False
    """Whether this location can appear in an NPC's shop.

    Items which can appear both in the overworld and in a shop
    should still be tagged as shop.
    """

    conditional: bool = False
    """Whether this location is conditional on a progression item.

    This is used to track locations that won't become available until an unknown amount of time into
    the run, and as such shouldn't have "similar to the base game" items placed in them.
    """

    hidden: bool = False
    """Whether this location is particularly tricky to find.

    This is for players without an encyclopedic knowledge of Sekiro.
    """

    @property
    def is_event(self) -> bool:
        """Whether this location represents an event rather than a specific item pickup."""
        return self.default_item_name is None

    def __post_init__(self):
        if not self.is_event:
            self.ap_code = self.ap_code or SekiroLocationData.__location_id
            SekiroLocationData.__location_id += 1
        if self.miniboss: self.drop = True

    def location_groups(self) -> List[str]:
        """The names of location groups this location should appear in.

        This is computed from the properties assigned to this location."""
        names = []
        if self.prominent: names.append("Prominent")
        if self.progression: names.append("Progression")
        if self.boss: names.append("Boss Rewards")
        if self.miniboss: names.append("Miniboss Rewards")
        if self.npc: names.append("Friendly NPC Rewards")
        if self.hidden: names.append("Hidden")

        default_item = item_dictionary[cast(str, self.default_item_name)]
        names.append({
                         SekiroItemCategory.MISC: "Miscellaneous",
                         SekiroItemCategory.UNIQUE: "Unique",
                         SekiroItemCategory.UPGRADE: "Upgrade",
                     }[default_item.category])
        if default_item.classification == ItemClassification.progression:
            names.append("Progression")

        return names


class SekiroLocation(Location):
    game: str = "Sekiro"
    data: SekiroLocationData

    def __init__(
            self,
            player: int,
            data: SekiroLocationData,
            parent: Optional[Region] = None,
            event: bool = False):
        super().__init__(player, data.name, None if event else data.ap_code, parent)
        self.data = data


# Naming conventions:
#
# * The regions in item names should match the physical region where the item is
#   acquired, even if its logical region is different. For example, Irina's
#   inventory appears in the "Undead Settlement" region because she's not
#   accessible until there, but it begins with "FS:" because that's where her
#   items are purchased.
#
# * Avoid using vanilla enemy placements as landmarks, because these are
#   randomized by the enemizer by default. Instead, use generic terms like
#   "mob", "boss", and "miniboss".
#
# * Location descriptions don't need to direct the player to the precise spot.
#   You can assume the player is broadly familiar with Dark Souls III or willing
#   to look at a vanilla guide. Just give a general area to look in or an idea
#   of what quest a check is connected to. Terseness is valuable: try to keep
#   each location description short enough that the whole line doesn't exceed
#   100 characters.
#
# * Use "[name] drop" for items that require killing an NPC who becomes hostile
#   as part of their normal quest, "kill [name]" for items that require killing
#   them even when they aren't hostile, and just "[name]" for items that are
#   naturally available as part of their quest.
location_tables: Dict[str, List[SekiroLocationData]] = {
    "Dilapidated Temple": [ 
        SekiroLocationData("Shinobi Prosthetic - arrive at DT", "Shinobi Prosthetic")     
              ],
    "Ashina Outskirts": [ 
        SekiroLocationData("AO: Young Lord's Bell Charm - speak to Inosuke Nogami's mother", "Young Lord's Bell Charm")
              ],
    "Ashina Outskirts after Central Forces": [ 
              ],
    "Ashina Castle Gate": [ 
              ],
    "Ashina Reservoir": [ 
              ],
    "Ashina Reservoir Ending": [ 
        SekiroLocationData("ARE - Memory: Saint Isshin", "Memory: Saint Isshin")
              ],
    "Ashina Castle": [ 
        SekiroLocationData("AC: Gatehouse Key - dropped by enemy on bridge leading to Abandoned Dungeon entrance", "Gatehouse Key"),
        SekiroLocationData("AC: Memory: Genichiro", "Memory: Genichiro"),
        SekiroLocationData("Gun Fort Shrine Key - speak to Kuro", "Gun Fort Shrine Key")
              ],
    "Ashina Castle after Interior Ministry": [
        SekiroLocationData("DT: Father's Bell Charm - Emma questline", "Father's Bell Charm"),
        SekiroLocationData("ACIM: Aromatic Branch - second AC memory boss", "Aromatic Branch")
              ],
    "Ashina Castle after Central Forces": [ 
        SekiroLocationData("ACCF: Secret Passage Key - speak to Emma", "Secret Passage Key")
              ],
    "Hirata Estate": [ 
       # SekiroLocationData("HE1: Truly Precious Bait - Pot Noble Harunaga quest", "Truly Precious Bait"),
        SekiroLocationData("HE1: Mist Raven's Feathers - down the river from Bamboo Thicket Slope", "Mist Raven's Feathers"),
        SekiroLocationData("HE1: Hidden Temple Key - Owl after Bamboo Thicket Slope", "Hidden Temple Key")
              ],
    "Hirata Estate Second Half": [
    ],
    "Hirata Estate Revisited": [ 
              ],
    "Abandoned Dungeon": [ 
              ],
    "Senpou Temple": [ 
              ],
    "Senpou Temple Grounds": [ 
              ],
    "Senpou Temple Inner Sanctum": [
        SekiroLocationData("STIS: Puppeteer Ninjutsu - STIS memory boss", "Puppeteer Ninjutsu"),
        SekiroLocationData("STIS: Mortal Blade", "Mortal Blade")
              ],
    "Upper Sunken Valley": [ 
              ],
    "Sunken Valley Passage": [ 
        SekiroLocationData("SVP: Lotus of the Palace - after SVP memory boss", "Lotus of the Palace"),
              ],
    "Ashina Depths": [ 
              ],
    "Hidden Forest": [ 
              ],
    "Mibu Village": [ 
        SekiroLocationData("MV: Mibu Breathing Technique - kill MV memory boss", "Mibu Breathing Technique"),
        SekiroLocationData("MV: Shelter Stone - after MV memory boss", "Shelter Stone")
              ],
    "Fountainhead Palace": [ 
        SekiroLocationData("FP: Divine Dragon's Tears", "Divine Dragon's Tears"),
      #  SekiroLocationData("FP: Truly Precious Bait - Pot Noble Koremori quest", "Truly Precious Bait")
              ]
}

for i, region in enumerate(region_order):
    for location in location_tables[region]: location.region_value = i

location_name_groups: Dict[str, Set[str]] = {
    # We could insert these locations automatically with setdefault(), but we set them up explicitly
    # instead so we can choose the ordering.
    "Prominent": set(),
    "Progression": set(),
    "Boss Rewards": set(),
    "Miniboss Rewards": set(),
    "Friendly NPC Rewards": set(),
    "Unique": set(),
    "Healing": set(),
    "Miscellaneous": set(),
    "Hidden": set(),
}

location_descriptions = {
    "Prominent": "A small number of locations that are in very obvious locations. Mostly boss " + \
                 "drops. Ideal for setting as priority locations.",
    "Progression": "Locations that contain items in vanilla which unlock other locations.",
    "Boss Rewards": "Boss drops. Does not include soul transfusions or shop items.",
    "Miniboss Rewards": "Miniboss drops. Only includes enemies considered minibosses by the " + \
                        "enemy randomizer.",
    "Friendly NPC Rewards": "Items given by friendly NPCs as part of their quests or from " + \
                            "non-violent interaction.",
    "Upgrade": "Locations that contain upgrade items in vanilla, including titanite, gems, and " + \
               "Shriving Stones.",
    "Unique": "Locations that contain items in vanilla that are unique per NG cycle, such as " + \
              "scrolls, keys, ashes, and so on. Doesn't cover equipment, spells, or souls.",
    "Healing": "Locations that contain Undead Bone Shards and Estus Shards in vanilla.",
    "Miscellaneous": "Locations that contain generic stackable items in vanilla, such as arrows, " +
                     "firebombs, buffs, and so on.",
    "Hidden": "Locations that are particularly difficult to find, such as behind illusory " + \
              "walls, down hidden drops, and so on. Does not include large locations like Untended " + \
              "Graves or Archdragon Peak.",
}

location_dictionary: Dict[str, SekiroLocationData] = {}
for location_name, location_table in location_tables.items():
    location_dictionary.update({location_data.name: location_data for location_data in location_table})

    for location_data in location_table:
        if not location_data.is_event:
            for group_name in location_data.location_groups():
                location_name_groups[group_name].add(location_data.name)

    # Allow entire locations to be added to location sets.
    if not location_name.endswith(" Shop"):
        location_name_groups[location_name] = set([
            location_data.name for location_data in location_table
            if not location_data.is_event
        ])
