"""Deterministic market analysis — no LLM, no randomness.

Input: the `collected` dict produced by agent.collect_all() / fixtures.
Every statement produced carries the figure it rests on and the endpoint
that figure came from, so the brief can cite its evidence inline.
"""
from __future__ import annotations

EP_FG_LATEST = "/v3/fear-and-greed/latest"
EP_FG_HIST = "/v3/fear-and-greed/historical"
EP_GLOBAL = "/v1/global-metrics/quotes/latest"
EP_LISTINGS = "/v1/cryptocurrency/listings/latest"
EP_ALTSEASON = "/v1/altcoin-season-index/latest"
EP_CMC100 = "/v3/index/cmc100-latest"

MIN_MOVER_VOLUME_USD = 1_000_000

# (upper bound inclusive, regime label, weather metaphor)
_REGIME_BANDS = [
    (24, "Extreme fear", "Storm"),
    (44, "Fear", "Rain"),
    (55, "Neutral", "Overcast"),
    (74, "Greed", "Sunny"),
    (100, "Extreme greed", "Heatwave"),
]


def classify_regime(fg_value: int) -> tuple[str, str]:
    """Fear & Greed value -> (regime label, weather metaphor)."""
    for upper, label, weather in _REGIME_BANDS:
        if fg_value <= upper:
            return label, weather
    return "Extreme greed", "Heatwave"


def trend_word(delta: float | None) -> str:
    if delta is None:
        return "unknown"
    if delta >= 5:
        return "improving"
    if delta <= -5:
        return "deteriorating"
    return "steady"


def _fg_history_points(hist_data) -> list[dict]:
    """Normalise historical fear/greed to oldest->newest list of dicts."""
    if not hist_data:
        return []
    points = []
    for row in hist_data:
        try:
            points.append({"timestamp": int(row["timestamp"]), "value": int(row["value"])})
        except (KeyError, TypeError, ValueError):
            continue
    points.sort(key=lambda p: p["timestamp"])
    return points


def compute_breadth(listings: list) -> dict | None:
    """% of listed coins with percent_change_24h > 0."""
    vals = []
    for coin in listings or []:
        try:
            pct = coin["quote"]["USD"]["percent_change_24h"]
        except (KeyError, TypeError):
            pct = None
        if pct is not None:
            vals.append(pct)
    if not vals:
        return None
    up = sum(1 for v in vals if v > 0)
    return {
        "count": len(vals),
        "up": up,
        "down": len(vals) - up,
        "pct_up": round(100.0 * up / len(vals), 1),
        "source_endpoint": EP_LISTINGS,
    }


def top_movers(listings: list, n: int = 5, min_volume: float = MIN_MOVER_VOLUME_USD) -> dict:
    """Top gainers/losers by 24h % change, filtered to liquid coins only."""
    rows = []
    for coin in listings or []:
        try:
            q = coin["quote"]["USD"]
            pct, vol = q["percent_change_24h"], q["volume_24h"]
            price = q["price"]
        except (KeyError, TypeError):
            continue
        if pct is None or vol is None or vol < min_volume:
            continue
        rows.append({
            "symbol": coin.get("symbol", "?"),
            "name": coin.get("name", "?"),
            "pct_change_24h": round(float(pct), 2),
            "price_usd": float(price) if price is not None else None,
            "volume_24h_usd": float(vol),
            "source_endpoint": EP_LISTINGS,
        })
    gainers = sorted((r for r in rows if r["pct_change_24h"] > 0),
                     key=lambda r: r["pct_change_24h"], reverse=True)[:n]
    losers = sorted((r for r in rows if r["pct_change_24h"] < 0),
                    key=lambda r: r["pct_change_24h"])[:n]
    return {"gainers": gainers, "losers": losers,
            "min_volume_usd": min_volume, "considered": len(rows)}


