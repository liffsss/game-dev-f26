"""Play a three-year campaign as the ruler."""

import argparse

from .game import Game


def read_amount(label: str, *, default: int) -> int:
    while True:
        answer = input(f"{label} [{default}]  ").strip()
        if answer.lower() in {"q", "quit"}:
            raise EOFError
        if not answer:
            return default
        try:
            return int(answer)
        except ValueError:
            print("Enter a whole number, or q to quit.")


def show_state(state: dict) -> None:
    print(f"\nYEAR {state['year']} / {state['years']}   |   {state['drought_percent']}% chance of drought")
    print(f"People: {state['population']}   Land: {state['land']} acres   Grain: {state['grain']} bushels")
    print(f"Land price: {state['land_price']} grain per acre")
    rules = state["constants"]
    print("\nCrop             Seed cost    Normal harvest    Drought harvest (per acre)")
    for name in ("regular", "resilient"):
        crop = rules[name]
        print(f"{name.title():<17}{crop['seed_cost']:>5}{crop['normal_yield']:>17}{crop['drought_yield']:>19}")


def choose_plan(state: dict, trade_bounds: dict) -> dict:
    rules = state["constants"]
    low, high = trade_bounds["minimum"], trade_bounds["maximum"]
    while True:
        trade = read_amount(f"Acres to trade ({low} sell, +{high} buy, 0 hold)", default=0)
        if low <= trade <= high:
            break
        print(f"Trade must be between {low} and {high} acres.")
    grain = state["grain"] - trade * state["land_price"]
    food = rules["food_per_person"]
    print(f"After trade: {state['land'] + trade} acres and {grain} grain. Each person needs {food} grain.")
    feed = read_amount("People to feed", default=min(state["population"], max(0, grain // food)))
    seed_grain = grain - feed * food
    labor = state["population"] * rules["acres_per_person"]
    max_acres = max(0, min(state["land"] + trade, labor))
    print(f"Seed budget: {seed_grain} grain. Plant up to {max_acres} total acres.")
    regular = read_amount("Regular acres", default=0)
    resilient = read_amount("Resilient acres", default=0)
    expected = {
        weather: sum(
            acres * rules[name][f"{weather}_yield"]
            for name, acres in (("regular", regular), ("resilient", resilient))
        )
        for weather in ("normal", "drought")
    }
    after_seeds = seed_grain - regular * rules["regular"]["seed_cost"] - resilient * rules["resilient"]["seed_cost"]
    print(f"Before harvest: {after_seeds} grain. Harvest if normal: {expected['normal']}. If drought: {expected['drought']}.")
    return {"trade": trade, "feed": feed, "regular": regular, "resilient": resilient}


def play(case: str, seed: int) -> None:
    game = Game()
    game.reset(seed, case)
    print("HAMURABI: THREE HARVESTS")
    print("Make a plan each year: trade land, feed people, and plant two kinds of seed.")
    print("Goal: finish three harvests with at most 10 deaths and enough grain to feed the remaining population once.")
    print("If more than 45% of the population starves in one year, the campaign ends. Enter q at any prompt to leave.")
    while not game.outcome()["terminal"]:
        state = game.observe("ruler")
        show_state(state)
        try:
            action = choose_plan(state, game.legal_actions("ruler")["properties"]["trade"])
            confirmation = input("Submit this plan? [Y/n]  ").strip().lower()
            if confirmation in {"q", "quit"}:
                return
            if confirmation not in {"", "y", "yes"}:
                continue
        except (EOFError, KeyboardInterrupt):
            print("\nCampaign closed.")
            return
        result = game.step("ruler", action)
        if not result["accepted"]:
            print(f"Plan refused: {result['reason']} Your year and resources are unchanged. Try again.")
            continue
        event = result["event"]
        weather = "Drought" if event["drought"] else "Normal rain"
        print(f"\nHarvest report: {weather}, {event['harvest']} grain collected, {event['starved']} people starved.")

    outcome = game.outcome()
    final = game.observe("ruler")
    label = {"secured": "The city is secure", "shortfall": "The city fell short of its goal", "famine": "Famine ended the campaign"}
    print(f"\n{label[outcome['reason']]}. Score: {outcome['score']}.")
    print(f"Final population: {final['population']}   Land: {final['land']}   Grain: {final['grain']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("steady", "dry", "lean"), default="steady")
    parser.add_argument("--seed", type=int, default=101)
    args = parser.parse_args()
    play(args.case, args.seed)


if __name__ == "__main__":
    main()
