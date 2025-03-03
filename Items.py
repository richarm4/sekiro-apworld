from dataclasses import dataclass
import dataclasses
from enum import IntEnum
from typing import Any, cast, ClassVar, Dict, Generator, List, Optional, Set

from BaseClasses import Item, ItemClassification


class SekiroItemCategory(IntEnum):
    MISC = 0
    UNIQUE = 1
    UPGRADE = 2

@dataclass
class SekiroItemData:
    __item_id: ClassVar[int] = 100000
    """The next item ID to use when creating item data."""

    name: str
    sekiro_code: Optional[int]
    category: SekiroItemCategory

    base_name: Optional[str] = None
    """The name of the individual item, if this is a multi-item group."""

    classification: ItemClassification = ItemClassification.filler
    """How important this item is to the game progression."""

    ap_code: Optional[int] = None
    """The Archipelago ID for this item."""

    is_dlc: bool = False
    """Whether this item is only found in one of the two DLC packs."""

    count: int = 1
    """The number of copies of this item included in each drop."""

    inject: bool = False
    """If this is set, the randomizer will try to inject this item into the game."""

    souls: Optional[int] = None
    """If this is a consumable item that gives souls, the number of souls it gives."""

    filler: bool = False
    """Whether this is a candidate for a filler item to be added to fill out extra locations."""

    skip: bool = False
    """Whether to omit this item from randomization and replace it with filler or unique items."""

    @property
    def unique(self):
        """Whether this item should be unique, appearing only once in the randomizer."""
        return self.category not in {
            SekiroItemCategory.MISC, SekiroItemCategory.UPGRADE,
        }

    def __post_init__(self):
        self.ap_code = self.ap_code or SekiroItemData.__item_id
        if not self.base_name: self.base_name = self.name
        SekiroItemData.__item_id += 1

    def item_groups(self) -> List[str]:
        """The names of item groups this item should appear in.

        This is computed from the properties assigned to this item."""
        names = []
        if self.classification == ItemClassification.progression: names.append("Progression")

        names.append({
            SekiroItemCategory.MISC: "Miscellaneous",
            SekiroItemCategory.UNIQUE: "Unique",
            SekiroItemCategory.UPGRADE: "Upgrade",
        }[self.category])

        return names

    def counts(self, counts: List[int]) -> Generator["SekiroItemData", None, None]:
        """Returns an iterable of copies of this item with the given counts."""
        yield self
        for count in counts:
            yield dataclasses.replace(
                self,
                ap_code = None,
                name = "{} x{}".format(self.base_name, count),
                base_name = self.base_name,
                count = count,
                filler = False, # Don't count multiples as filler by default
            )


class SekiroItem(Item):
    game: str = "Sekiro"
    data: SekiroItemData

    def __init__(
            self,
            player: int,
            data: SekiroItemData,
            classification = None):
        super().__init__(data.name, classification or data.classification, data.ap_code, player)
        self.data = data

    @staticmethod
    def event(name: str, player: int) -> "SekiroItem":
        data = SekiroItemData(name, None, SekiroItemCategory.MISC,
                           skip = True, classification = ItemClassification.progression)
        data.ap_code = None
        return SekiroItem(player, data)


_vanilla_items = [
    # TODO: Actually give real item codes, just threw in random numbers as placeholders

    # Key Items
    
    SekiroItemData("Aromatic Branch", 0x00555420, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Divine Dragon's Tears", 0x00555421, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Father's Bell Charm", 0x00555422, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Gatehouse Key", 0x00555423, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Gun Fort Shrine Key", 0x00555424, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Hidden Temple Key", 0x00555425, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Lotus of the Palace", 0x00555426, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Mibu Breathing Technique", 0x00555427, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Mist Raven's Feathers", 0x00555428, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Mortal Blade", 0x00555429, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Puppeteer Ninjutsu", 0x00555430, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Secret Passage Key", 0x00555431, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Shelter Stone", 0x00555432, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Shinobi Prosthetic", 0x00555433, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),
    SekiroItemData("Young Lord's Bell Charm", 0x00555435, SekiroItemCategory.UNIQUE, classification = ItemClassification.progression),

    # Memories
    SekiroItemData("Memory: Genichiro", 0x00666000, SekiroItemCategory.UNIQUE, classification = ItemClassification.useful),
    SekiroItemData("Memory: Saint Isshin", 0x00666001, SekiroItemCategory.UNIQUE, classification = ItemClassification.useful),
    # Miscellaneous
    SekiroItemData("Gachiin's Sugar", 0x00555436, SekiroItemCategory.MISC, filler = True),
]

item_name_groups: Dict[str, Set] = {
    "Progression": set(),
    "Miscellaneous": set(),
    "Unique": set(),
    "Upgrade": set(),
}


item_descriptions = {
    "Progression": "Items which unlock locations.",
    "Miscellaneous": "Generic stackable items, such as oil, sugars, balloons and so on.",
    "Unique": "Items that are unique per NG cycle, such as the Ceremonial Tanto or prosthetic tools.",
    "Upgrade": "Upgrade items, including gourd seeds and prayer beads.",
}



for item_data in _vanilla_items:
    for group_name in item_data.item_groups():
        item_name_groups[group_name].add(item_data.name)

filler_item_names = [item_data.name for item_data in _vanilla_items if item_data.filler]
item_dictionary = {item_data.name: item_data for item_data in _vanilla_items}
