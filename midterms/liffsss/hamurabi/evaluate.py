"""Run bounded paired episodes and optionally save public evaluation traces."""

import argparse
import hashlib
import json
import os
from dataclasses import asdict, fields
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from .game import Game
from .players import (
    ACTION_FIELDS,
    MAX_OUTPUT_TOKENS,
    MODEL_TIMEOUT_SECONDS,
    PROMPT_ID,
    BaselinePolicy,
    Usage,
    VertexPolicy,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
SUITE_PATH = PROJECT_DIR / "suite.json"
STEP_LIMIT = 3
MODEL_CALL_LIMIT = 3
STANDARD_GLOBAL_PRICE = {
    "model": "gemini-3.5-flash-lite",
    "tier": "standard pay-as-you-go",
    "checked_on": "2026-11-07",
    "usd_per_million_input": 0.30,
    "usd_per_million_cached_input": 0.03,
    "usd_per_million_output_including_reasoning": 2.50,
    "source": "https://cloud.google.com/model-garden/pricing",
}


def run_episode(policy, case, seed, *, step_limit=STEP_LIMIT, model_call_limit=MODEL_CALL_LIMIT, show_turns=False):
    game = Game()
    game.reset(seed, case)
    turns = []
    model_calls = 0
    steps = 0
    illegal_actions = 0
    stop_reason = None
    started = perf_counter()
    while not game.outcome()["terminal"]:
        if steps >= step_limit:
            stop_reason = "step_limit"
            break
        if policy.live and model_calls >= model_call_limit:
            stop_reason = "model_call_limit"
            break
        observation = game.observe("ruler")
        schema = game.legal_actions("ruler")
        if show_turns:
            print(
                f"  Year {observation['year']}: {observation['population']} people, "
                f"{observation['land']} acres, {observation['grain']} grain, "
                f"{observation['drought_percent']}% drought. {policy.name} choosing...",
                flush=True,
            )
        if policy.live:
            model_calls += 1
        decision_started = perf_counter()
        decision = policy.decide(observation, schema)
        turn = {
            "observation": observation,
            "legal_actions": schema,
            "decision_seconds": round(perf_counter() - decision_started, 4),
            "action": None,
            "error": decision.error,
            "model_version": decision.model_version,
            "usage": asdict(decision.usage) if decision.usage else None,
            "transition": None,
        }
        turns.append(turn)
        if decision.error:
            stop_reason = decision.error
            if show_turns:
                print(f"    Stopped: {stop_reason}", flush=True)
            break
        # Trace only the four known fields, never unexpected model text.
        if isinstance(decision.action, dict):
            turn["action"] = {
                field: decision.action[field]
                for field in ACTION_FIELDS
                if type(decision.action.get(field)) is int
            }
        transition = game.step("ruler", decision.action)
        turn["transition"] = transition
        if not transition["accepted"]:
            illegal_actions += 1
            stop_reason = "illegal_action"
            if show_turns:
                print(f"    Rejected: {transition['reason']}", flush=True)
            break
        steps += 1
        if show_turns:
            event = transition["event"]
            weather = "drought" if event["drought"] else "normal weather"
            action_summary = ", ".join(f"{key} {turn['action'][key]}" for key in ACTION_FIELDS)
            print(
                f"    {action_summary} -> {weather}; harvest {event['harvest']}, "
                f"starved {event['starved']}",
                flush=True,
            )

    game_outcome = game.outcome()
    outcome = dict(game_outcome)
    if stop_reason is not None:
        outcome.update(terminal=True, reason=stop_reason, success=False)
    usage = summarize_usage(turns, model_calls)
    return {
        "case": case,
        "seed": seed,
        "policy": policy.name,
        "outcome": outcome,
        "game_outcome": game_outcome,
        "steps": steps,
        "step_attempts": steps + illegal_actions,
        "model_calls": model_calls,
        "illegal_actions": illegal_actions,
        "seconds": round(perf_counter() - started, 4),
        "usage": usage,
        "turns": turns,
    }


def summarize_usage(turns, model_calls):
    observed = [turn["usage"] for turn in turns if turn["usage"] is not None]
    usage = {
        "attempts_with_usage": len(observed),
        "attempts_without_usage": model_calls - len(observed),
    }
    for field in fields(Usage):
        values = [item[field.name] for item in observed if item[field.name] is not None]
        usage[field.name] = sum(values) if values or not model_calls else None
    return usage


def estimate_cost(usage, price):
    if price is None or usage["input_tokens"] is None or usage["output_tokens"] is None:
        return None
    cached = usage["cached_input_tokens"] or 0
    billable_output = usage["output_tokens"] + (usage["thinking_tokens"] or 0)
    total = (
        (usage["input_tokens"] - cached) * price["usd_per_million_input"]
        + cached * price["usd_per_million_cached_input"]
        + billable_output * price["usd_per_million_output_including_reasoning"]
    )
    return round(total / 1_000_000, 9)


def source_version():
    paths = (SUITE_PATH, *(Path(__file__).with_name(name) for name in ("game.py", "players.py", "evaluate.py")))
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def save_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv=None):
    suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", choices=("baseline", "vertex", "both"), default="baseline")
    parser.add_argument("--live", action="store_true", help="explicitly permit the Vertex AI requests")
    parser.add_argument("--case", choices=[case["name"] for case in suite["cases"]])
    parser.add_argument("--seed", type=int, help="select one declared seed within --case")
    parser.add_argument("--output", type=Path, help="write a JSON report and public action traces")
    parser.add_argument("--show-turns", action="store_true", help="show each policy choosing a move")
    args = parser.parse_args(argv)
    use_vertex = args.policy in ("vertex", "both")
    if use_vertex and not args.live:
        parser.error("--policy vertex or both requires --live")
    if args.seed is not None and not args.case:
        parser.error("--seed requires --case")
    selected_cases = [case for case in suite["cases"] if args.case in (None, case["name"])]
    if args.seed is not None and args.seed not in selected_cases[0]["seeds"]:
        parser.error("--seed must match a seed declared for this case")

    policies = [BaselinePolicy()] if args.policy in ("baseline", "both") else []
    model = None
    location = None
    if use_vertex:
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "global").strip()
        model = os.getenv("COURSE_MODEL", "").strip()
        if not project or not location or not model:
            parser.error("configure GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION and COURSE_MODEL for Vertex")
        try:
            from google import genai  # noqa: F401
        except ImportError:
            parser.error("install the live dependency from requirements.txt before running Vertex")
        policies.append(VertexPolicy(project, location, model))

    price = STANDARD_GLOBAL_PRICE if model == STANDARD_GLOBAL_PRICE["model"] and location == "global" else None
    report = {
        "suite_version": suite["version"],
        "source_sha256": source_version(),
        "started_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "step_limit": STEP_LIMIT,
        "model_call_limit": MODEL_CALL_LIMIT,
        "model_timeout_seconds": MODEL_TIMEOUT_SECONDS if use_vertex else None,
        "model_output_token_limit": MAX_OUTPUT_TOKENS if use_vertex else None,
        "provider": "vertex" if use_vertex else None,
        "requested_model": model,
        "location": location,
        "prompt_id": PROMPT_ID if use_vertex else None,
        "price": price,
        "episodes": [],
    }
    for case in selected_cases:
        seeds = [args.seed] if args.seed is not None else case["seeds"]
        for seed in seeds:
            for policy in policies:
                print(f"{policy.name} | {case['name']} | seed {seed}", flush=True)
                episode = run_episode(policy, case["name"], seed, show_turns=args.show_turns)
                episode["split"] = case["split"]
                episode["estimated_cost_usd"] = estimate_cost(episode["usage"], price) if policy.live else 0.0
                report["episodes"].append(episode)
                outcome = episode["outcome"]
                print(
                    f"  {outcome['reason']} | score {outcome['score']} | {episode['steps']} steps | "
                    f"{episode['model_calls']} model calls | {episode['seconds']:.2f}s",
                    flush=True,
                )
                if args.output:
                    save_report(args.output, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
