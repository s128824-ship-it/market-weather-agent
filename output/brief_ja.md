# マーケット天気 — デイリーブリーフ

生成日時: 2026-11-24 09:03 UTC / 2026-11-24 18:03 JST  |  データモード: live keyless

## 今日の天気: 嵐（極度の恐怖）

恐怖・強欲指数は **9**（極度の恐怖）、7日推移は横ばい（7日前比: -4）。出典: `/v3/fear-and-greed/latest`

## 主要指標

- 時価総額合計: **$2.06T** （前日比 -1.70%） — `/v1/global-metrics/quotes/latest`
- BTCドミナンス: **58.50%** / ETH 9.99% — `/v1/global-metrics/quotes/latest`
- 24時間出来高合計: $100.5B — `/v1/global-metrics/quotes/latest`
- 地合い（騰落）: 上位100銘柄中 **43.0%** が24時間で上昇（43上昇 / 57下落） — `/v1/cryptocurrency/listings/latest`
- アルトコインシーズン指数: **59/100** — `/v1/altcoin-season-index/latest`
- CMC100: **117.46**（24h -1.85%） — `/v3/index/cmc100-latest`

## 値動き上位（24時間、出来高 $1M 以上のみ）

### 上昇
| コイン | 24h % | 価格 | 24h出来高 |
|---|---:|---:|---:|
| ATOM (Cosmos) | +9.44% | $1.30 | $42.6M |
| 币安人生 (币安人生) | +5.20% | $0.4713 | $3.4M |
| VET (VeChain) | +4.25% | $0.0049 | $13.0M |
| FF (Falcon Finance) | +3.52% | $0.1056 | $6.0M |
| STABLE (Stable) | +3.37% | $0.0232 | $7.2M |

### 下落
| コイン | 24h % | 価格 | 24h出来高 |
|---|---:|---:|---:|
| PIEVERSE (Pieverse) | -12.34% | $3.14 | $218.6M |
| ZRO (LayerZero) | -11.60% | $1.08 | $99.5M |
| ZEC (Zcash) | -5.44% | $751.04 | $1.0B |
| WLFI (World Liberty Financial) | -5.32% | $0.0409 | $63.3M |
| ETHFI (ether.fi) | -5.21% | $0.4778 | $30.6M |

## 異常検知

- ルールベースの異常は検知されませんでした。

## トレンドセクション

- Trending section unavailable: /v1/cryptocurrency/trending/latest requires the Startup plan or above (no CMC_API_KEY in this run). Fallback applied — brief generated without it. Detail: plan/key not authorised for this endpoint (HTTP 403, error 1005): An API Key is required for this call.

## 根拠 — 呼び出したエンドポイント

- `/v3/fear-and-greed/latest` [keyless] HTTP 200 OK
- `/v3/fear-and-greed/historical?limit=30` [keyless] HTTP 200 OK
- `/v1/global-metrics/quotes/latest?convert=USD` [keyless] HTTP 200 OK
- `/v1/cryptocurrency/listings/latest?start=1&limit=100&convert=USD` [keyless] HTTP 200 OK
- `/v1/altcoin-season-index/latest` [keyless] HTTP 200 OK
- `/v3/index/cmc100-latest` [keyless] HTTP 200 OK
- `/v1/cryptocurrency/trending/latest` [keyless] HTTP 403 FAILED — plan/key not authorised for this endpoint (HTTP 403, error 1005): An API Key is required for this call.

---
*Experimental hackathon project. Not financial advice. / 実験的なハッカソンプロジェクトです。投資助言ではありません。*
