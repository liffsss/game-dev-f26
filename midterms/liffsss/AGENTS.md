# Hamurabi: Three Harvests

Work inside this submission folder. Use `skills/rule-change/SKILL.md` for any
change to an action, rule, observation, or outcome. Treat the root starter as
course infrastructure. Do not copy historical game code, text, or images.

The engine alone owns weather, resources, rules, and score. The runtime model
receives a public observation and an action schema through the player module.
It never gets the seed, an engine object, tools, or answer keys. Never give it
credentials. Run `python -m unittest discover -s tests -v` from this folder.
Live runs require an explicit Vertex option and local credentials. Keep secrets
out of all artifacts. Do not change the declared suite based on its results.

The independent reviewer operates read-only and sends findings to the
implementation team. The student decides release and submission.
