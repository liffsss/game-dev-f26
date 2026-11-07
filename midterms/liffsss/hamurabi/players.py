"""Players see only the game interface's public observation and action schema."""

import json
from dataclasses import dataclass

MODEL_TIMEOUT_SECONDS = 15
MAX_OUTPUT_TOKENS = 1024
ACTION_FIELDS = ("trade", "feed", "regular", "resilient")
PROMPT_ID = "granary-public-v1"
SYSTEM_INSTRUCTION = """You are the ruler in a three-year grain management game. Choose this year's plan as a single JSON object. Your main goal is to feed the people and finish with enough grain for another year. If several plans seem viable, prefer a higher end score from population, grain and land. Drought is uncertain. Balance normal yield with the possibility of a dry year. A positive trade buys acres and a negative trade sells them. Set feed to the number of people, not the grain spent. Trading is settled first. Food and seed costs together must fit the grain after trade. Regular and resilient acres together must fit the land after trade and the labor cap from the observation. Verify the numbers before sending your action. Use only the public observation and legal action schema. Return trade, feed, regular and resilient as integers."""


@dataclass(frozen=True)
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    thinking_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None


@dataclass(frozen=True)
class Decision:
    action: object = None
    error: str | None = None
    usage: Usage | None = None
    model_version: str | None = None


class BaselinePolicy:
    """Greedily maximize people fed, then expected grain and land value for this year."""

    name = "baseline"
    live = False

    def decide(self, observation, legal_actions):
        rules = observation["constants"]
        land, grain, population = (observation[k] for k in ("land", "grain", "population"))
        price = observation["land_price"]
        p = observation["drought_percent"]
        regular = rules["regular"]
        resilient = rules["resilient"]
        cost_regular = regular["seed_cost"]
        cost_resilient = resilient["seed_cost"]
        # Integer arithmetic keeps ties and reproducibility independent of rounding.
        regular_return = (100 - p) * regular["normal_yield"] + p * regular["drought_yield"] - 100 * cost_regular
        resilient_return = (100 - p) * resilient["normal_yield"] + p * resilient["drought_yield"] - 100 * cost_resilient
        trade_range = legal_actions["properties"]["trade"]
        best = None
        best_action = None
        for trade in range(trade_range["minimum"], trade_range["maximum"] + 1):
            land_after_trade = land + trade
            grain_after_trade = grain - trade * price
            if land_after_trade < 0 or grain_after_trade < 0:
                continue
            feed = min(population, grain_after_trade // rules["food_per_person"])
            planting_budget = grain_after_trade - feed * rules["food_per_person"]
            capacity = min(land_after_trade, population * rules["acres_per_person"])
            for r in range(min(capacity, planting_budget // cost_regular) + 1):
                affordable = (planting_budget - r * cost_regular) // cost_resilient
                s = min(capacity - r, affordable) if resilient_return >= 0 else 0
                expected = 100 * (planting_budget + 10 * land_after_trade) + regular_return * r + resilient_return * s
                drought_reserve = planting_budget + (regular["drought_yield"] - cost_regular) * r + (resilient["drought_yield"] - cost_resilient) * s
                rank = (feed, expected, drought_reserve, -abs(trade), -r)
                if best is None or rank > best:
                    best = rank
                    best_action = {"trade": trade, "feed": feed, "regular": r, "resilient": s}
        return Decision(action=best_action)


def decode_vertex_response(response):
    metadata = response.usage_metadata
    usage = None if metadata is None else Usage(
        input_tokens=metadata.prompt_token_count,
        output_tokens=metadata.candidates_token_count,
        thinking_tokens=metadata.thoughts_token_count,
        total_tokens=metadata.total_token_count,
        cached_input_tokens=metadata.cached_content_token_count,
    )
    model_version = response.model_version
    if not response.candidates or response.candidates[0].finish_reason != "STOP":
        return Decision(error="unfinished_model_response", usage=usage, model_version=model_version)
    try:
        action = json.loads(response.text or "")
    except (ValueError, TypeError):
        return Decision(error="invalid_model_response", usage=usage, model_version=model_version)
    return Decision(action=action, usage=usage, model_version=model_version)


class VertexPolicy:
    name = "vertex"
    live = True

    def __init__(self, project, location, model):
        self.project = project
        self.location = location
        self.model = model

    def decide(self, observation, legal_actions):
        # Keep the SDK optional for human play, offline evaluation and CI.
        from google import genai
        from google.auth.exceptions import GoogleAuthError
        from google.genai import errors, types
        from httpx import HTTPError, TimeoutException

        payload = json.dumps({"observation": observation, "legal_actions": legal_actions}, sort_keys=True)
        response_schema = {
            "type": "object",
            "properties": {field: {"type": "integer"} for field in ACTION_FIELDS},
            "required": list(ACTION_FIELDS),
        }
        try:
            with genai.Client(
                vertexai=True,
                project=self.project,
                location=self.location,
                http_options=types.HttpOptions(
                    api_version="v1",
                    timeout=MODEL_TIMEOUT_SECONDS * 1000,
                    retry_options=types.HttpRetryOptions(attempts=1),
                    headers={"X-Vertex-AI-LLM-Request-Type": "shared"},
                ),
            ) as client:
                reply = client.models.generate_content(
                    model=self.model,
                    contents=payload,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.2,
                        max_output_tokens=MAX_OUTPUT_TOKENS,
                        response_mime_type="application/json",
                        response_json_schema=response_schema,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                )
        except (TimeoutError, TimeoutException):
            return Decision(error="model_timeout")
        except errors.UnknownApiResponseError:
            # The SDK exception can contain an untrusted provider response body.
            return Decision(error="invalid_provider_response")
        except errors.APIError as error:
            code = error.code
            if code in (408, 504):
                return Decision(error="model_timeout")
            return Decision(error=f"model_api_{code}" if isinstance(code, int) else "model_api_error")
        except GoogleAuthError:
            return Decision(error="model_auth_error")
        except HTTPError:
            return Decision(error="model_transport_error")
        return decode_vertex_response(reply)
