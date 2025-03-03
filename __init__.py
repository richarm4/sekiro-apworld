# world/dark_souls_3/__init__.py
from collections.abc import Sequence
from collections import defaultdict
import json
from logging import warning
from typing import cast, Any, Callable, Dict, Set, List, Optional, TextIO, Union

from BaseClasses import CollectionState, MultiWorld, Region, Location, LocationProgressType, Entrance, Tutorial, ItemClassification

from worlds.AutoWorld import World, WebWorld
from worlds.generic.Rules import CollectionRule, ItemRule, add_rule, add_item_rule

from .Items import SekiroItem, SekiroItemData, filler_item_names, item_descriptions, item_dictionary, item_name_groups
from .Locations import SekiroLocation, SekiroLocationData, location_tables, location_descriptions, location_dictionary, location_name_groups, region_order
from .Options import SekiroOptions, option_groups


class SekiroWeb(WebWorld):
    setup_en = Tutorial(
        "setup",
        "description here",
        "en",
        "setup_en.md",
        "setup/en",
        ["your name here"]
    )
    tutorials = [setup_en]


class SekiroWorld(World):
    """
    Sekiro is a game where you try to parry then die to a giant ape.
    """

    game = "Sekiro"
    options: SekiroOptions
    options_dataclass = SekiroOptions
    web = SekiroWeb()
    base_id = 100000
    required_client_version = (0, 4, 2)
    item_name_to_id = {data.name: data.ap_code for data in item_dictionary.values() if data.ap_code is not None}
    location_name_to_id = {
        location.name: location.ap_code
        for locations in location_tables.values()
        for location in locations
        if location.ap_code is not None
    }
    location_name_groups = location_name_groups
    item_name_groups = item_name_groups
    location_descriptions = location_descriptions
    item_descriptions = item_descriptions

    all_excluded_locations: Set[str] = set()
    """This is the same value as `self.options.exclude_locations.value` initially, but if
    `options.exclude_locations` gets cleared due to `excluded_locations: allow_useful` this still
    holds the old locations so we can ensure they don't get necessary items.
    """

    local_itempool: List[SekiroItem] = []
    """The pool of all items within this particular world. This is a subset of
    `self.multiworld.itempool`."""

    def __init__(self, multiworld: MultiWorld, player: int):
        super().__init__(multiworld, player)
        self.all_excluded_locations = set()

    def generate_early(self) -> None:
        self.created_regions = set()
        self.all_excluded_locations.update(self.options.exclude_locations.value)


    def create_regions(self) -> None:
        # Create Vanilla Regions
        regions: Dict[str, Region] = {"Menu": self.create_region("Menu", {})}
        regions.update({region_name: self.create_region(region_name, location_tables[region_name]) for region_name in [
            "Dilapidated Temple",
            "Ashina Outskirts",
            "Ashina Outskirts after Central Forces",
            "Ashina Castle Gate",
            "Ashina Reservoir",
            "Ashina Reservoir Ending",
            "Ashina Castle",
            "Ashina Castle after Interior Ministry",
            "Ashina Castle after Central Forces",
            "Hirata Estate",
            # We need to split hirata estate first visit to enable shinobi prosthetic randomization not causing a mild logic nightmare
            "Hirata Estate Second Half",
            "Hirata Estate Revisited",
            "Abandoned Dungeon",
            "Senpou Temple",
            "Senpou Temple Grounds",
            "Senpou Temple Inner Sanctum",
            "Upper Sunken Valley",
            "Sunken Valley Passage",
            "Ashina Depths",
            "Hidden Forest",
            "Mibu Village",
            "Fountainhead Palace"
        ]})

        # Connect Regions
        def create_connection(from_region: str, to_region: str):
            connection = Entrance(self.player, f"Go To {to_region}", regions[from_region])
            regions[from_region].exits.append(connection)
            connection.connect(regions[to_region])

        regions["Menu"].exits.append(Entrance(self.player, "New Game", regions["Menu"]))
        self.multiworld.get_entrance("New Game", self.player).connect(regions["Dilapidated Temple"])

        create_connection("Dilapidated Temple", "Ashina Outskirts")
        create_connection("Dilapidated Temple", "Hirata Estate")
        create_connection("Hirata Estate", "Hirata Estate Second Half")
        
        create_connection("Dilapidated Temple", "Hirata Estate Revisited")

        create_connection("Ashina Outskirts", "Ashina Castle Gate")
        
        create_connection("Ashina Castle Gate", "Ashina Castle")
        
        create_connection("Ashina Castle", "Abandoned Dungeon")
        create_connection("Ashina Castle", "Ashina Reservoir")
        create_connection("Ashina Castle", "Upper Sunken Valley")

        create_connection("Senpou Temple", "Ashina Castle after Interior Ministry")
        create_connection("Hirata Estate", "Ashina Castle after Interior Ministry")
        create_connection("Mibu Village", "Ashina Castle after Interior Ministry")
        create_connection("Sunken Valley Passage", "Ashina Castle after Interior Ministry")

        create_connection("Ashina Castle after Interior Ministry", "Fountainhead Palace")

        create_connection("Ashina Castle after Central Forces", "Ashina Reservoir Ending")
        create_connection("Ashina Castle after Central Forces", "Ashina Outskirts after Central Forces")

        create_connection("Upper Sunken Valley", "Sunken Valley Passage")
        create_connection("Ashina Reservoir", "Abandoned Dungeon")
        
        create_connection("Abandoned Dungeon", "Senpou Temple")

        create_connection("Senpou Temple", "Senpou Temple Grounds")
        create_connection("Senpou Temple Grounds", "Senpou Temple Inner Sanctum")
        create_connection("Abandoned Dungeon", "Senpou Temple")
        create_connection("Abandoned Dungeon", "Ashina Depths")
        
        create_connection("Ashina Depths", "Hidden Forest")
        
        create_connection("Hidden Forest", "Mibu Village")

        create_connection("Fountainhead Palace", "Ashina Castle after Central Forces")

    # For each region, add the associated locations retrieved from the corresponding location_table
    def create_region(self, region_name, location_table) -> Region:
        new_region = Region(region_name, self.player, self.multiworld)

        # Use this to un-exclude event locations so the fill doesn't complain about items behind
        # them being unreachable.
        excluded = self.options.exclude_locations.value

        for location in location_table:
            if self._is_location_available(location):
                new_location = SekiroLocation(self.player, location, new_region)
                if (
                    # Exclude missable locations that don't allow useful items
                    location.missable and self.options.missable_location_behavior == "forbid_useful"
                    and not (
                        # Unless they are excluded to a higher degree already
                        location.name in self.all_excluded_locations
                        and self.options.missable_location_behavior < self.options.excluded_location_behavior
                    )
                ):
                    new_location.progress_type = LocationProgressType.EXCLUDED
            else:
                # Replace non-randomized items with events that give the default item
                event_item = (
                    self.create_item(location.default_item_name) if location.default_item_name
                    else SekiroItem.event(location.name, self.player)
                )

                new_location = SekiroLocation(
                    self.player,
                    location,
                    parent = new_region,
                    event = True,
                )
                event_item.code = None
                new_location.place_locked_item(event_item)
                if location.name in excluded:
                    excluded.remove(location.name)
                    # Only remove from all_excluded if excluded does not have priority over missable
                    if not (self.options.missable_location_behavior < self.options.excluded_location_behavior):
                        self.all_excluded_locations.remove(location.name)

            new_region.locations.append(new_location)

        self.multiworld.regions.append(new_region)
        self.created_regions.add(region_name)
        return new_region

    def create_items(self) -> None:
        # Just used to efficiently deduplicate items
        item_set: Set[str] = set()

        # Gather all default items on randomized locations
        self.local_itempool = []
        num_required_extra_items = 0
        for location in cast(List[SekiroLocation], self.multiworld.get_unfilled_locations(self.player)):
            if not self._is_location_available  (location.name):
                raise Exception("Sekiro generation bug: Added an unavailable location.")

            default_item_name = cast(str, location.data.default_item_name)
            item = item_dictionary[default_item_name]
            if item.skip:
                num_required_extra_items += 1
            elif not item.unique:
                self.local_itempool.append(self.create_item(default_item_name))
            else:
                # For unique items, make sure there aren't duplicates in the item set even if there
                # are multiple in-game locations that provide them.
                if default_item_name in item_set:
                    num_required_extra_items += 1
                else:
                    item_set.add(default_item_name)
                    self.local_itempool.append(self.create_item(default_item_name))

        injectables = self._create_injectable_items(num_required_extra_items)
        num_required_extra_items -= len(injectables)
        self.local_itempool.extend(injectables)

        # Extra filler items for locations containing skip items
        self.local_itempool.extend(self.create_item(self.get_filler_item_name()) for _ in range(num_required_extra_items))

        # Add items to itempool
        self.multiworld.itempool += self.local_itempool

    def _create_injectable_items(self, num_required_extra_items: int) -> List[SekiroItem]:
        """Returns a list of items to inject into the multiworld instead of skipped items.

        If there isn't enough room to inject all the necessary progression items
        that are in missable locations by default, this adds them to the
        player's starting inventory.
        """

        all_injectable_items = [
            item for item
            in item_dictionary.values()
            if item.inject
        ]
        injectable_mandatory = [
            item for item in all_injectable_items
            if item.classification == ItemClassification.progression
        ]
        injectable_optional = [
            item for item in all_injectable_items
            if item.classification != ItemClassification.progression
        ]

        number_to_inject = min(num_required_extra_items, len(all_injectable_items))
        items = (
            self.random.sample(
                injectable_mandatory,
                k=min(len(injectable_mandatory), number_to_inject)
            )
            + self.random.sample(
                injectable_optional,
                k=max(0, number_to_inject - len(injectable_mandatory))
            )
        )

        if number_to_inject < len(injectable_mandatory):
            # It's worth considering the possibility of _removing_ unimportant
            # items from the pool to inject these instead rather than just
            # making them part of the starting health back
            for item in injectable_mandatory:
                if item in items: continue
                self.multiworld.push_precollected(self.create_item(item))
                warning(
                    f"Couldn't add \"{item.name}\" to the item pool for " + 
                    f"{self.player_name}. Adding it to the starting " +
                    f"inventory instead."
                )

        return [self.create_item(item) for item in items]

    def create_item(self, item: Union[str, SekiroItemData]) -> SekiroItem:
        data = item if isinstance(item, SekiroItemData) else item_dictionary[item]
        classification = None

        return SekiroItem(self.player, data, classification=classification)

    def _fill_local_item(
        self, name: str,
        regions: List[str],
        additional_condition: Optional[Callable[[SekiroLocationData], bool]] = None,
    ) -> None:
        """Chooses a valid location for the item with the given name and places it there.
        
        This always chooses a local location among the given regions. If additional_condition is
        passed, only locations meeting that condition will be considered.

        If the item could not be placed, it will be added to starting inventory.
        """
        item = next((item for item in self.local_itempool if item.name == name), None)
        if not item: return

        candidate_locations = [
            location for location in (
                self.multiworld.get_location(location.name, self.player)
                for region in regions
                for location in location_tables[region]
                if self._is_location_available(location)
                and not location.missable
                and not location.conditional
                and (not additional_condition or additional_condition(location))
            )
            # We can't use location.progress_type here because it's not set
            # until after `set_rules()` runs.
            if not location.item and location.name not in self.all_excluded_locations
            and location.item_rule(item)
        ]

        self.local_itempool.remove(item)

        if not candidate_locations:
            warning(f"Couldn't place \"{name}\" in a valid location for {self.player_name}. Adding it to starting inventory instead.")
            location = next(
                (location for location in self._get_our_locations() if location.data.default_item_name == item.name),
                None
            )
            if location: self._replace_with_filler(location)
            self.multiworld.push_precollected(self.create_item(name))
            return

        location = self.random.choice(candidate_locations)
        location.place_locked_item(item)

    def _replace_with_filler(self, location: SekiroLocation) -> None:
        """If possible, choose a filler item to replace location's current contents with."""
        if location.locked: return

        # Try 10 filler items. If none of them work, give up and leave it as-is.
        for _ in range(0, 10):
            candidate = self.create_filler()
            if location.item_rule(candidate):
                location.item = candidate
                return

    def get_filler_item_name(self) -> str:
        return self.random.choice(filler_item_names)

    def set_rules(self) -> None:
        randomized_items = {item.name for item in self.local_itempool}

        #self._add_shop_rules()
        #self._add_npc_rules()
        self._add_allow_useful_location_rules()
        
        self._add_entrance_rule("Ashina Outskirts", "Shinobi Prosthetic")
        self._add_entrance_rule("Hirata Estate Second Half", "Shinobi Prosthetic")
        self._add_entrance_rule("Hirata Estate Revisited", "Father's Bell Charm")
        self._add_entrance_rule("Ashina Castle after Interior Ministry", lambda state: ( 
            state.has("Lotus of the Palace", self.player)
            and state.has("Shelter Stone", self.player)
            and state.has("Mortal Blade", self.player)
        ))
        self._add_entrance_rule("Sunken Valley Passage", "Gun Fort Shrine Key")
        self._add_entrance_rule("Fountainhead Palace", "Aromatic Branch")
        self._add_entrance_rule("Ashina Castle after Central Forces", lambda state: self._can_get(state, "FP: Divine Dragon's Tears"))
        self._add_location_rule("FP: Divine Dragon's Tears", "Mibu Breathing Technique")
        self._add_location_rule("ARE: Memory: Saint Isshin", "Secret Passage Key")
        
        self.multiworld.completion_condition[self.player] = lambda state: self._can_get(state, "ARE: Memory: Saint Isshin") and state.has("Divine Dragon's Tears", self.player)

    def _add_shop_rules(self) -> None:
        """Adds rules for items unlocked in shops."""
        return None
