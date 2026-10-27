# Interval — chat transcript

25–27 October 2026, UK time. The Nebius API key pasted in this chat is not included here. It lives only in the gitignored `hackathon/.env`.

---

## Sunday 25 October, 3:44pm — product positioning

**You**

Understand this repo’s product positioning, then review six opportunities:

1. A derived-metrics layer (the “F1 analytics standard”). Compute things nobody publishes consistently: fuel-corrected race pace, tyre degradation curves per compound and track, true teammate deltas, pit-stop loss per circuit, overtaking difficulty, quali-to-race conversion. Publish them as clean tables or an API. Strongest positioning play, because Fast-F1 gives ingredients and you’d be selling the dish. Defensible, since the methodology becomes IP.
2. A 2026-regulation baseline. The 2026 rules changed the cars (bigger electric share, active aero), so historical comparisons are broken. A vault that separates eras and tracks how energy deployment shows up in lap and speed-trap data. The “why now”.
3. A natural-language query layer. An LLM over the SQL schema. Strong demo, easy to copy unless it sits on option 1’s metrics.
4. Fantasy and prediction tools. Clearest path to a paying audience, seasonal and noisy.
5. A content engine. Auto-generated weekly charts and insights. Audience-building rather than product-building.
6. An open dataset/warehouse for researchers. Versioned Parquet/DuckDB snapshots. Low effort, low differentiation.

Then research https://onboarding.tldr.tech/. Where could this idea go? Options to reimagine the proposition together.

**Reply**

The repo carries three positionings that do not agree.

| Surface | Claim | State |
| --- | --- | --- |
| README, docs, worker | F1 Data Library: ingest, BigQuery warehouse, Kaggle export. Live SignalR on a residential host, FastF1 failsafe on Cloud Run, one source per session. | Real. Almost all the engineering is here. |
| About page | Interval.ai / INPLAY: freeze the race at the moment of consequence, the fan makes the pit-wall call, then reality plays out. | Copy only. Nothing implements a decision, a choice, or a score. |
| Overview page | Live F1 Data Sync: a sub-100 ms API, “the data layer behind Interval.ai”. | Aspirational. The live APIs are a timing board, a status strip, and a BigQuery dump into a visualiser iframe. |

Around those: a mock magazine, placeholder Pitwall and Factory dashboards, and a referral-gated signup that logs the user out after creating the account. The asset that exists is narrower: a reliable capture of 2026 sessions at lap and 0.5 s telemetry resolution, with sectors, pit in/out, position, track status, compound, tyre age and stint. Weather is switched off. Fuel and ERS deployment are not in any public channel.

Review of the six:

1. Derived metrics are the strongest, with two corrections. The methodology is not very defensible as secret IP; consistency, versioning, freshness and coverage are the moat. Several ingredients are missing or must be modelled: fuel, weather, overtakes. Multi-year claims need a 2022–2025 FastF1 backfill.
2. The 2026 baseline is timely, but the first season under the rules is nearly over. There is no public energy-deployment channel. Inferred from speed traces is an honest claim.
3. Natural language without option 1 is a demo. Ship it as an MCP server over the metric definitions.
4. Fantasy is the clearest paying audience and the weakest fit. Treat it as a customer of option 1.
5. Content is a front door, not a substitute for a product. The TLDR research changes its rank.
6. The open dataset already exists (Kaggle listing 9485317). Keep it. Add versioned Parquet and DuckDB.

Constraint across all six: the live capture runs on an F1 TV bearer. Selling raw rows is a different risk from publishing a Kaggle CSV. Derived metrics are the safer thing to charge for.

What onboarding.tldr.tech actually is: not a signup wizard. A public, no-login, ranked feed of about 50 stories, each with a one-line topic, a summary, a category, and facts that carry source links. The payload also has tier, feed score, rank score, relevance, topic-mate count, and a judgment justification. TLDR has rebuilt itself from “editors write a newsletter” into a pipeline that clusters sources, extracts facts with provenance, scores them, and renders a feed. The email is one channel. The feed is the proof, shown before the ask.

Where it could go: a moment layer for F1. Every session becomes ranked moments, each backed by the laps that justify it, consumed as a feed, a newsletter, a chart, an MCP endpoint, or a game. That reconciles the three identities in the repo.

Options, one first screen each:

- **A. Interval, the moment feed.** This weekend’s ranked moments, no login, one email field.
- **B. The F1 analytics standard.** Metric tables with definitions and version numbers.
- **C. Hindsight, the decision game** the About page already promises.
- **D. Agent-native open warehouse.** MCP, DuckDB snapshots, an AI-instructions page.
- **E. Pitwall-in-a-box for media.** A chart pack five minutes after the flag.

Recommendation: lead with A, build B underneath as the scoring layer, ship C as the interaction on each card, expose D from day one, hold E and fantasy.

---

## Sunday 25 October, 3:57pm — TLDR as a trend barometer

**You**

Reference https://tldr.tech/ to understand where tech trends are going, and give an angle for where the F1 proposition should be positioned.

**Reply**

Read of the front page plus recent Tech, AI, and Data editions (14–23 October). Ten patterns, the ones that matter marked.

1. Agents are becoming the consumer of software. Products are being redesigned so an agent can use them.
2. The frontier is moving from generation to decisions. Calibrated choices between options, not paragraphs.
3. Application code is no longer the asset. TLDR Data: “the durable asset shifts from application code to a governed historical record of entities, state changes, and provenance.”
4. Request-fulfilment analytics is dying. Decision-support analytics is not.
5. Being the cited number is the new SEO. “Publish stats, get cited.”
6. Specialist small models beat frontier models on narrow jobs.
7. Freshness and provenance are product features. The residential live capture is a freshness advantage datacentres cannot copy.
8. Trust and verifiability are being paid for.
9. Media is losing the attention war to AI summaries. Experiences that involve the person push back.
10. Voice and on-device models are maturing. Secondary here.

Applied to the six options: clean tables, a chat UI, and Parquet snapshots are request fulfilment. The definitions, the history, and the provenance survive. The object that fits the surviving shape, and that nobody has structured, is the pit-wall decision.

Angle: **Interval is the decision record for motorsport.** Every session becomes a timestamped record of decisions, with the options that were open, the call that was made, what happened next, and the laps that prove it. Humans play it. Agents query it. Models train on it.

What that asks of the repo: a `decisions` table, a detection job, a 2022–2025 backfill, three views (feed, game, MCP), one public name, and dropping the referral gate, the Factory, and the mock articles.

---

## Sunday 25 October, 4:09pm — Oakley and a causal instrument

**You**

That is not sexy enough.

