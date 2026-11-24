"""Renderers: brief.md (EN), brief_ja.md (JA), dashboard.html.

Every output carries: generation timestamp (UTC + JST), the list of
endpoints actually called with HTTP status, the missing-sections list,
and the disclaimer.
"""
from __future__ import annotations

import html
from datetime import timezone, timedelta

DISCLAIMER = "Experimental hackathon project. Not financial advice."
DISCLAIMER_JA = "実験的なハッカソンプロジェクトです。投資助言ではありません。"
JST = timezone(timedelta(hours=9))

_WEATHER_JA = {"Storm": "嵐", "Rain": "雨", "Overcast": "曇り", "Sunny": "晴れ", "Heatwave": "猛暑"}
_LABEL_JA = {"Extreme fear": "極度の恐怖", "Fear": "恐怖", "Neutral": "中立",
             "Greed": "強欲", "Extreme greed": "極度の強欲"}
_TREND_JA = {"improving": "回復傾向", "deteriorating": "悪化傾向", "steady": "横ばい", "unknown": "不明"}


def _fmt_ts(meta) -> tuple[str, str]:
    dt = meta["generated_at"]
    return (dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            dt.astimezone(JST).strftime("%Y-%m-%d %H:%M JST"))


def _money(v) -> str:
    if v is None:
        return "n/a"
    if abs(v) >= 1e12:
        return f"${v/1e12:.2f}T"
    if abs(v) >= 1e9:
        return f"${v/1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.1f}M"
    return f"${v:,.2f}"


def _endpoint_lines(meta) -> list[str]:
    lines = []
    for r in meta.get("endpoints", []):
        status = r["http_status"] if r["http_status"] is not None else "—"
        ok = "OK" if r["ok"] else "FAILED"
        note = f" — {r['note']}" if r.get("note") else ""
        lines.append(f"- `{r['endpoint']}` [{r['mode']}] HTTP {status} {ok}{note}")
    return lines


def _price(v) -> str:
    if v is None:
        return "n/a"
    if v >= 1000:
        return f"${v:,.2f}"
    if v >= 1:
        return f"${v:.2f}"
    return f"${v:.4f}"


def _movers_table(movers, ja: bool = False) -> list[str]:
    head = "| Coin | 24h % | Price | Volume 24h |" if not ja else "| コイン | 24h % | 価格 | 24h出来高 |"
    lines = [head, "|---|---:|---:|---:|"]
    for row in movers:
        lines.append(
            f"| {row['symbol']} ({row['name']}) | {row['pct_change_24h']:+.2f}% | "
            f"{_price(row['price_usd'])} | {_money(row['volume_24h_usd'])} |"
        )
    return lines


def render_markdown(a: dict, meta: dict) -> str:
    utc, jst = _fmt_ts(meta)
    r, g = a.get("regime"), a.get("global")
    L = ["# Market Weather — Daily Brief", ""]
    L.append(f"Generated: {utc} / {jst}  |  Data mode: {meta.get('mode', 'live')}")
    L.append("")
    if r:
        L.append(f"## Today's weather: {r['weather']} ({r['label']})")
        L.append("")
        L.append(f"Fear & Greed is **{r['fear_greed']}** ({r['band_label']}), trend "
                 f"{r['trend']} (7d delta: {r['delta_7d'] if r['delta_7d'] is not None else 'n/a'}). "
                 f"Source: `{r['source_endpoint']}`.")
    else:
        L.append("## Today's weather: unavailable (Fear & Greed section missing)")
    L.append("")
    L.append("## Key figures")
    L.append("")
    if g:
        L.append(f"- Total market cap: **{_money(g['total_market_cap_usd'])}** "
                 f"({g['mcap_change_24h_pct']:+.2f}% vs yesterday) — `{g['source_endpoint']}`"
                 if g["mcap_change_24h_pct"] is not None else
                 f"- Total market cap: **{_money(g['total_market_cap_usd'])}** — `{g['source_endpoint']}`")
        L.append(f"- BTC dominance: **{g['btc_dominance_pct']:.2f}%** / ETH {g['eth_dominance_pct']:.2f}% — `{g['source_endpoint']}`")
        L.append(f"- Total volume 24h: {_money(g['total_volume_24h_usd'])} — `{g['source_endpoint']}`")
    if a.get("breadth"):
        b = a["breadth"]
        L.append(f"- Breadth: **{b['pct_up']}%** of top {b['count']} coins up in 24h ({b['up']} up / {b['down']} down) — `{b['source_endpoint']}`")
    if a.get("altcoin_season"):
        s = a["altcoin_season"]
        L.append(f"- Altcoin Season Index: **{s['index']}/100** ({s['season']}) — `{s['source_endpoint']}`")
    if a.get("cmc100"):
        c = a["cmc100"]
        L.append(f"- CMC100: **{c['value']}** ({c['change_24h_pct']:+}% 24h) — `{c['source_endpoint']}`")
    L.append("")
    L.append("## Top movers (24h, volume ≥ $1M only)")
    L.append("")
    L.append("### Gainers")
    L += _movers_table(a["movers"]["gainers"]) if a["movers"]["gainers"] else ["_None._"]
    L.append("")
    L.append("### Losers")
    L += _movers_table(a["movers"]["losers"]) if a["movers"]["losers"] else ["_None._"]
    L.append("")
    L.append("## Anomalies")
    L.append("")
    if a["anomalies"]:
        for an in a["anomalies"]:
            L.append(f"- ⚠️ {an['text']} (source: `{an['source_endpoint']}`)")
    else:
        L.append("- None detected by the deterministic rules.")
    L.append("")
    if a.get("trending_note"):
        L.append("## Trending section")
        L.append("")
        L.append(f"- {a['trending_note']}")
        L.append("")
    if a["missing"]:
        L.append("## Missing sections")
        L.append("")
        for m in a["missing"]:
            L.append(f"- {m} (data unavailable this run; brief generated without it)")
        L.append("")
    L.append("## Evidence — endpoints called")
    L.append("")
    L += _endpoint_lines(meta)
    L.append("")
    L.append("---")
    L.append(f"*{DISCLAIMER}*")
    return "\n".join(L) + "\n"


