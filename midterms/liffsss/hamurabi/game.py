"""Deterministic, single-player rules for Hamurabi: Three Harvests."""

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from random import Random


PLAYER = "ruler"
ACTION_FIELDS = ("trade", "feed", "regular", "resilient")
LAND_PRICES = (18, 22, 25)
FOOD_PER_PERSON = 20
ACRES_PER_PERSON = 2
MAX_TRADE = 20
FAMINE_PERCENT = 45
MAX_TOTAL_STARVED = 10
GRAIN_PER_ACRE_SCORE = 10
GRAIN_PER_STARVED_PENALTY = 40
CROPS = {
    "regular": {"seed_cost": 2, "normal_yield": 30, "drought_yield": 5},
    "resilient": {"seed_cost": 3, "normal_yield": 25, "drought_yield": 20},
}
SUITE_FILE = Path(__file__).resolve().parent.parent / "suite.json"


@dataclass
class _Season:
    population: int
    land: int
    grain: int
    forecasts: tuple[int, ...]
    year: int = 1
    previous_year: dict | None = None
    total_starved: int = 0
    invalid_actions: int = 0
    reason: str = "ongoing"


class Game:
    """The runner owns this object. Give a player only the public snapshots."""

    def __init__(self):
        self._season = None
        self._weather = Random()

    def reset(self, seed: int, case: str = "steady") -> dict:
        if type(seed) is not int:
            raise ValueError("The episode seed must be an integer.")
        suite = json.loads(SUITE_FILE.read_text(encoding="utf-8"))
        entry = next((entry for entry in suite["cases"] if entry["name"] == case), None)
        if entry is None:
            raise ValueError(f"Unknown starting case: {case}")
        self._season = _Season(
            population=entry["population"],
            land=entry["land"],
            grain=entry["grain"],
            forecasts=tuple(entry["drought_percent"]),
        )
        self._weather = Random(seed)
        return self.observe()

    def _get_season(self) -> _Season:
        if self._season is None:
            raise RuntimeError("Reset the game before starting an episode.")
        return self._season

    @staticmethod
    def _require_ruler(player_id):
        if player_id != PLAYER:
            raise ValueError(f"Only the {PLAYER!r} role can play this game.")

    def observe(self, player_id: str = PLAYER) -> dict:
        self._require_ruler(player_id)
        season = self._get_season()
        return {
            "year": season.year,
            "years": len(LAND_PRICES),
            "population": season.population,
            "land": season.land,
            "grain": season.grain,
            "drought_percent": season.forecasts[season.year - 1],
            "land_price": LAND_PRICES[season.year - 1],
            "previous_year": deepcopy(season.previous_year),
            "total_starved": season.total_starved,
            "invalid_actions": season.invalid_actions,
            "constants": {
                "food_per_person": FOOD_PER_PERSON,
                "acres_per_person": ACRES_PER_PERSON,
                "max_trade": MAX_TRADE,
                **deepcopy(CROPS),
            },
        }

    def legal_actions(self, player_id: str = PLAYER) -> dict:
        self._require_ruler(player_id)
        if self.outcome()["terminal"]:
            return {"not": {}}
        public = self.observe(player_id)
        max_trade = public["constants"]["max_trade"]
        max_buy = min(max_trade, public["grain"] // public["land_price"])
        max_sell = min(max_trade, public["land"])
        max_acres = min(public["land"] + max_buy, public["population"] * ACRES_PER_PERSON)
        return {
            "type": "object",
            "properties": {
                "trade": {"type": "integer", "minimum": -max_sell, "maximum": max_buy},
                "feed": {"type": "integer", "minimum": 0, "maximum": public["population"]},
                "regular": {"type": "integer", "minimum": 0, "maximum": max_acres},
                "resilient": {"type": "integer", "minimum": 0, "maximum": max_acres},
            },
            "required": list(ACTION_FIELDS),
            "additionalProperties": False,
            "description": (
                "Trade is signed acres (positive buys, negative sells). Feed is people. "
                "Total planting must fit land after trade and current labor. Total grain "
                "cost of trade, feed and seed cannot exceed stored grain."
            ),
        }

    def outcome(self) -> dict:
        season = self._get_season()
        return {
            "terminal": season.reason != "ongoing",
            "reason": season.reason,
            "score": (
                FOOD_PER_PERSON * season.population
                + season.grain
                + GRAIN_PER_ACRE_SCORE * season.land
                - GRAIN_PER_STARVED_PENALTY * season.total_starved
            ),
            "success": season.reason == "secured",
        }

    def step(self, player_id: str, action: object) -> dict:
        self._require_ruler(player_id)
        season = self._get_season()
        if season.reason != "ongoing":
            return {"accepted": False, "reason": "The term is over.", "event": None,
                    "outcome": self.outcome()}
        reason = self._refusal(season, action)
        if reason is not None:
            season.invalid_actions += 1
            return {"accepted": False, "reason": reason, "event": None,
                    "outcome": self.outcome()}

        drought = self._weather.random() * 100 < season.forecasts[season.year - 1]
        yield_key = "drought_yield" if drought else "normal_yield"
        harvest = sum(action[crop] * values[yield_key] for crop, values in CROPS.items())
        population_before = season.population
        starved = population_before - action["feed"]
        season.grain += harvest - self._cost(season, action)
        season.land += action["trade"]
        season.population -= starved
        season.total_starved += starved
        event = {"year": season.year, "drought": drought, "harvest": harvest,
                 "starved": starved, **action}
        season.previous_year = event

        if 100 * starved > FAMINE_PERCENT * population_before:
            season.reason = "famine"
        elif season.year == len(LAND_PRICES):
            enough_people = season.total_starved <= MAX_TOTAL_STARVED
            enough_grain = season.grain >= FOOD_PER_PERSON * season.population
            season.reason = "secured" if enough_people and enough_grain else "shortfall"
        else:
            season.year += 1
        return {"accepted": True, "reason": "accepted", "event": event.copy(),
                "outcome": self.outcome()}

    @staticmethod
    def _cost(season: _Season, action: dict) -> int:
        land_cost = action["trade"] * LAND_PRICES[season.year - 1]
        food_cost = action["feed"] * FOOD_PER_PERSON
        seed_cost = sum(action[crop] * values["seed_cost"] for crop, values in CROPS.items())
        return land_cost + food_cost + seed_cost

    def _refusal(self, season: _Season, action: object) -> str | None:
        if not isinstance(action, dict) or action.keys() != set(ACTION_FIELDS):
            return "Give exactly four fields: trade, feed, regular, and resilient."
        if any(type(value) is not int for value in action.values()):
            return "All four values must be whole numbers."
        if not -min(MAX_TRADE, season.land) <= action["trade"] <= MAX_TRADE:
            return f"Trade at most {MAX_TRADE} acres, and sell only land you own."
        if not 0 <= action["feed"] <= season.population:
            return f"Feed between 0 and {season.population} people."
        if any(action[crop] < 0 for crop in CROPS):
            return "Planted acres cannot be negative."
        capacity = min(season.land + action["trade"], season.population * ACRES_PER_PERSON)
        if action["regular"] + action["resilient"] > capacity:
            return f"Land and labor allow at most {capacity} planted acres in total."
        cost = self._cost(season, action)
        if cost > season.grain:
            return f"This plan needs {cost} grain, but only {season.grain} is stored."
        return None