1. Look at https://www.oakleycapital.com/ for what gets investment.
2. Ground the suggestions in what causal analysis (https://github.com/py-why) brings: creating a new instrument.

**Reply**

Oakley’s own filings, not the homepage. They fund founder-led businesses with recurring revenue, secular demand, and value from specialist expertise, proprietary data, trusted brands, regulation, or embedded workflows. They name B2B information platforms as a niche. Three portfolio companies are the template:

- **TechInsights.** The authoritative semiconductor intelligence platform. Subscription growth, high retention, acquires adjacent data shops.
- **Graphwise.** A semantic layer, bought because LLMs are weak at factual consistency and at explaining how they reached a conclusion.
- **XTEL.** Software that turns trade-promotion data into faster, better decisions.

They do not fund datasets, dashboards, newsletters, or games. They fund the authoritative measurement house for an industry.

py-why (DoWhy, EconML, causal-learn) answers why, not what. Descriptive F1 stats are what agents will commoditise. Causal estimates with stated assumptions and refutation tests are a methodology, which is what TechInsights sells.

“Instrument” in both senses:

- Econometric. Grid penalties, safety-car and VSC timing, red flags, teammate pairs, and the 2026 reset are natural experiments already in the tables.
- Measurement. The output is a set of numbers the sport has argued about and never published consistently: how much of a result is the driver, the car, the pit wall, and luck.

Reimagined proposition: **Interval is the performance intelligence platform that separates driver, car, strategy and luck.**

Three flagship instruments:

1. **Driver Value.** Tenths per lap attributable to the driver, independent of the car.
2. **Strategy Alpha.** The counterfactual value of each pit-wall decision versus the best option available at the time.
3. **Track Position Price.** What a grid slot and a position on track are worth at each circuit, under the 2026 cars.

Who pays, in Oakley’s order: teams and power-unit manufacturers, driver managers and sponsors, broadcasters, then betting and fantasy, then media. Consumer last.

Where it can fail: small N, contestable identification, licensing before the first paid contract, and a hard enterprise sales motion. Publish the uncertainty bands. Do not hide the assumptions.

---

## Sunday 25 October, 4:37pm — the proposition and the front door

**You**

Build a winning proposition with these attributes:

- B2B2C
- A measurement standard
- A py-why instrument: a framework to experiment, measure, test, and learn from outcomes
- A proprietary data vertical
- Speed: faster, more accurate decision making

Give options. An interesting front door that gets into investor discussions while the back end is being built.

**Reply**

**Interval is the independent measurement standard for motorsport performance.** It uses causal inference to separate driver, car, strategy and luck, publishes the results as versioned instruments within minutes of the flag, and licenses them to the teams, broadcasters and platforms that fans already use.

The name does the work: an interval is the gap on the timing screen, and every number carries a confidence interval. Tagline: “Every number comes with one.”

| Attribute | How it shows up |
| --- | --- |
| B2B2C | Instruments appear inside broadcasts, articles, fantasy apps and team apps with a “Powered by Interval” mark. The public index makes the badge worth licensing. |
| Measurement standard | Open methodology, version numbers, uncertainty bands, published refutation tests, a changelog. Independence is the difference from AWS F1 Insights, which is a sponsor’s product. |
| PyWhy instrument | Model, identify, estimate, refute, publish. F1’s natural experiments are the identification strategies. Teams get the same loop as a tool. |
| Proprietary data vertical | Residential live capture, the decision record, structured FIA car-presentation and penalty documents, and the estimates themselves. F1 first, then F2, F3, WEC, IndyCar, MotoGP. |
| Speed | Verdicts in minutes. The sport’s decision cycle is weekly. The instrument matches it. |

Front doors, each shippable on current assets:

| # | Front door | Ships on | Investor hook |
| --- | --- | --- | --- |
| 1 | Driver Value Index | Backfill only | “The FICO score of F1” |
| 2 | Upgrade Verdict: “Did it work?” | Backfill plus FIA documents | “Independent ROI on a $135M cost cap” |
| 3 | Pit Wall Scoreboard plus Make the Call | Live capture | Engagement plus a labelled dataset of human judgement |
| 4 | The 2026 Causal Atlas | Backfill | “What the rules actually did” |
| 5 | Interval Lab | Backfill | “The xG moment, with a reference implementation” |

Lead with 1 and 2 from one pipeline. Ship 5 beside them. Both run on backfill, so neither waits on the live capture. Build 3 once decision detection exists. Use 4 as a one-off at the end of the season.

For investor conversations, the artefacts that matter: a live public index with two or three press pickups, the methodology note with refutation tests, a one-page comparison with AWS F1 Insights, one letter of intent to embed the index, and an expansion slide across series.

Three things to settle: which number goes first, whether “independent” means never taking a team or rights-holder as a shareholder, and the licensing position before the first paid embed.

---

## Sunday 25 October, 4:43pm — a downloadable page

**You**

Make this page available as a download via psf.

**Reply**

Read as PDF. A styled page was started (`docs/interval-proposition.md` on `cursor/proposition-pdf-download-c187`). The PDF was not finished. The next message replaced that task. The draft markdown is still untracked and is not part of the hackathon branch.

---

## Sunday 25 October, 5:02pm — the hackathon charter

**You**

Charter a way forward: enter the Nebius × NVIDIA Global AI Hackathon (https://nebiusglobalaihackathon.devpost.com/), build with NVIDIA Nemotron (https://developer.nvidia.com/topics/ai/nemotron), for an AI-agents use case (https://nebius.com/solutions/ai-agents).

Thinking: we are building the back end for the endpoint solution that product is selling. Thoughts?

**Reply**

The hackathon entry is the endpoint. The measurement backend stays private behind tool calls.

Facts from the pages:

- Deadline: Friday 30 October 2026, 5:00pm UK time. About 27,000 participants. Judging 1–15 December. Winners around 11 January 2027. The demo has to stay up, free, through judging.
- Runtime calls must go to Nebius Token Factory or Nebius AI Cloud. The same model via OpenRouter does not count.
- At least one NVIDIA open model. The Apps and Agents track says Ultra for hard reasoning and Nano or Super for fast calls.
- A working demo URL, a public repo with an Apache, MIT, or MPL license, a README, and a YouTube demo of three minutes or less.
- The F1 Data Library already exists. The rules require a written note of what was built during the submission window.
- Nebius sells the agent runtime and a blueprint: orchestration, cited retrieval, live grounding, simulation, evals. Their own case study: architecture beat the model.
- Nemotron is the open model family for that pattern. Nano and Lightning for cheap steps, Super and Ultra for planning and verification.

The inversion: Nebius and NVIDIA score an agent someone can use. Interval owns the instrument that makes the number true. The submission is the endpoint. The backend appears only as tools the agent is not allowed to skip. v0 of a tool can be a within-teammate delta on a frozen export, labelled as an estimate that has not yet been refuted.

What to submit. Track: Best Apps and Agents. One screen: a question in, a card out. Three tools: `teammate_delta`, `pit_window`, `evidence`. Two models on Token Factory, server-side only. Leave Tavily out unless there is a spare hour.

What stays private: the live capture, the F1 TV token, the BigQuery credentials, the full telemetry. The December judges will not have the home machine.

Five days:

| When | Outcome |
| --- | --- |
| Sunday night | Token Factory key. One Nano call and one Super call succeed. |
| Monday | The three tools against a frozen slice. A missing lap returns empty. |
| Tuesday | The agent loop: plan, call tools, refuse to answer without them, format the card. |
| Wednesday | The one screen, deployed, including one scripted “make the call” moment. |
| Thursday | Video, license, README, the pre-existing-project note, feedback on Token Factory. Submit before 5:00pm UK on Friday. |

This is not the Oakley meeting. It is a Nebius and NVIDIA design-partner conversation. With 27,000 entries the cash prize is a lottery. The thing to keep is a URL.

---

## Sunday 25 October, 6:36pm — start tonight’s work

**You**

Create a new branch for the hackathon and start the work for tonight. Tell me the next steps.

**Reply**

Branch `cursor/nebius-hackathon-agent-c187`. Pull request [#23](https://github.com/JustSteve1/F1/pull/23).

`hackathon/` holds a Token Factory client. Nano formats. Super plans and verifies. Ultra is behind `--with-ultra`. Nine unit tests pass without a key. The live capture and credentials are not in this directory.

Your step that night:

1. Create a Token Factory API key. Billing country is the usual blocker.
2. `cd hackathon && cp .env.example .env` and set `NEBIUS_API_KEY`.
3. `python3 -m interval_agent.smoke`

A good run prints two `OK` lines. Paste them back.

Model ids:

| Role | Model id |
| --- | --- |
| format | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` |
| plan, verify | `nvidia/nemotron-3-super-120b-a12b` |
| opt-in | `nvidia/Nemotron-3-Ultra-550b-a55b` |

---

## Sunday 25 October, 6:45pm — smoke test

**You**

Run steps 2 and 3. The API key was pasted in chat, with an instruction to keep it safe, and to say when everything is complete.

**Reply**

The key was written only to `hackathon/.env` (mode 600). That file is gitignored and is not in pull request #23. The key is not repeated in this transcript.

| Model | Result | Latency | Tokens |
| --- | --- | --- | --- |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | OK, replied `ready` | 652 ms | 23 in, 57 out |
| `nvidia/nemotron-3-super-120b-a12b` | OK, replied `ready` | 638 ms | 23 in, 47 out |

Tonight’s step was complete.

---

## Monday 26 October, 7:30am — the day’s work

**You**

It’s Monday. Remind me what we’re doing today and why.

**Reply**

Today: the three tools the agent is allowed to quote.

| Tool | What it returns |
| --- | --- |
| `teammate_delta` | A driver against their teammate, in tenths per lap, with the number of laps behind the figure |
| `pit_window` | Pit in and pit out, laps lost, and the position before and after |
| `evidence` | The lap rows that justify either number |

They run on a frozen slice committed with the hackathon code, not on the live capture. A missing lap returns empty. The within-teammate delta is the first, honest version of Driver Value: an estimate, labelled as not yet refuted.

Why: the entry is an agent endpoint, and the claim is that every tenth comes from a measurement. Nano and Super already answer. These tools are the contract that stops the model inventing a lap time.

Tuesday is the agent loop. Wednesday is the one screen. Thursday is the video and the Devpost submission. Deadline: Friday 30 October, 5:00pm UK time.

---

## Tuesday 27 October, 11:58am — this file

**You**

Make this chat downloadable as an .md file.

**Reply**

This file.
