# Agent team · Hamurabi: Three Harvests

I chose to keep the land, food and planting decisions from *Hamurabi* and make
weather a visible tradeoff. I wanted one crop to be worth planting when the
forecast is good, and another to make a bad harvest less punishing. I kept the
scope to three years so a person could finish a campaign and the agent could
play it in three calls. The branch starts with a separate suite declaration,
`de5cd94`, before either policy was built.

| Role | Work and evidence |
| --- | --- |
| Student, design and release | Set the reconstruction and drought/seed direction. Review the final evidence, observe the human playtest, and decide what to submit. |
| Codex, implementation | Coordinated separate engine and evaluator tasks. The engine task used the rule/source map and wrote rule tests first. The evaluator task implemented the live Vertex player, baseline and bounded runner. See [instructions](AGENTS.md) and [session excerpts](docs/IMPLEMENTATION-SESSION.md). |
| Reusable skill | [rule-change](skills/rule-change/SKILL.md) was invoked by name in the engine implementation session and separately in the independent read-only review. Both traced the new rule to a source label and a test. |
| Independent Codex reviewer | Read the code and tests, reproduced the provider edge case with a mock, and replayed the twelve recorded episodes. [Review findings](review.md). The reviewer had no write role. |
| In-game Gemini player | Selected annual moves from the same public game interface as the baseline. It had no development tools. [Traces](traces/evaluation.json). |

Codex recommended scaling the harvest per acre during implementation. The first proposed yields could not cover a 2,000-grain
food bill for the 100-person starts. Raising both yields preserved the crop
tradeoff and made a three-year win possible. The experiment kept the held-out cases and logged every budget error with the
prompt frozen. The next comparison I would try is to give the
policies the same scoring details and ask Gemini to work from a visible grain
ledger. The [evaluation](EVALUATION.md) and [human playtest notes](PLAYTEST.md)
show the evidence for that decision.
