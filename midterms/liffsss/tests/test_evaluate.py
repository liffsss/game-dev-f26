import unittest
from types import SimpleNamespace

from hamurabi.evaluate import run_episode
from hamurabi.players import BaselinePolicy, Decision, decode_vertex_response


class FakeVertex:
    name = "vertex"
    live = True

    def __init__(self, *decisions):
        self.decisions = iter(decisions)
        self.inputs = []

    def decide(self, observation, legal_actions):
        self.inputs.append((observation, legal_actions))
        return next(self.decisions)


class EvaluationTests(unittest.TestCase):
    def test_step_limit_stops_before_another_action(self):
        episode = run_episode(BaselinePolicy(), "steady", 101, step_limit=1)
        self.assertEqual(episode["outcome"]["reason"], "step_limit")
        self.assertEqual(episode["steps"], 1)
        self.assertEqual(episode["model_calls"], 0)
        self.assertEqual(len(episode["turns"]), 1)

    def test_call_limit_stops_before_another_call(self):
        plan = Decision(action={"trade": 0, "feed": 100, "regular": 100, "resilient": 0})
        policy = FakeVertex(plan)
        episode = run_episode(policy, "steady", 101, model_call_limit=1)
        self.assertEqual(episode["outcome"]["reason"], "model_call_limit")
        self.assertEqual(episode["model_calls"], 1)
        self.assertEqual(len(policy.inputs), 1)

    def test_timeout_is_counted_without_fallback_or_move(self):
        episode = run_episode(FakeVertex(Decision(error="model_timeout")), "steady", 101)
        self.assertEqual(episode["outcome"]["reason"], "model_timeout")
        self.assertFalse(episode["outcome"]["success"])
        self.assertEqual(episode["model_calls"], 1)
        self.assertEqual(episode["steps"], 0)
        self.assertEqual(episode["usage"]["attempts_without_usage"], 1)
        self.assertFalse(episode["game_outcome"]["terminal"])

    def test_illegal_action_fails_without_fallback(self):
        illegal = Decision(action={"trade": 0, "feed": 101, "regular": 0, "resilient": 0})
        episode = run_episode(FakeVertex(illegal), "steady", 101)
        self.assertEqual(episode["outcome"]["reason"], "illegal_action")
        self.assertEqual(episode["illegal_actions"], 1)
        self.assertEqual(episode["model_calls"], 1)
        self.assertEqual(episode["steps"], 0)
        self.assertFalse(episode["turns"][0]["transition"]["accepted"])

    def test_model_cannot_distinguish_unrevealed_weather_from_its_input(self):
        first = FakeVertex(Decision(error="model_timeout"))
        second = FakeVertex(Decision(error="model_timeout"))
        run_episode(first, "steady", 101)
        run_episode(second, "steady", 102)
        self.assertEqual(first.inputs, second.inputs)
        observation, schema = first.inputs[0]
        self.assertIsNone(observation["previous_year"])
        self.assertEqual(set(schema["properties"]), {"trade", "feed", "regular", "resilient"})
        self.assertNotIn("seed", observation)
        self.assertNotIn("case", observation)
        self.assertNotIn("future_weather", observation)

    def test_baseline_replays_same_legal_actions_and_terminal_outcome(self):
        for case, seed in (("steady", 102), ("dry", 201), ("lean", 301)):
            with self.subTest(case=case):
                first = run_episode(BaselinePolicy(), case, seed)
                second = run_episode(BaselinePolicy(), case, seed)
                self.assertEqual(first["steps"], 3)
                self.assertEqual(first["illegal_actions"], 0)
                self.assertTrue(first["game_outcome"]["terminal"])
                self.assertEqual(first["outcome"], second["outcome"])
                self.assertEqual(
                    [turn["action"] for turn in first["turns"]],
                    [turn["action"] for turn in second["turns"]],
                )

    def test_decode_counts_reasoning_and_keeps_usage_on_invalid_output(self):
        reply = SimpleNamespace(
            candidates=[SimpleNamespace(finish_reason="STOP")],
            model_version="test-version",
            text="oops",
            usage_metadata=SimpleNamespace(
                prompt_token_count=50, candidates_token_count=12, thoughts_token_count=31,
                total_token_count=93, cached_content_token_count=0,
            ),
        )
        decision = decode_vertex_response(reply)
        self.assertEqual(decision.error, "invalid_model_response")
        self.assertEqual(decision.usage.thinking_tokens, 31)
        self.assertEqual(decision.usage.total_tokens, 93)
        self.assertEqual(decision.model_version, "test-version")


if __name__ == "__main__":
    unittest.main()
