"""Minimal MCP server over stdio (JSON-RPC 2.0), standard library only.

Implements: initialize, notifications/initialized, ping, tools/list, tools/call.
Tools:
  - get_market_weather   : full regime summary (live, fixtures fallback)
  - get_fear_greed_trend : current F&G + 7d/30d comparison
  - get_top_movers       : top gainers/losers (24h, volume >= $1M)
  - get_coin_snapshot    : price snapshot by symbol — keyless simple-price
                           route first, keyed quotes/latest if a key is set.

Run:  python3 mcp_server.py        (speaks JSON-RPC on stdin/stdout, one
                                    JSON object per line)
"""
from __future__ import annotations

import json
import sys

import agent as agent_mod
import analysis
from cmc_client import CMCClient, CMCError

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "market-weather-agent", "version": "0.1.0"}

TOOLS = [
    {
        "name": "get_market_weather",
        "description": "Current crypto market 'weather': regime from Fear & Greed, "
                       "total market cap, BTC dominance, breadth, anomalies. "
                       "Every figure is sourced from a named CoinMarketCap endpoint.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_fear_greed_trend",
        "description": "Fear & Greed index now vs 7 and 30 days ago, with trend direction.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_top_movers",
        "description": "Top gainers and losers in the top 100 by 24h % change, "
                       "filtered to 24h volume >= $1M.",
        "inputSchema": {"type": "object", "properties": {
            "n": {"type": "integer", "description": "How many per side (default 5)"}}},
    },
    {
        "name": "get_coin_snapshot",
        "description": "Latest USD price snapshot for one coin symbol (e.g. BTC).",
        "inputSchema": {"type": "object", "properties": {
            "symbol": {"type": "string", "description": "Coin symbol, e.g. BTC"}},
            "required": ["symbol"]},
    },
]


def _load_analysis() -> dict:
    """Live analysis; on any collection failure, fall back to fixtures."""
    try:
        client = CMCClient()
        data = agent_mod.collect_all(client)
        if data.get("fear_greed_latest") is None and data.get("listings") is None:
            raise CMCError("live collection returned no core sections")
        return analysis.analyse(data)
    except Exception:
        data, _records = agent_mod.load_fixtures()
        return analysis.analyse(data)


def _tool_result(payload) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]}


def call_tool(name: str, arguments: dict) -> dict:
    if name == "get_coin_snapshot":
        symbol = str(arguments.get("symbol", "")).upper().strip()
        if not symbol:
            return _tool_result({"error": "symbol is required"})
        client = CMCClient()
        # Keyless route first: /v2/simple/price (verified keyless).
        try:
            data = client.get_keyless("/v2/simple/price", {"symbol": symbol, "convert": "USD"})
            for row in data or []:
                if row.get("symbol") == symbol:
                    quotes = row.get("quotes") or [{}]
                    return _tool_result({
                        "symbol": symbol, "name": row.get("name"),
                        "price_usd": quotes[0].get("price"),
                        "source_endpoint": "/v2/simple/price (keyless)",
                        "disclaimer": "Experimental hackathon project. Not financial advice.",
                    })
            return _tool_result({"error": f"symbol {symbol} not found via keyless route"})
        except CMCError as keyless_err:
            # Keyed fallback: quotes/latest (needs an API key).
            if client.has_key:
                try:
                    data = client.get_keyed("/v2/cryptocurrency/quotes/latest",
                                            {"symbol": symbol, "convert": "USD"})
                    row = (data or {}).get(symbol) or {}
                    q = ((row.get("quote") or {}).get("USD") or {})
                    return _tool_result({
                        "symbol": symbol, "name": row.get("name"),
                        "price_usd": q.get("price"),
                        "pct_change_24h": q.get("percent_change_24h"),
                        "source_endpoint": "/v2/cryptocurrency/quotes/latest (keyed)",
                        "disclaimer": "Experimental hackathon project. Not financial advice.",
                    })
                except CMCError as keyed_err:
                    return _tool_result({"error": f"keyless: {keyless_err}; keyed: {keyed_err}"})
            return _tool_result({"error": f"keyless route failed and no CMC_API_KEY set: {keyless_err}"})

    a = _load_analysis()
    if name == "get_market_weather":
        return _tool_result({
            "regime": a.get("regime"), "global": a.get("global"),
            "breadth": a.get("breadth"), "altcoin_season": a.get("altcoin_season"),
            "cmc100": a.get("cmc100"), "anomalies": a["anomalies"],
            "missing": a["missing"],
            "disclaimer": "Experimental hackathon project. Not financial advice.",
        })
    if name == "get_fear_greed_trend":
        r = a.get("regime") or {}
        return _tool_result({
            "fear_greed_now": r.get("fear_greed"),
            "value_7d_ago": r.get("value_7d_ago"),
            "delta_7d": r.get("delta_7d"),
            "value_30d_ago": r.get("value_30d_ago"),
            "trend": r.get("trend"),
            "history_points": len(a.get("fear_greed_history", [])),
            "source_endpoint": "/v3/fear-and-greed/latest + /v3/fear-and-greed/historical",
            "disclaimer": "Experimental hackathon project. Not financial advice.",
        })
    if name == "get_top_movers":
        n = int(arguments.get("n", 5))
        movers = analysis.top_movers(
            # recompute with requested n from the same listings used above
            _last_listings(a), n=n)
        return _tool_result({**movers,
                             "disclaimer": "Experimental hackathon project. Not financial advice."})
    return _tool_result({"error": f"unknown tool: {name}"})


# cache listings from the most recent analysis load for get_top_movers(n)
_LISTINGS_CACHE: list = []


def _last_listings(_a) -> list:
    global _LISTINGS_CACHE
    if not _LISTINGS_CACHE:
        try:
            client = CMCClient()
            _LISTINGS_CACHE = client.get_keyless(
                "/v1/cryptocurrency/listings/latest",
                {"start": 1, "limit": 100, "convert": "USD"}) or []
        except Exception:
            data, _r = agent_mod.load_fixtures()
            _LISTINGS_CACHE = data.get("listings") or []
    return _LISTINGS_CACHE


def handle(msg: dict) -> dict | None:
    method = msg.get("method")
    mid = msg.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }}
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        try:
            result = call_tool(params.get("name", ""), params.get("arguments") or {})
        except Exception as e:  # never crash the server on a tool error
            result = _tool_result({"error": f"{e.__class__.__name__}: {e}"})
        return {"jsonrpc": "2.0", "id": mid, "result": result}
    if mid is not None:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"method not found: {method}"}}
    return None


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
