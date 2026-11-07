# Independent rules and evaluation review

A separate Codex reviewer worked read-only using the project’s `rule-change`
skill and the repository rules-reviewer instructions. It read the engine,
public interface, model adapter, evaluator, terminal UI, rule map, suite,
configuration, workflow, tests and saved trace. No live model calls were made.

- No blocker in the game rules or information boundary. A mocked SDK client
  captured the outbound observation and legal-action schema only. The reviewer
  replayed all 12 declared episodes and checked the original source hash,
  public inputs, transitions, outcomes, attempt limits and estimated costs.
- Finding: the initial draft of the map lacked implementation locators for
  D1–D3. The final map links to the exact design specification, implementation
  and acceptance tests, and distinguishes historical rules from adapted limits.
- Finding: `google-genai` can raise `UnknownApiResponseError` on a non-JSON
  provider reply. The original run saw no such error. The post-run fix records
  one counted failed call, no action and no fallback under
  `invalid_provider_response`, without copying the response body. The team
  reproduced and verified the fix with a mocked SDK response.
- Note: the prompt did not state exact starvation thresholds and score weights;
  the heuristic knows the published land weight. The evaluation now discloses
  this and marks state-at-stop scores. The recorded prompt remains unchanged.
- Note: the 15-second SDK timeout is a transport setting, not an independent
  stopwatch around credential refresh. The deterministic timeout test checks
  that a failed call consumes budget and makes no move.
- Note: the README now states Python 3.11+ and uses the tested Python 3.12 in
  local and CI commands.

Human playtesting, GitHub Actions execution and final submission are separate
from the independent code review.
