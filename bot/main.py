from typing import Optional

from loguru import logger

from ares import AresBot
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units


class MyBot(AresBot):
    def __init__(self, game_step_override: Optional[int] = None):
        """Initiate custom bot

        Parameters
        ----------
        game_step_override :
            If provided, set the game_step to this value regardless of how it was
            specified elsewhere
        """
        super().__init__(game_step_override)

    async def on_step(self, iteration: int) -> None:
        await super(MyBot, self).on_step(iteration)

        if iteration % 100 == 0:
            logger.info(f"{self.time_formatted} Num banes: {len(self.mediator.get_own_army_dict[UnitTypeId.BANELING])}")

            # print out available abilities for a single ling to see if bane morph is there
            if lings := self.mediator.get_own_army_dict[UnitTypeId.ZERGLING]:
                abilities = await self.get_available_abilities(lings)
                for ling_abilities in abilities:
                    for ability in ling_abilities:
                        logger.info(f"{ability}")
                    break

        larvae: Units = self.larva
        lings: Units = self.units(UnitTypeId.ZERGLING)
        # Send all idle banes to enemy
        if banes := [u for u in self.units if u.type_id == UnitTypeId.BANELING and u.is_idle]:
            for unit in banes:
                unit.attack(self.select_target())

        # If supply is low, train overlords
        if (
                self.supply_left < 2
                and larvae
                and self.can_afford(UnitTypeId.OVERLORD)
                and not self.already_pending(UnitTypeId.OVERLORD)
        ):
            larvae.random.train(UnitTypeId.OVERLORD)
            return

        # If bane nest is ready, train banes
        if lings and self.can_afford(UnitTypeId.BANELING) and self.structures(UnitTypeId.BANELINGNEST).ready:
            # TODO: Get lings.random.train(UnitTypeId.BANELING) to work
            #   Broken on recent patches
            # lings.random.train(UnitTypeId.BANELING)

            # This way is working
            lings.random(AbilityId.MORPHTOBANELING_BANELING)
            return

        # If all our townhalls are dead, send all our units to attack
        if not self.townhalls:
            for unit in self.units.of_type({UnitTypeId.DRONE, UnitTypeId.QUEEN, UnitTypeId.ZERGLING}):
                unit.attack(self.enemy_start_locations[0])
            return

        hq: Unit = self.townhalls.first

        # Send idle queens with >=25 energy to inject
        for queen in self.units(UnitTypeId.QUEEN).idle:
            # The following checks if the inject ability is in the queen abilitys - basically it checks if we have enough energy and if the ability is off-cooldown
            # abilities = await self.get_available_abilities(queen)
            # if AbilityId.EFFECT_INJECTLARVA in abilities:
            if queen.energy >= 25:
                queen(AbilityId.EFFECT_INJECTLARVA, hq)

        # Build spawning pool
        if self.structures(UnitTypeId.SPAWNINGPOOL).amount + self.already_pending(UnitTypeId.SPAWNINGPOOL) == 0:
            if self.can_afford(UnitTypeId.SPAWNINGPOOL):
                await self.build(
                    UnitTypeId.SPAWNINGPOOL,
                    near=hq.position.towards(self.game_info.map_center, 5),
                )

        # Upgrade to lair if spawning pool is complete
        # if self.structures(UnitTypeId.SPAWNINGPOOL).ready:
        #     if hq.is_idle and not self.townhalls(UnitTypeId.LAIR):
        #         if self.can_afford(UnitTypeId.LAIR):
        #             hq.build(UnitTypeId.LAIR)

        # If lair is ready and we have no hydra den on the way: build hydra den
        if self.structures(UnitTypeId.SPAWNINGPOOL).ready and self.can_afford(UnitTypeId.BANELINGNEST):
            if self.structures(UnitTypeId.BANELINGNEST).amount + self.already_pending(UnitTypeId.BANELINGNEST) == 0:
                await self.build(
                    UnitTypeId.BANELINGNEST,
                    near=hq.position.towards(self.game_info.map_center, 5),
                )

        # If we dont have both extractors: build them
        if (
                self.structures(UnitTypeId.SPAWNINGPOOL)
                and self.gas_buildings.amount + self.already_pending(UnitTypeId.EXTRACTOR) < 2
                and self.can_afford(UnitTypeId.EXTRACTOR)
        ):
            # May crash if we dont have any drones
            for vg in self.vespene_geyser.closer_than(10, hq):
                drone: Unit = self.workers.random
                drone.build_gas(vg)
                break

        # If we have less than 22 drones, build drones
        if self.supply_workers + self.already_pending(UnitTypeId.DRONE) < 22:
            if larvae and self.can_afford(UnitTypeId.DRONE):
                larva: Unit = larvae.random
                larva.train(UnitTypeId.DRONE)
                return

        # Saturate gas
        for a in self.gas_buildings:
            if a.assigned_harvesters < a.ideal_harvesters:
                w: Units = self.workers.closer_than(10, a)
                if w:
                    w.random.gather(a)

        # Build queen once the pool is done
        if self.structures(UnitTypeId.SPAWNINGPOOL).ready:
            if not self.units(UnitTypeId.QUEEN) and hq.is_idle:
                if self.can_afford(UnitTypeId.QUEEN):
                    hq.train(UnitTypeId.QUEEN)

        # Train zerglings
        if larvae and self.can_afford(UnitTypeId.ZERGLING):
            larvae.random.train(UnitTypeId.ZERGLING)

    """
    Can use `python-sc2` hooks as usual, but make a call the inherited method in the superclass
    Examples:
    """
    # async def on_start(self) -> None:
    #     await super(MyBot, self).on_start()
    #
    #     # on_start logic here ...
    #
    # async def on_end(self, game_result: Result) -> None:
    #     await super(MyBot, self).on_end(game_result)
    #
    #     # custom on_end logic here ...
    #
    # async def on_building_construction_complete(self, unit: Unit) -> None:
    #     await super(MyBot, self).on_building_construction_complete(unit)
    #
    #     # custom on_building_construction_complete logic here ...
    #
    # async def on_unit_created(self, unit: Unit) -> None:
    #     await super(MyBot, self).on_unit_created(unit)
    #
    #     # custom on_unit_created logic here ...
    #
    # async def on_unit_destroyed(self, unit_tag: int) -> None:
    #     await super(MyBot, self).on_unit_destroyed(unit_tag)
    #
    #     # custom on_unit_destroyed logic here ...
    #
    # async def on_unit_took_damage(self, unit: Unit, amount_damage_taken: float) -> None:
    #     await super(MyBot, self).on_unit_took_damage(unit, amount_damage_taken)
    #
    #     # custom on_unit_took_damage logic here ...
