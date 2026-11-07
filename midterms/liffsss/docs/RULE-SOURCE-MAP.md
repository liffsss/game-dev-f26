# Rule and source map

The reference is David H. Ahl’s “Hammurabi” in *BASIC Computer Games: Microcomputer Edition* (Creative Computing, 1978), printed pp. 78–79. The book credits a FOCAL predecessor and Ahl’s BASIC conversion and ten-year assessment. See the [archived scan](https://www.mocagh.org/softguide/basicgames.pdf) and Atari Archives [p. 78](https://www.atariarchives.org/basicgames/showpage.php?page=78) and [p. 79](https://www.atariarchives.org/basicgames/showpage.php?page=79). The original publication is copyrighted. The listing served as evidence of game behavior. This project uses newly written code and text and takes no artwork from the book.

| ID | Evidence and source locator | Behavior in this build and implementation locator |
| --- | --- | --- |
| R1 | `code` · Ahl p. 79, BASIC lines 310–350 | Buy or sell land for grain at the announced unit price. The trade changes land and grain together. [Rules](../hamurabi/game.py#L135-L176) |
| R2 | `code` · Ahl p. 79, BASIC lines 410–430 and 539–555 | Feed from stored grain at 20 bushels per person. Unfed people die. Losing strictly more than 45% of the starting population in one year ends the term. [Rules](../hamurabi/game.py#L147-L175), [boundary test](../tests/test_game.py#L112-L122) |
| R3 | `code` · Ahl p. 78, opening description and sample play, and p. 79, BASIC lines 440–511 and 515–530 | Spend grain on seed, constrain planted acres by land and labor, and add harvest to storage. [Rules](../hamurabi/game.py#L147-L155), [validation](../hamurabi/game.py#L178-L195) |
| D1 | `design` · [Weather and crops](#weather-and-crops) | Expose the current drought percentage. Use distinct planting costs and normal and dry yields. The engine draws one weather outcome after each accepted plan. [Constants](../hamurabi/game.py#L12-L24), [rules](../hamurabi/game.py#L147-L158), [weather test](../tests/test_game.py#L90-L97) |
| D2 | `design` · [Cases and outcomes](#cases-and-outcomes) | Play three years or until famine. Apply the reserve target, death threshold, and score below. [Cases](../suite.json), [reset](../hamurabi/game.py#L47-L61), [score](../hamurabi/game.py#L121-L133), [terminal test](../tests/test_game.py#L11-L40) |
| D3 | `design` · [Plan and public interface](#plan-and-public-interface) | Apply the four-field plan atomically. An invalid active-turn plan increments its counter and leaves the year, weather and resources intact. [Boundary](../hamurabi/game.py#L73-L119), [validation](../hamurabi/game.py#L135-L195), [refusal test](../tests/test_game.py#L42-L57) |

## Weather and crops

| Crop | Seed cost per acre | Normal harvest per acre | Drought harvest per acre |
| --- | ---: | ---: | ---: |
| Regular | 2 | 30 | 5 |
| Resilient | 3 | 25 | 20 |

Units are bushels. The resilient crop costs more and returns less in normal weather, but preserves more of the harvest during a drought. The higher harvest numbers fit the roughly 100-acre cases and a 2,000-bushel food bill for 100 people. Each case specifies three forecast percentages. The engine uses a dedicated seeded random stream and draws exactly once per accepted year. The observation shows the active forecast and the most recent completed harvest, including its realized weather. The evaluator keeps the seed, random stream, and future outcomes private.

## Cases and outcomes

[The suite](../suite.json) defines the initial population, land, stored grain, and forecast sequence. Each case starts with 100 people. No plague, immigration, births, or rats are simulated. The three-year horizon and one source of chance keep the focus on feeding and crop choice.

The state after harvest contains the number fed, land after trade, and `old grain − net spending + harvest`. A year with starvation above 45% ends in `famine`. At the end of Year 3, `secured` requires at most 10 cumulative deaths and at least 20 bushels per surviving person in storage. Other Year 3 finishes are `shortfall`. Score is `20 × population + grain + 10 × land − 40 × cumulative deaths`.

## Plan and public interface

The fixed price is 18, 22, then 25 bushels per acre. `trade` buys positive acres or sells negative acres within ±20 and the land owned. `feed` counts people from zero through the year's starting population. `regular` and `resilient` are nonnegative acreage. The sum must fit land after trade and two acres per person at the start of the year. Buying, feeding, and both seed costs, minus sale revenue, must fit the stored grain. An exact budget is legal. Harvest can only fund a later plan.

The runner calls `reset(seed, case)`, `observe("ruler")`, `legal_actions("ruler")`, `step("ruler", action)`, and `outcome()`. `legal_actions` publishes individual field bounds and describes the coupled constraints. The engine validates those constraints before resolving weather. Public snapshots are detached from the engine, so mutating one cannot change the campaign. A completed term accepts no further plans.
