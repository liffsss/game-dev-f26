# Evaluation · November 7, 2026

## Declaration and setup

[Suite v1](suite.json) was committed as `de5cd94` before the game and policies
were implemented. We ran one independent Gemini episode and one scripted
baseline episode on each of six case/seed pairs. `steady` was the development
case. `dry` and `lean` were reserved from prompt tuning, and the prompt
`granary-public-v1` stayed fixed for the full live suite. No episode was
restarted or replaced. The two policies for each pair started with the same
resources, public forecast, and seeded weather stream. See
[all 12 public action traces](traces/evaluation.json).

| Case | Split | Population / acres / grain | Forecasts | Seeds |
| --- | --- | --- | --- | --- |
| steady | development | 100 / 100 / 2,800 | 20%, 25%, 20% | 101, 102 |
| dry | held out | 100 / 110 / 3,300 | 65%, 75%, 70% | 201, 202 |
| lean | held out | 100 / 120 / 2,180 | 40%, 55%, 45% | 301, 302 |

Game version `1.0.0`, evaluated source commit `0a7b744`. The suite and runner source SHA-256 is
`d976eb8705dd7f64a93813a94d69fe8b482b8da533d00d57eb934602f4d08738`.
Runtime provider Vertex AI (`global`), requested and returned model
`gemini-3.5-flash-lite`, SDK `google-genai==2.23.0`, temperature 0.2, and
output cap 1,024 tokens. An episode permits at most three accepted steps and
three model calls. The SDK HTTP timeout is 15 seconds per request, with SDK
retries disabled. Failed calls count. On a timeout, malformed response, or
illegal action the runner stops with a reason and uses no fallback. The same
schema and engine validate both players. The 15 seconds is a transport
timeout rather than a separate wall-clock deadline around credential refresh.

The baseline considers each legal trade, feeds as many people as it can, and
then maximizes expected grain plus the public score weight of 10 per acre for
this year's plan. It uses drought reserves as a tie-breaker. The two policies
receive identical public observation and schema objects. The scripted policy
encodes the 10-per-acre weight. The model prompt names the goal and components
but omits the exact score weights and numeric death thresholds. That difference,
and the very different compute budgets, are limits on this comparison.

## Results

| Case | Seed | Baseline outcome / score | Gemini outcome / score | Gemini steps / calls | Gemini seconds / tokens | Est. Gemini cost |
| --- | ---: | --- | --- | --- | --- | ---: |
| steady | 101 | secured / 6,853 | secured / 6,900 | 3 / 3 | 3.93 / 2,075 | $0.000838 |
| steady | 102 | famine / −1,700 | illegal / 4,840* | 1 / 2 | 1.97 / 1,380 | $0.000590 |
| dry | 201 | secured / 7,350 | illegal / 4,565* | 1 / 2 | 2.01 / 1,353 | $0.000529 |
| dry | 202 | secured / 8,000 | illegal / 4,105* | 2 / 3 | 3.02 / 2,067 | $0.000827 |
| lean | 301 | secured / 6,147 | illegal / 5,380* | 0 / 1 | 1.34 / 662 | $0.000287 |
| lean | 302 | secured / 6,751 | illegal / 5,380* | 0 / 1 | 1.09 / 663 | $0.000289 |

\* Score at the point of refusal. An early-stop score is not a three-year
result and is not used to compare final scores.

The baseline secured **5/6** campaigns, with 1 famine, 18 accepted actions,
and 0 illegal actions. Gemini secured **1/6** campaigns, with 7 accepted and
5 illegal actions across 12 model calls. There were zero timeouts and zero
provider or JSON parsing errors. Median episode time was 0.006 seconds for
baseline and 1.99 seconds for Gemini on this machine. The Gemini suite totaled
7,791 input and 409 output tokens, with no cached input or separately reported
reasoning tokens. Baseline had no token usage or provider cost. Using
[Google's Standard global list prices](https://cloud.google.com/model-garden/pricing)
checked November 7, 2026 ($0.30 input and $2.50 output including reasoning per
million tokens), estimated Gemini cost was **$0.00336** before credit. This is
an estimate from returned usage, not a billing statement.

On steady/101 both policies secured the city. Gemini planted a mix in year 2,
collected 1,500 grain in the drought, and did not need to sell land in year 3.
The baseline planted 140 regular acres in year 2 and harvested 700, then sold
19 acres in year 3 to afford food and seed. On steady/102 the baseline's
first-year drought caused a food shortfall the city never recovered from. All
five rejected Gemini plans overspent the available grain. For example, lean/301
requested a 2,640-grain plan with 2,180 stored, while the baseline sold nine
acres before feeding and planting. Valid JSON alone did not enforce the budget.

## History, verification and limitations

Each request starts fresh with current public resources, forecast, limits and
the most recent public harvest. There is no accumulated chat or cross-episode
memory. Earlier harvests change decisions through current resources and deaths.
After removing `previous_year` from the public observations, the baseline
selected the same actions on all 12 later turns. This checks the baseline's
use of history only. It does not measure a memory effect for Gemini.

All 12 recorded traces replayed exactly through the rules. After evaluation,
independent review found that a non-JSON HTTP reply could raise before being
recorded. A narrow post-run catch now records one failed call and a sanitized
`invalid_provider_response`; a simulated reply verified this path. It changed
neither the prompt nor the engine. The frozen trace remains the observed run
at the commit above. The deterministic
suite covers trade and grain accounting, legal and illegal moves, hidden
weather, all terminal reasons, bounds and timeouts, and a UI regression.
The observed regression was an impossible 999-acre buy that moved the human
prompt to feeding with a negative grain balance. A failing test captured the
prompt sequence; the corrected prompt reuses the engine's published trade
bounds and asks for a new trade immediately. The
[GitHub Actions workflow](../../.github/workflows/midterm-liffsss.yml) runs
these tests on the submission folder. The checks passed locally on Python
3.12; the GitHub Actions run is pending publication of the branch and PR.

This is a six-pair classroom experiment on one model configuration. It cannot
establish the strength of Gemini generally or separate the effect of the prompt
from the effect of the engine interface. Weather is stochastic and the suite
shares one economy. After this frozen run, the most direct follow-up is to show
the model a grain ledger or ask it to submit one part of the budget at a time,
then compare invalid actions on a newly declared set of seeds. See
[human playtest notes](PLAYTEST.md) for one player's feedback. After playing,
they said they would favor drought-resistant seed above a 50% drought forecast
and stick with it after a low harvest. Their feedback identifies a strategy to
check in a future session with higher forecasts.