def render_markdown_ja(a: dict, meta: dict) -> str:
    utc, jst = _fmt_ts(meta)
    r, g = a.get("regime"), a.get("global")
    L = ["# マーケット天気 — デイリーブリーフ", ""]
    L.append(f"生成日時: {utc} / {jst}  |  データモード: {meta.get('mode', 'live')}")
    L.append("")
    if r:
        L.append(f"## 今日の天気: {_WEATHER_JA.get(r['weather'], r['weather'])}（{_LABEL_JA.get(r['band_label'], r['band_label'])}）")
        L.append("")
        L.append(f"恐怖・強欲指数は **{r['fear_greed']}**（{_LABEL_JA.get(r['band_label'], '')}）、"
                 f"7日推移は{_TREND_JA.get(r['trend'], r['trend'])}（7日前比: {r['delta_7d'] if r['delta_7d'] is not None else '不明'}）。"
                 f"出典: `{r['source_endpoint']}`")
    else:
        L.append("## 今日の天気: 取得できませんでした（恐怖・強欲指数セクション欠落）")
    L.append("")
    L.append("## 主要指標")
    L.append("")
    if g:
        chg = f"（前日比 {g['mcap_change_24h_pct']:+.2f}%）" if g["mcap_change_24h_pct"] is not None else ""
        L.append(f"- 時価総額合計: **{_money(g['total_market_cap_usd'])}** {chg} — `{g['source_endpoint']}`")
        L.append(f"- BTCドミナンス: **{g['btc_dominance_pct']:.2f}%** / ETH {g['eth_dominance_pct']:.2f}% — `{g['source_endpoint']}`")
        L.append(f"- 24時間出来高合計: {_money(g['total_volume_24h_usd'])} — `{g['source_endpoint']}`")
    if a.get("breadth"):
        b = a["breadth"]
        L.append(f"- 地合い（騰落）: 上位{b['count']}銘柄中 **{b['pct_up']}%** が24時間で上昇（{b['up']}上昇 / {b['down']}下落） — `{b['source_endpoint']}`")
    if a.get("altcoin_season"):
        s = a["altcoin_season"]
        L.append(f"- アルトコインシーズン指数: **{s['index']}/100** — `{s['source_endpoint']}`")
    if a.get("cmc100"):
        c = a["cmc100"]
        L.append(f"- CMC100: **{c['value']}**（24h {c['change_24h_pct']:+}%） — `{c['source_endpoint']}`")
    L.append("")
    L.append("## 値動き上位（24時間、出来高 $1M 以上のみ）")
    L.append("")
    L.append("### 上昇")
    L += _movers_table(a["movers"]["gainers"], ja=True) if a["movers"]["gainers"] else ["_なし_"]
    L.append("")
    L.append("### 下落")
    L += _movers_table(a["movers"]["losers"], ja=True) if a["movers"]["losers"] else ["_なし_"]
    L.append("")
    L.append("## 異常検知")
    L.append("")
    if a["anomalies"]:
        for an in a["anomalies"]:
            L.append(f"- ⚠️ {an['text']}（出典: `{an['source_endpoint']}`）")
    else:
        L.append("- ルールベースの異常は検知されませんでした。")
    L.append("")
    if a.get("trending_note"):
        L.append("## トレンドセクション")
        L.append("")
        L.append(f"- {a['trending_note']}")
        L.append("")
    if a["missing"]:
        L.append("## 欠落セクション")
        L.append("")
        for m in a["missing"]:
            L.append(f"- {m}（今回は取得できず、このセクションなしで生成）")
        L.append("")
    L.append("## 根拠 — 呼び出したエンドポイント")
    L.append("")
    L += _endpoint_lines(meta)
    L.append("")
    L.append("---")
    L.append(f"*{DISCLAIMER} / {DISCLAIMER_JA}*")
    return "\n".join(L) + "\n"


