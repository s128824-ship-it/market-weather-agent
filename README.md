# Market Weather Agent

A deterministic AI agent that reads live CoinMarketCap data and writes the
daily market brief the way a weather forecast reads: the market regime *is*
the weather (Storm, Rain, Overcast, Sunny, Heatwave). Every claim in the
brief carries the figure it rests on and the CoinMarketCap endpoint that
figure came from — no vibes, only evidence. The same analysis is exposed as
an MCP server, so other AI agents can ask the market questions directly.

Built for **Build with CMC: API Hackathon Round 2** (DoraHacks), track:
**AI Agents and Automation**.

> Experimental hackathon project. Not financial advice.

## Quick start

Zero setup — the agent runs against CoinMarketCap's **keyless public API**:

```bash
python3 agent.py            # live run -> output/brief.md, brief_ja.md, dashboard.html
python3 agent.py --demo     # fully offline run from recorded fixtures in fixtures/
python3 -m unittest discover -s tests
python3 mcp_server.py       # MCP server on stdio (JSON-RPC)
```

Optional keyed mode (unlocks plan-gated endpoints such as trending):

```bash
export CMC_API_KEY=your_key_here   # or copy .env.example to .env locally
python3 agent.py
```

The key is read from the environment only. It is never printed, logged, or
committed (see `.gitignore`). Keyless calls never send the key header.

**Requirements:** Python 3.10+, standard library only. No pip installs —
judges can run this anywhere Python runs.

## What it produces

| Output | What |
|---|---|
| `output/brief.md` | English daily brief: regime, key figures, top movers, anomalies, evidence list |
| `output/brief_ja.md` | Japanese version of the same brief |
| `output/dashboard.html` | Single self-contained HTML dashboard (inline CSS, no external assets): regime gauge, key figures, movers tables, anomalies |
| `evidence/live-run-log.txt` | Verification log of a real live run: endpoint, HTTP status, timestamp, 1-line summary per call |

## Architecture

```
                ┌─────────────┐   keyless (default)
                │ cmc_client  │──────────────────────► CMC public-api
                │  urllib,    │   keyed (CMC_API_KEY) ► CMC pro-api
                │  retry, 403 │        ▲
                └──────┬──────┘        │ plan-gated endpoints (trending)
        collectors (agent.py)          │ fall back gracefully + note
                │  partial failure OK — missing sections are marked
                ▼
                ┌─────────────┐
                │ analysis.py │  deterministic, no LLM:
                │             │  regime · breadth · movers · anomalies
                └──────┬──────┘
              ┌────────┴─────────┐
              ▼                  ▼
        ┌───────────┐     ┌─────────────┐
        │ brief.py  │     │ mcp_server  │  stdio JSON-RPC:
        │ EN/JA/HTML│     │  4 tools    │  weather / F&G trend /
        └───────────┘     └─────────────┘  movers / coin snapshot
```

## Endpoint table

Keyless base: `https://pro-api.coinmarketcap.com/public-api` ·
Keyed base: `https://pro-api.coinmarketcap.com`

| Endpoint | Mode | What it feeds |
|---|---|---|
| `GET /v3/fear-and-greed/latest` | keyless | Regime classification (current sentiment) |
| `GET /v3/fear-and-greed/historical?limit=30` | keyless | 7d/30d sentiment trend, swing anomaly (≥10 pts) |
| `GET /v1/global-metrics/quotes/latest?convert=USD` | keyless | Total market cap, BTC/ETH dominance, 24h mcap change (≥3% anomaly) |
| `GET /v1/cryptocurrency/listings/latest?start=1&limit=100&convert=USD` | keyless | Breadth (% of top 100 up 24h), top movers (filtered to 24h volume ≥ $1M) |
| `GET /v1/altcoin-season-index/latest` | keyless → keyed → skip | Altcoin Season Index section |
| `GET /v3/index/cmc100-latest` | keyless | CMC100 index value + 24h change |
| `GET /v1/cryptocurrency/trending/latest` | keyed (Startup+) | Trending section — on HTTP 403 (error 1005/1006) the agent falls back and notes it in the brief |
| `GET /v2/simple/price?symbol=…` | keyless | MCP `get_coin_snapshot` |
| `GET /v2/cryptocurrency/quotes/latest?symbol=…` | keyed fallback | MCP `get_coin_snapshot` when the keyless route fails and a key is set |