#TODO: Implement sekiro shop logic
        """
        shop_unlocks = {
        }
        for (shop, unlocks) in shop_unlocks.items():
            for (key, key_name, items) in unlocks:
                self._add_location_rule(
                    [f"FS: {item} - {shop} for {key_name}" for item in items], key)
"""

    def _add_npc_rules(self) -> None:
        """Adds rules for items accessible via NPC quests.
        We list missable locations here even though they never contain progression items so that the
        game knows what sphere they're in.
        """
        #TODO: Implement sekiro npc logic
        return None

        


    def _add_allow_useful_location_rules(self) -> None:
        """Adds rules for locations that can contain useful but not necessary items.

        If we allow useful items in the excluded locations, we don't want Archipelago's fill
        algorithm to consider them excluded because it never allows useful items there. Instead, we
        manually add item rules to exclude important items.
        """

        all_locations = self._get_our_locations()

        allow_useful_locations = (
            (
                {
                    location.name
                    for location in all_locations
                    if location.name in self.all_excluded_locations
                    and not location.data.missable
                }
                if self.options.excluded_location_behavior < self.options.missable_location_behavior
                else self.all_excluded_locations
            )
            if self.options.excluded_location_behavior == "allow_useful"
            else set()
        ).union(
            {
                location.name
                for location in all_locations
                if location.data.missable
                and not (
                    location.name in self.all_excluded_locations
                    and self.options.missable_location_behavior <
                        self.options.excluded_location_behavior
                )
            }
            if self.options.missable_location_behavior == "allow_useful"
            else set()
        )
        for location in allow_useful_locations:
            self._add_item_rule(
                location,
                lambda item: not item.advancement
            )

        # Prevent the player from prioritizing and "excluding" the same location
        self.options.priority_locations.value -= allow_useful_locations

        if self.options.excluded_location_behavior == "allow_useful":
            self.options.exclude_locations.value.clear()

    def _add_location_rule(self, location: Union[str, List[str]], rule: Union[CollectionRule, str]) -> None:
        """Sets a rule for the given location if it that location is randomized.

        The rule can just be a single item/event name as well as an explicit rule lambda.
        """
        locations = location if isinstance(location, list) else [location]
        for location in locations:

            if not self._is_location_available(location): continue
            if isinstance(rule, str):
                assert item_dictionary[rule].classification == ItemClassification.progression
                rule = lambda state, item=rule: state.has(item, self.player)
            add_rule(self.multiworld.get_location(location, self.player), rule)

    def _add_entrance_rule(self, region: str, rule: Union[CollectionRule, str]) -> None:
        """Sets a rule for the entrance to the given region."""
        assert region in location_tables
        if region not in self.created_regions: return
        if isinstance(rule, str):
            if " -> " not in rule:
                assert item_dictionary[rule].classification == ItemClassification.progression
            rule = lambda state, item=rule: state.has(item, self.player)
        add_rule(self.multiworld.get_entrance("Go To " + region, self.player), rule)

    def _add_item_rule(self, location: str, rule: ItemRule) -> None:
        """Sets a rule for what items are allowed in a given location."""
        if not self._is_location_available(location): return
        add_item_rule(self.multiworld.get_location(location, self.player), rule)

    def _can_go_to(self, state, region) -> bool:
        """Returns whether state can access the given region name."""
        return state.can_reach_entrance(f"Go To {region}", self.player)

    def _can_get(self, state, location) -> bool:
        """Returns whether state can access the given location name."""
        return state.can_reach_location(location, self.player)

    def _is_location_available(
        self,
        location: Union[str, SekiroLocationData, SekiroLocation]
    ) -> bool:
        """Returns whether the given location is being randomized."""
        if isinstance(location, SekiroLocationData):
            data = location
        elif isinstance(location, SekiroLocation):
            data = location.data
        else:
            data = location_dictionary[location]

        return (
            not data.is_event
            and not (
                self.options.excluded_location_behavior == "do_not_randomize"
                and data.name in self.all_excluded_locations
            )
            and not (
                self.options.missable_location_behavior == "do_not_randomize"
                and data.missable
            )
        )

    def write_spoiler(self, spoiler_handle: TextIO) -> None:
        text = ""

        if self.options.excluded_location_behavior == "allow_useful":
            text += f"\n{self.player_name}'s world excluded: {sorted(self.all_excluded_locations)}\n"

        if text:
            text = "\n" + text + "\n"
            spoiler_handle.write(text)

    def _shuffle(self, seq: Sequence) -> List:
        """Returns a shuffled copy of a sequence."""
        copy = list(seq)
        self.random.shuffle(copy)
        return copy

    def _pop_item(
        self,
        location: Location,
        items: List[SekiroItem]
    ) -> SekiroItem:
        """Returns the next item in items that can be assigned to location."""
        for i, item in enumerate(items):
            if location.can_fill(self.multiworld.state, item, False):
                return items.pop(i)

        # If we can't find a suitable item, give up and assign an unsuitable one.
        return items.pop(0)

    def _get_our_locations(self) -> List[SekiroLocation]:
        return cast(List[SekiroLocation], self.multiworld.get_locations(self.player))

    def fill_slot_data(self) -> Dict[str, object]:
        slot_data: Dict[str, object] = {}

        # Once all clients support overlapping item IDs, adjust the Sekiro AP item IDs to encode the
        # in-game ID as well as the count so that we don't need to send this information at all.
        #
        # We include all the items the game knows about so that users can manually request items
        # that aren't randomized, and then we _also_ include all the items that are placed in
        # practice `item_dictionary.values()` doesn't include upgraded or infused weapons.
        items_by_name = {
            location.item.name: cast(SekiroItem, location.item).data
            for location in self.multiworld.get_filled_locations()
            # item.code None is used for events, which we want to skip
            if location.item.code is not None and location.item.player == self.player
        }
        for item in item_dictionary.values():
            if item.name not in items_by_name:
                items_by_name[item.name] = item

        ap_ids_to_sekiro_ids: Dict[str, int] = {}
        item_counts: Dict[str, int] = {}
        for item in items_by_name.values():
            if item.ap_code is None: continue
            if item.sekiro_code: ap_ids_to_sekiro_ids[str(item.ap_code)] = item.sekiro_code
            if item.count != 1: item_counts[str(item.ap_code)] = item.count

        # A map from Archipelago's location IDs to the keys the static randomizer uses to identify
        # locations.
        location_ids_to_keys: Dict[int, str] = {}
        for location in cast(List[SekiroLocation], self.multiworld.get_filled_locations(self.player)):
            # Skip events and only look at this world's locations
            if (location.address is not None and location.item.code is not None
                    and location.data.static):
                location_ids_to_keys[location.address] = location.data.static

        slot_data = {
            "options": {
                "death_link": self.options.death_link.value,
                "randomize_enemies": self.options.randomize_enemies.value,
                "reduce_harmless_enemies": self.options.reduce_harmless_enemies.value,
                "scale_enemies": self.options.scale_enemies.value,
            },
            "seed": self.multiworld.seed_name,  # to verify the server's multiworld
            "slot": self.multiworld.player_name[self.player],  # to connect to server
            # Reserializing here is silly, but it's easier for the static randomizer.
            "random_enemy_preset": json.dumps(self.options.random_enemy_preset.value),
            "apIdsToItemIds": ap_ids_to_sekiro_ids,
            "itemCounts": item_counts,
            "locationIdsToKeys": location_ids_to_keys,
            # The range of versions of the static randomizer that are compatible
            # with this slot data. Incompatible versions should have at least a
            # minor version bump. Pre-release versions should generally only be
            # compatible with a single version, except very close to a stable
            # release when no changes are expected.
            #
            # TODO: This is checked by the static randomizer, which will surface an
            # error to the user if its version doesn't fall into the allowed
            # range. This needs to be changed to whatever is compatible for Sekiro.
            "versions": ">=3.0.0-beta.24 <3.1.0",
        }

        return slot_data

    @staticmethod
    def interpret_slot_data(slot_data: Dict[str, Any]) -> Dict[str, Any]:
        return slot_data