def render_dashboard(a: dict, meta: dict) -> str:
    utc, jst = _fmt_ts(meta)
    r, g = a.get("regime"), a.get("global")
    fg = r["fear_greed"] if r else 0
    weather = r["weather"] if r else "Unavailable"
    label = r["label"] if r else "n/a"

    def mover_rows(rows):
        out = []
        for m in rows:
            cls = "pos" if m["pct_change_24h"] >= 0 else "neg"
            price = f"${m['price_usd']:,.2f}" if m["price_usd"] is not None else "n/a"
            out.append(f"<tr><td>{html.escape(m['symbol'])}</td>"
                       f"<td class='{cls}'>{m['pct_change_24h']:+.2f}%</td>"
                       f"<td>{price}</td><td>{_money(m['volume_24h_usd'])}</td></tr>")
        return "\n".join(out) or "<tr><td colspan='4'>None</td></tr>"

    anomalies = "\n".join(
        f"<li>⚠️ {html.escape(an['text'])} <code>{html.escape(an['source_endpoint'])}</code></li>"
        for an in a["anomalies"]) or "<li>None detected.</li>"
    endpoints = "\n".join(f"<li><code>{html.escape(line[2:])}</code></li>"
                          for line in _endpoint_lines(meta))
    missing = ", ".join(a["missing"]) if a["missing"] else "none"
    b = a.get("breadth")
    breadth_txt = f"{b['pct_up']}% up ({b['up']}/{b['count']})" if b else "n/a"
    alt = a.get("altcoin_season")
    alt_txt = f"{alt['index']}/100 ({alt['season']})" if alt else "n/a"
    c100 = a.get("cmc100")
    c100_txt = f"{c100['value']} ({c100['change_24h_pct']:+}% 24h)" if c100 else "n/a"
    mcap_txt = _money(g["total_market_cap_usd"]) if g else "n/a"
    dom_txt = f"{g['btc_dominance_pct']:.2f}%" if g else "n/a"
    trending = f"<p>{html.escape(a['trending_note'])}</p>" if a.get("trending_note") else ""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Market Weather — {html.escape(weather)}</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem auto;max-width:860px;padding:0 1rem;background:#0f1420;color:#e8ecf4}}
.card{{background:#1a2133;border-radius:12px;padding:1.2rem;margin:1rem 0}}
.gauge{{background:linear-gradient(90deg,#b03a2e,#e67e22,#f1c40f,#82e0aa,#27ae60);height:22px;border-radius:11px;position:relative}}
.marker{{position:absolute;top:-4px;width:6px;height:30px;background:#fff;border-radius:3px;left:calc({fg}% - 3px)}}
.big{{font-size:2.4rem;font-weight:700}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:.35rem .5rem;border-bottom:1px solid #2c3852;text-align:left}}
.pos{{color:#7dffa8}}.neg{{color:#ff8a8a}}code{{color:#9fc1ff}}footer{{color:#8b96ad;font-size:.85rem}}
</style></head><body>
<h1>🌦️ Market Weather</h1>
<p>Generated: {utc} / {jst} · Mode: {html.escape(str(meta.get('mode','live')))}</p>
<div class="card"><div class="big">{html.escape(weather)} — {html.escape(label)}</div>
<p>Fear &amp; Greed gauge (0 = Extreme fear, 100 = Extreme greed): <b>{fg}</b></p>
<div class="gauge"><div class="marker"></div></div></div>
<div class="card"><h2>Key figures</h2>
<p>Total market cap: <b>{mcap_txt}</b> · BTC dominance: <b>{dom_txt}</b><br>
Breadth (top 100, 24h): <b>{breadth_txt}</b> · Altcoin Season: <b>{html.escape(alt_txt)}</b> · CMC100: <b>{html.escape(c100_txt)}</b></p></div>
<div class="card"><h2>Top gainers (24h, vol ≥ $1M)</h2>
<table><tr><th>Coin</th><th>24h %</th><th>Price</th><th>Volume</th></tr>
{mover_rows(a['movers']['gainers'])}</table></div>
<div class="card"><h2>Top losers (24h, vol ≥ $1M)</h2>
<table><tr><th>Coin</th><th>24h %</th><th>Price</th><th>Volume</th></tr>
{mover_rows(a['movers']['losers'])}</table></div>
<div class="card"><h2>Anomalies</h2><ul>{anomalies}</ul>{trending}
<p>Missing sections: {html.escape(missing)}</p></div>
<div class="card"><h2>Evidence — endpoints called</h2><ul>{endpoints}</ul></div>
<footer>{DISCLAIMER}</footer>
</body></html>
"""
