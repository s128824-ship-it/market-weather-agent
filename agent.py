"""Market Weather Agent — CLI entry point.

Usage:
    python3 agent.py           Live run (keyless by default; keyed extras if
                               CMC_API_KEY is set). Writes output/.
    python3 agent.py --demo    Offline run from fixtures/ (recorded live
                               responses). Writes output/.

Collectors tolerate each other's failure: a failed section is recorded in
`_missing` and the brief is still produced without it.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from cmc_client import CMCClient, CMCError, PlanNotAuthorizedError, CallRecord
import analysis
import brief as brief_mod

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"

# fixture file -> collected key
_FIXTURE_MAP = {
    "fear_greed_latest": "fear-greed-latest.json",
    "fear_greed_historical": "fear-greed-historical.json",
    "global_metrics": "global-metrics.json",
    "listings": "listings-top100.json",
    "altcoin_season": "altcoin-season-latest.json",
    "cmc100": "cmc100-latest.json",
}


def collect_all(client: CMCClient) -> dict:
    """Live collection. Returns data dict; failures land in _missing."""
    data: dict = {"_missing": []}

    def grab(key, fn):
        try:
            data[key] = fn()
        except CMCError as e:
            data[key] = None
            data["_missing"].append(key)
            data[f"_error_{key}"] = str(e)

    grab("fear_greed_latest", lambda: client.get_keyless("/v3/fear-and-greed/latest"))
    grab("fear_greed_historical",
         lambda: client.get_keyless("/v3/fear-and-greed/historical", {"limit": 30}))
    grab("global_metrics",
         lambda: client.get_keyless("/v1/global-metrics/quotes/latest", {"convert": "USD"}))
    grab("listings",
         lambda: client.get_keyless("/v1/cryptocurrency/listings/latest",
                                    {"start": 1, "limit": 100, "convert": "USD"}))
    # Altcoin season: keyless if available, else keyed, else skip gracefully.
    grab("altcoin_season", lambda: client.get_auto("/v1/altcoin-season-index/latest"))
    grab("cmc100", lambda: client.get_keyless("/v3/index/cmc100-latest"))

    # Trending needs Startup plan or above. Attempt it (keyed if a key is set,
    # otherwise keyless, which CMC rejects) and fall back gracefully on 403.
    try:
        if client.has_key:
            data["trending"] = client.get_keyed("/v1/cryptocurrency/trending/latest")
        else:
            data["trending"] = client.get_keyless("/v1/cryptocurrency/trending/latest")
        data["_trending_note"] = "Trending data retrieved."
    except PlanNotAuthorizedError as e:
        data["trending"] = None
        data["_trending_note"] = (
            "Trending section unavailable: /v1/cryptocurrency/trending/latest requires "
            f"the Startup plan or above (no CMC_API_KEY in this run). Fallback applied — "
            f"brief generated without it. Detail: {e}"
        )
    except CMCError as e:
        data["trending"] = None
        data["_trending_note"] = f"Trending section unavailable this run: {e}"
    return data


def load_fixtures() -> tuple[dict, list[dict]]:
    """Offline data from recorded fixtures + synthetic call records."""
    data: dict = {"_missing": []}
    records = []
    endpoint_of = {
        "fear_greed_latest": "/v3/fear-and-greed/latest",
        "fear_greed_historical": "/v3/fear-and-greed/historical?limit=30",
        "global_metrics": "/v1/global-metrics/quotes/latest?convert=USD",
        "listings": "/v1/cryptocurrency/listings/latest?start=1&limit=100&convert=USD",
        "altcoin_season": "/v1/altcoin-season-index/latest",
        "cmc100": "/v3/index/cmc100-latest",
    }
    for key, fname in _FIXTURE_MAP.items():
        path = FIXTURES / fname
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            data[key] = payload.get("data")
            records.append(CallRecord(endpoint_of[key], "fixture", 200, True, "0",
                                      "recorded live response").as_dict())
        else:
            data[key] = None
            data["_missing"].append(key)
    data["_trending_note"] = (
        "Trending section unavailable in demo mode: trending endpoints require the "
        "Startup plan or above. Fallback applied — brief generated without it."
    )
    return data, records


def run(demo: bool, outdir: Path) -> dict:
    if demo:
        data, records = load_fixtures()
        mode = "demo (fixtures recorded from live keyless API)"
    else:
        client = CMCClient()
        data = collect_all(client)
        records = [r.as_dict() for r in client.records]
        mode = "live keyless" + (" + keyed extras" if client.has_key else "")

    result = analysis.analyse(data)
    meta = {
        "generated_at": datetime.now(timezone.utc),
        "endpoints": records,
        "mode": mode,
    }
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "brief.md").write_text(brief_mod.render_markdown(result, meta), encoding="utf-8")
    (outdir / "brief_ja.md").write_text(brief_mod.render_markdown_ja(result, meta), encoding="utf-8")
    (outdir / "dashboard.html").write_text(brief_mod.render_dashboard(result, meta), encoding="utf-8")
    return {"analysis": result, "meta": meta, "records": records}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Market Weather Agent")
    ap.add_argument("--demo", action="store_true", help="offline run from fixtures/")
    ap.add_argument("--out", default=str(ROOT / "output"), help="output directory")
    args = ap.parse_args(argv)
    res = run(demo=args.demo, outdir=Path(args.out))
    r = res["analysis"].get("regime")
    print(f"mode: {res['meta']['mode']}")
    print(f"regime: {r['weather']} ({r['label']}, F&G {r['fear_greed']})" if r else "regime: unavailable")
    print(f"missing: {res['analysis']['missing'] or 'none'}")
    print(f"outputs written to {args.out}/ (brief.md, brief_ja.md, dashboard.html)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