Analysis rules (all deterministic): regime bands on Fear & Greed
(0–24 Extreme fear/Storm, 25–44 Fear/Rain, 45–55 Neutral/Overcast,
56–74 Greed/Sunny, 75–100 Extreme greed/Heatwave); trend from the 7-day
delta (±5); anomalies for a ≥10-point Fear & Greed swing in 7 days, a ≥3%
total-market-cap move in 24h, and BTC dominance at extremes (≥60% or ≤40%).

## MCP tools

| Tool | Returns |
|---|---|
| `get_market_weather` | Regime, global figures, breadth, altcoin season, CMC100, anomalies |
| `get_fear_greed_trend` | Fear & Greed now vs 7d/30d ago, trend direction |
| `get_top_movers` | Gainers/losers (24h, volume ≥ $1M), `n` per side |
| `get_coin_snapshot` | USD price for a symbol (keyless simple-price, keyed quotes fallback) |

Smoke test: send `initialize`, then `tools/list`, then `tools/call` — one
JSON-RPC object per line on stdin; responses arrive on stdout.

## API feedback (for CoinMarketCap)

**What the API made possible**

- The keyless public API is a genuinely zero-friction on-ramp: four of CMC's
  proprietary indices (Fear & Greed latest *and* historical, Altcoin Season,
  CMC100) plus global metrics and listings are reachable with no signup at
  all, which made a fully reproducible, judge-runnable submission possible.
- Fear & Greed *historical* being keyless is what turns a sentiment number
  into a trend — the brief's regime-trend and swing-anomaly rules exist
  because that endpoint is open.
- `/v2/simple/price` being keyless gives agents a cheap single-coin lookup
  without burning full quotes calls.

**Where it got in the way**

- Trending (`/v1/cryptocurrency/trending/latest`, `gainers-losers`) is gated
  behind the Startup plan. In keyless mode the call returns HTTP 403 with
  error 1005 ("An API Key is required") rather than a plan-specific code —
  distinguishing "no key" (1005) from "key but wrong plan" (1006) has to be
  handled defensively. We fall back and say so in the brief.
- Fear & Greed historical cadence is daily with `limit` counting points, and
  the semantics (is `limit=30` 30 days?) are only obvious after inspecting
  real responses; a `start`/`end` or explicit `interval` note in the docs
  would help.
- Unknown or wrong paths can return **HTTP 200 with `status.error_code` 500**
  ("system is busy") instead of a 404-style error, so clients must check the
  envelope, not just the HTTP status. (Found while probing index paths:
  the correct ones are `/v1/altcoin-season-index/latest` and
  `/v3/index/cmc100-latest` — the dash-vs-slash difference is easy to miss.)
- Global metrics exposes the 24h market-cap change only as
  `total_market_cap_yesterday_percentage_change` inside the USD quote —
  discoverable, but not where a first-time user looks for it.

## Judging criteria mapping

| Criterion (weight) | How this project answers it |
|---|---|
| **Does it work (30)** | Live-verified end to end on 2026-11-18: 6/6 core endpoints HTTP 200 in `evidence/live-run-log.txt`; `--demo` mode reproduces the full pipeline offline from recorded real responses; 19 unit tests pass. |
| **Agent quality & reliability (25)** | Deterministic (no LLM) analysis; per-collector failure isolation — one dead endpoint degrades the brief, never kills it; one retry with backoff on 429/5xx; envelope error codes checked, not just HTTP status; plan-gated endpoints fall back with an explicit note. |
| **Creative use of the API (20)** | Four proprietary CMC indices (Fear & Greed latest+historical, Altcoin Season, CMC100) combined with global metrics and listings into a weather-regime model; the same evidence-linked analysis is served to other agents over MCP — an API *for agents, built on the API*. |
| **Code quality & documentation (15)** | Stdlib-only, ~5 small modules, typed dataclasses, fixture-based unit tests (regime, breadth, movers filter, brief rendering, client auth/retry/403 handling), this README with a full endpoint table and honest API feedback. API key never logged or committed. |
| **Presentation (10)** | The brief reads like a weather forecast in English *and* Japanese; a single-file HTML dashboard with a sentiment gauge, movers tables and an evidence section; every number in every output cites its endpoint. |

## Files

```
ANCHOR.md          design anchor written before the code
agent.py           CLI + collectors        cmc_client.py  API client
analysis.py        deterministic analysis  brief.py       EN/JA/HTML renderers
mcp_server.py      MCP server (stdio)      fixtures/      recorded live responses
tests/             unittest (19 tests)     evidence/      live-run log
output/            latest generated briefs + dashboard
```

> Experimental hackathon project. Not financial advice. Market figures are
> snapshots from the CoinMarketCap API at generation time and change
> continuously; anyone acting on this output does so at their own risk.
