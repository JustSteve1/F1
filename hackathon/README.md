# Interval agent (Nebius × NVIDIA hackathon)

The endpoint a producer or strategist asks a question of. Nemotron plans and formats. Every number has to come back from a tool. This directory is the hackathon submission slice. The live capture, warehouse credentials, and F1 TV token stay outside it.

Track: Best Apps and Agents. Deadline: Friday 30 October 2026, 5:00pm UK time.

## Tonight

Prove Token Factory can serve Nemotron Nano and Nemotron Super from this machine.

```bash
cd hackathon
cp .env.example .env
# put NEBIUS_API_KEY in .env — the console shows the key once
python3 -m interval_agent.smoke
```

A good run prints two `OK` lines, one per model, with latency and token counts. `--with-ultra` adds Nemotron 3 Ultra and costs more; leave it off unless Nano and Super already succeed.

```bash
python3 -m unittest interval_agent.test_token_factory
```

Model ids, from the Token Factory catalog:

| Role | Model id |
| --- | --- |
| format (fast) | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` |
| plan, verify | `nvidia/nemotron-3-super-120b-a12b` |
| opt-in | `nvidia/Nemotron-3-Ultra-550b-a55b` |

Calls go to `https://api.tokenfactory.nebius.com/v1/chat/completions`. The same weights on another host do not meet the hackathon rule.

## What this repo already was

The F1 Data Library (live timing ingest, BigQuery, Kaggle export) predates the submission window. The agent, this client, and the tool contract are the work added for the hackathon.

## License

MIT, for this directory. See [LICENSE](./LICENSE).
