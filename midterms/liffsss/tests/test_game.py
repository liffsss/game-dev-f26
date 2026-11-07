import unittest

from hamurabi.game import Game


def move(trade=0, feed=100, regular=0, resilient=0):
    return {"trade": trade, "feed": feed, "regular": regular, "resilient": resilient}


class GameRulesTest(unittest.TestCase):
    def test_three_year_acceptance_trace(self):
        game = Game()
        start = game.reset(101)
        self.assertEqual((start["year"], start["land"], start["grain"]), (1, 100, 2800))
        self.assertEqual(start["drought_percent"], 20)
        self.assertIsNone(start["previous_year"])

        first = game.step("ruler", move(trade=10, regular=80, resilient=30))
        self.assertTrue(first["accepted"])
        self.assertFalse(first["event"]["drought"])
        self.assertEqual(first["event"]["harvest"], 3150)
        year_two = game.observe()
        self.assertEqual((year_two["year"], year_two["land"], year_two["grain"]), (2, 110, 3520))
        self.assertEqual(year_two["previous_year"], first["event"])

        second = game.step("ruler", move(resilient=110))
        self.assertTrue(second["accepted"])
        self.assertTrue(second["event"]["drought"])
        self.assertEqual(second["event"]["harvest"], 2200)
        self.assertEqual(game.observe()["grain"], 3390)

        third = game.step("ruler", move(regular=110))
        self.assertTrue(third["accepted"])
        self.assertEqual(game.observe()["grain"], 4470)
        self.assertEqual(
            game.outcome(),
            {"terminal": True, "reason": "secured", "score": 7570, "success": True},
        )
        self.assertFalse(game.step("ruler", move())["accepted"])
        self.assertEqual(game.observe()["year"], 3)

    def test_refusal_changes_only_counter_and_does_not_consume_weather(self):
        game = Game()
        start = game.reset(1)
        fresh = Game()
        fresh.reset(1)
        denied = game.step("ruler", move(regular=100, resilient=1))
        self.assertFalse(denied["accepted"])
        self.assertIsNone(denied["event"])
        self.assertEqual(game.observe(), {**start, "invalid_actions": 1})
        self.assertEqual(game.legal_actions(), fresh.legal_actions())

        expected = fresh.step("ruler", move(regular=50, resilient=50))["event"]
        actual = game.step("ruler", move(regular=50, resilient=50))["event"]
        self.assertEqual(actual, expected)
        self.assertTrue(actual["drought"])
        self.assertEqual(actual["harvest"], 1250)

    def test_refuses_nonintegers_out_of_range_and_overspending(self):
        game = Game()
        game.reset(301, case="lean")
        invalid = (
            move(trade=21),
            move(trade=-21),
            move(feed=101),
            move(regular=-1),
            move(resilient=1.0),
            move(feed=True),
            move(trade=20),
            move(resilient=61),
            {**move(), "drought": False},
            {"trade": 0, "feed": 100},
            None,
        )
        for proposal in invalid:
            with self.subTest(proposal=proposal):
                self.assertFalse(game.step("ruler", proposal)["accepted"])
        self.assertEqual(game.observe()["invalid_actions"], len(invalid))
        self.assertEqual(game.observe()["grain"], 2180)
        self.assertEqual(game.observe()["year"], 1)

    def test_exact_grain_budget_is_legal_and_applies_sale(self):
        game = Game()
        game.reset(301, case="lean")
        result = game.step("ruler", move(trade=-1, regular=99))
        self.assertTrue(result["accepted"])
        self.assertEqual(game.observe()["land"], 119)
        self.assertEqual(game.observe()["grain"], result["event"]["harvest"])

    def test_no_hidden_weather_or_seed_in_observation_or_legal_schema(self):
        drought = Game()
        normal = Game()
        self.assertEqual(drought.reset(1), normal.reset(101))
        self.assertEqual(drought.legal_actions(), normal.legal_actions())
        proposal = move(regular=50, resilient=50)
        self.assertTrue(drought.step("ruler", proposal)["event"]["drought"])
        self.assertFalse(normal.step("ruler", proposal)["event"]["drought"])

    def test_observation_and_event_are_detached_from_engine_state(self):
        game = Game()
        start = game.reset(101)
        start["constants"]["regular"]["seed_cost"] = 0
        start["land"] = 999
        game.legal_actions()["properties"]["trade"]["maximum"] = 999
        self.assertEqual(game.observe()["constants"]["regular"]["seed_cost"], 2)
        self.assertEqual(game.observe()["land"], 100)
        self.assertEqual(game.legal_actions()["properties"]["trade"]["maximum"], 20)
        result = game.step("ruler", move(regular=1))
        result["event"]["harvest"] = 999
        self.assertEqual(game.observe()["previous_year"]["harvest"], 30)

    def test_famine_boundary_is_strictly_greater_than_45_percent(self):
        game = Game()
        game.reset(101)
        self.assertTrue(game.step("ruler", move(feed=55))["accepted"])
        self.assertFalse(game.outcome()["terminal"])
        self.assertEqual(game.observe()["population"], 55)
        game.reset(101)
        self.assertTrue(game.step("ruler", move(feed=54))["accepted"])
        self.assertEqual(game.observe()["population"], 54)
        self.assertEqual(game.outcome()["reason"], "famine")
        self.assertTrue(game.outcome()["terminal"])

    def test_third_year_without_reserve_ends_in_shortfall(self):
        game = Game()
        game.reset(101)
        for proposal in (move(regular=75), move(resilient=75), move()):
            self.assertTrue(game.step("ruler", proposal)["accepted"])
        self.assertEqual(game.outcome()["reason"], "shortfall")
        self.assertTrue(game.outcome()["terminal"])
        self.assertFalse(game.outcome()["success"])


    def test_labor_limits_planting_even_when_land_and_grain_allow_it(self):
        game = Game()
        game.reset(101, case="lean")
        self.assertTrue(game.step("ruler", move(feed=55))["accepted"])
        state = game.observe()
        self.assertEqual((state["population"], state["land"], state["grain"]), (55, 120, 1080))
        self.assertEqual(game.legal_actions()["properties"]["regular"]["maximum"], 110)
        refused = game.step("ruler", move(feed=0, regular=111))
        self.assertFalse(refused["accepted"])
        self.assertEqual(game.observe(), {**state, "invalid_actions": 1})

    def test_population_shortfall_and_starvation_penalty_survive_a_large_reserve(self):
        game = Game()
        game.reset(101)
        for proposal in (move(feed=89, regular=100), move(feed=89, resilient=100),
                         move(feed=89, regular=100)):
            self.assertTrue(game.step("ruler", proposal)["accepted"])
        final = game.observe()
        self.assertEqual((final["population"], final["grain"], final["total_starved"]), (89, 4760, 11))
        self.assertEqual(
            game.outcome(),
            {"terminal": True, "reason": "shortfall", "score": 7100, "success": False},
        )


if __name__ == "__main__":
    unittest.main()
