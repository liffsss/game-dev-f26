---
name: rule-change
description: Tie a Hamurabi rule or interface change to evidence and a deterministic acceptance trace. Also supports read-only verification.
---

1. Open `docs/RULE-SOURCE-MAP.md` and identify the affected rule. Keep the
   original evidence label or use `design` for a deliberate adaptation. Do
   not turn an inference into evidence by relabeling it.
2. In implementation mode, write the acceptance test first and save the
   failure reason. Cover one refused move and whether it consumes weather,
   changes resources, or exposes a secret. Modify the engine, update the map
   locator, and run `python -m unittest discover -s tests -v` from this folder.
3. In review mode, leave files alone. Read the map, test, and engine together.
   Reproduce a legal and a refused move or run the tests. Inspect the public
   inputs the model actually receives and verify that failed calls consume
   the budget. Report findings with file and line and any unverified claims.
4. In both modes, record the rule ID, evidence, commands, and what remains
   uncertain. The student makes the release decision.
