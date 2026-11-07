# Hamurabi: Three Harvests

COMS E6998 section 014 · liffsss · November 2026

Three years to keep a city fed. Each year you can trade land, decide how many
people to feed, and split planting between regular and drought-resistant seed.
The forecast gives a probability. The harvest comes after you commit the plan.
Finish with at most ten cumulative starvation deaths and enough grain to feed
the surviving population once more. More than 45% starvation in one year ends
the campaign early.

## Scope and sources

This is a from-scratch, bounded reconstruction of the grain-and-acreage loop
from David H. Ahl's BASIC *Hammurabi*, derived from Doug Dyment's FOCAL game.
It keeps the land market, feeding, planting and harvest. It replaces the long
campaign with three years, adds a forecast and a seed choice, and leaves out
rats, plague and immigration. Three turns let a person finish quickly and
keep each live evaluation episode to at most three calls. The forecast turns
weather into a decision about how much risk to take with the grain reserve.

The historical reference was Ahl's *BASIC Computer Games* (1978),
[pp. 78–79](https://www.atariarchives.org/basicgames/showpage.php?page=78).
The scan is copyrighted and was consulted for rules and attribution. The code,
UI text and numeric adaptations here are new. No historical listing, prose, or
assets are redistributed. See the [rule and source map](docs/RULE-SOURCE-MAP.md)
for individual rule locators and the exact transitions.

## Run from a fresh clone

Run the following commands from `midterms/liffsss/` within the clone. Python
3.11 or newer is required. Python 3.12 is the tested version. If needed, replace
`python3.12` with an equivalent Python 3.11+ executable. The game, baseline,
and tests use the standard library. No install or account is needed for these
commands.

```sh
python3.12 --version
python3.12 -m hamurabi --case steady --seed 101
python3.12 -m unittest discover -s tests -v
python3.12 -m hamurabi.evaluate --policy baseline --show-turns
```

At the prompts, enter whole numbers. Negative trade sells acres and positive
trade buys them. Read the seed budget and compare the two harvest estimates
before submitting. `q` exits. For a playtest with a new weather draw, use
`python3.12 -m hamurabi --case steady --seed 404` from the same folder.

For a live evaluation, use your own Google Cloud project with the Vertex AI
API enabled and Application Default Credentials. From `midterms/liffsss/`:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT='your-own-vertex-project'
export GOOGLE_CLOUD_LOCATION='global'
export COURSE_MODEL='gemini-3.5-flash-lite'
python -m hamurabi.evaluate --policy both --live --output /tmp/hamurabi-rerun.json
```

For a single demonstration (up to three live calls),
run this from `midterms/liffsss/` with the same Vertex environment:

```sh
python -m hamurabi.evaluate --policy vertex --live --case steady --seed 101 --show-turns
```

## Interface and evidence

`hamurabi.game.Game` supplies `reset(seed, case)`, `observe(player_id)`,
`legal_actions(player_id)`, `step(player_id, action)`, and `outcome()`. The ruler
makes one complete annual plan. The engine validates it and owns all resource
changes, weather and scoring. The evaluator submits the model's response through
that same interface.

- [Declared suite](suite.json) and [evaluation report](EVALUATION.md)
- [Agent team log](AGENT-TEAM.md), [agent configuration](agent-config.json), and [independent review](review.md)
- [Human playtest notes or status](PLAYTEST.md)
- Recording link: pending a reviewer-accessible upload.