def analyse(collected: dict) -> dict:
    """Run all analysis over collected data. Tolerates missing sections."""
    out: dict = {"statements": [], "anomalies": [], "missing": list(collected.get("_missing", []))}
    st = out["statements"]

    # --- Fear & Greed / regime -------------------------------------------
    fg = collected.get("fear_greed_latest")
    points = _fg_history_points(collected.get("fear_greed_historical"))
    out["fear_greed_history"] = points
    fg_now = fg_7d = fg_30d = None
    if points:
        fg_now = points[-1]["value"]
        if len(points) > 7:
            fg_7d = points[-8]["value"]
        if len(points) > 30:
            fg_30d = points[-31]["value"]
        elif points:
            fg_30d = points[0]["value"]
    if fg and fg.get("value") is not None:
        fg_now = int(fg["value"])
    if fg_now is not None:
        label, weather = classify_regime(fg_now)
        delta7 = (fg_now - fg_7d) if fg_7d is not None else None
        out["regime"] = {
            "fear_greed": fg_now,
            "label": fg.get("value_classification") if fg else label,
            "band_label": label,
            "weather": weather,
            "value_7d_ago": fg_7d,
            "delta_7d": delta7,
            "trend": trend_word(delta7),
            "value_30d_ago": fg_30d,
            "source_endpoint": EP_FG_LATEST,
        }
        st.append({
            "text": f"Market weather: {weather} — Fear & Greed is {fg_now} ({label}).",
            "figure": fg_now, "source_endpoint": EP_FG_LATEST,
        })
        if delta7 is not None:
            st.append({
                "text": f"Sentiment trend is {trend_word(delta7)}: {delta7:+d} points vs 7 days ago ({fg_7d}).",
                "figure": delta7, "source_endpoint": EP_FG_HIST,
            })
        if fg_7d is not None and abs(fg_now - fg_7d) >= 10:
            out["anomalies"].append({
                "text": f"Fear & Greed swung {fg_now - fg_7d:+d} points in 7 days ({fg_7d} -> {fg_now}).",
                "figure": fg_now - fg_7d, "source_endpoint": EP_FG_HIST,
            })
    else:
        out["regime"] = None
        if "fear_greed_latest" not in out["missing"]:
            out["missing"].append("fear_greed_latest")

    # --- Global metrics ----------------------------------------------------
    gm = collected.get("global_metrics")
    if gm:
        q = (gm.get("quote") or {}).get("USD") or {}
        total_mcap = q.get("total_market_cap")
        mcap_change = q.get("total_market_cap_yesterday_percentage_change")
        btc_dom = gm.get("btc_dominance")
        out["global"] = {
            "total_market_cap_usd": total_mcap,
            "total_volume_24h_usd": q.get("total_volume_24h"),
            "mcap_change_24h_pct": mcap_change,
            "btc_dominance_pct": btc_dom,
            "eth_dominance_pct": gm.get("eth_dominance"),
            "source_endpoint": EP_GLOBAL,
        }
        if total_mcap is not None:
            st.append({
                "text": f"Total market cap is ${total_mcap:,.0f}.",
                "figure": total_mcap, "source_endpoint": EP_GLOBAL,
            })
        if mcap_change is not None and abs(mcap_change) >= 3:
            out["anomalies"].append({
                "text": f"Total market cap moved {mcap_change:+.2f}% in 24h.",
                "figure": mcap_change, "source_endpoint": EP_GLOBAL,
            })
        if btc_dom is not None and (btc_dom >= 60 or btc_dom <= 40):
            out["anomalies"].append({
                "text": f"BTC dominance is at an extreme: {btc_dom:.2f}%.",
                "figure": btc_dom, "source_endpoint": EP_GLOBAL,
            })
    else:
        out["global"] = None
        if "global_metrics" not in out["missing"]:
            out["missing"].append("global_metrics")

    # --- Listings: breadth + movers ---------------------------------------
    listings = collected.get("listings") or []
    out["breadth"] = compute_breadth(listings)
    if out["breadth"]:
        b = out["breadth"]
        st.append({
            "text": f"Breadth: {b['pct_up']}% of the top {b['count']} coins rose in 24h ({b['up']} up / {b['down']} down).",
            "figure": b["pct_up"], "source_endpoint": EP_LISTINGS,
        })
    else:
        if "listings" not in out["missing"]:
            out["missing"].append("listings")
    out["movers"] = top_movers(listings)

    # --- Altcoin season -----------------------------------------------------
    alt = collected.get("altcoin_season")
    if alt and alt.get("altcoin_index") is not None:
        idx = alt["altcoin_index"]
        season = "Altcoin season" if idx >= 75 else "Bitcoin season" if idx <= 25 else "Mixed season"
        out["altcoin_season"] = {
            "index": idx, "season": season,
            "yearly_high": alt.get("yearly_high"), "yearly_low": alt.get("yearly_low"),
            "source_endpoint": EP_ALTSEASON,
        }
        st.append({
            "text": f"Altcoin Season Index is {idx}/100 ({season}).",
            "figure": idx, "source_endpoint": EP_ALTSEASON,
        })
    else:
        out["altcoin_season"] = None
        if "altcoin_season" not in out["missing"]:
            out["missing"].append("altcoin_season")

    # --- CMC100 -------------------------------------------------------------
    c100 = collected.get("cmc100")
    if c100 and c100.get("value") is not None:
        out["cmc100"] = {
            "value": c100["value"],
            "change_24h_pct": c100.get("value_24h_percentage_change"),
            "source_endpoint": EP_CMC100,
        }
        st.append({
            "text": f"CMC100 index is {c100['value']} ({c100.get('value_24h_percentage_change'):+}% 24h).",
            "figure": c100["value"], "source_endpoint": EP_CMC100,
        })
    else:
        out["cmc100"] = None
        if "cmc100" not in out["missing"]:
            out["missing"].append("cmc100")

    out["trending_note"] = collected.get("_trending_note")
    return out
