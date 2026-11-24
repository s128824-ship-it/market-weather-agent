# Market Weather — Daily Brief

Generated: 2026-11-24 09:03 UTC / 2026-11-24 18:03 JST  |  Data mode: live keyless

## Today's weather: Storm (Extreme fear)

Fear & Greed is **9** (Extreme fear), trend steady (7d delta: -4). Source: `/v3/fear-and-greed/latest`.

## Key figures

- Total market cap: **$2.06T** (-1.70% vs yesterday) — `/v1/global-metrics/quotes/latest`
- BTC dominance: **58.50%** / ETH 9.99% — `/v1/global-metrics/quotes/latest`
- Total volume 24h: $100.5B — `/v1/global-metrics/quotes/latest`
- Breadth: **43.0%** of top 100 coins up in 24h (43 up / 57 down) — `/v1/cryptocurrency/listings/latest`
- Altcoin Season Index: **59/100** (Mixed season) — `/v1/altcoin-season-index/latest`
- CMC100: **117.46** (-1.85% 24h) — `/v3/index/cmc100-latest`

## Top movers (24h, volume ≥ $1M only)

### Gainers
| Coin | 24h % | Price | Volume 24h |
|---|---:|---:|---:|
| ATOM (Cosmos) | +9.44% | $1.30 | $42.6M |
| 币安人生 (币安人生) | +5.20% | $0.4713 | $3.4M |
| VET (VeChain) | +4.25% | $0.0049 | $13.0M |
| FF (Falcon Finance) | +3.52% | $0.1056 | $6.0M |
| STABLE (Stable) | +3.37% | $0.0232 | $7.2M |

### Losers
| Coin | 24h % | Price | Volume 24h |
|---|---:|---:|---:|
| PIEVERSE (Pieverse) | -12.34% | $3.14 | $218.6M |
| ZRO (LayerZero) | -11.60% | $1.08 | $99.5M |
| ZEC (Zcash) | -5.44% | $751.04 | $1.0B |
| WLFI (World Liberty Financial) | -5.32% | $0.0409 | $63.3M |
| ETHFI (ether.fi) | -5.21% | $0.4778 | $30.6M |

## Anomalies

- None detected by the deterministic rules.

## Trending section

- Trending section unavailable: /v1/cryptocurrency/trending/latest requires the Startup plan or above (no CMC_API_KEY in this run). Fallback applied — brief generated without it. Detail: plan/key not authorised for this endpoint (HTTP 403, error 1005): An API Key is required for this call.

## Evidence — endpoints called

- `/v3/fear-and-greed/latest` [keyless] HTTP 200 OK
- `/v3/fear-and-greed/historical?limit=30` [keyless] HTTP 200 OK
- `/v1/global-metrics/quotes/latest?convert=USD` [keyless] HTTP 200 OK
- `/v1/cryptocurrency/listings/latest?start=1&limit=100&convert=USD` [keyless] HTTP 200 OK
- `/v1/altcoin-season-index/latest` [keyless] HTTP 200 OK
- `/v3/index/cmc100-latest` [keyless] HTTP 200 OK
- `/v1/cryptocurrency/trending/latest` [keyless] HTTP 403 FAILED — plan/key not authorised for this endpoint (HTTP 403, error 1005): An API Key is required for this call.

---
*Experimental hackathon project. Not financial advice.*
