import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analysis


def _listing(symbol, pct, vol, price=100.0):
    return {"symbol": symbol, "name": symbol + "Coin",
            "quote": {"USD": {"percent_change_24h": pct, "volume_24h": vol, "price": price}}}


class TestRegime(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(analysis.classify_regime(0), ("Extreme fear", "Storm"))
        self.assertEqual(analysis.classify_regime(13), ("Extreme fear", "Storm"))
        self.assertEqual(analysis.classify_regime(24), ("Extreme fear", "Storm"))
        self.assertEqual(analysis.classify_regime(25), ("Fear", "Rain"))
        self.assertEqual(analysis.classify_regime(50), ("Neutral", "Overcast"))
        self.assertEqual(analysis.classify_regime(60), ("Greed", "Sunny"))
        self.assertEqual(analysis.classify_regime(90), ("Extreme greed", "Heatwave"))
        self.assertEqual(analysis.classify_regime(100), ("Extreme greed", "Heatwave"))

    def test_trend_word(self):
        self.assertEqual(analysis.trend_word(9), "improving")
        self.assertEqual(analysis.trend_word(-13), "deteriorating")
        self.assertEqual(analysis.trend_word(2), "steady")
        self.assertEqual(analysis.trend_word(None), "unknown")


class TestBreadth(unittest.TestCase):
    def test_breadth(self):
        listings = [_listing("A", 1.0, 2e6), _listing("B", -1.0, 2e6),
                    _listing("C", 3.0, 2e6), _listing("D", -2.0, 2e6)]
        b = analysis.compute_breadth(listings)
        self.assertEqual(b["count"], 4)
        self.assertEqual(b["up"], 2)
        self.assertEqual(b["pct_up"], 50.0)

    def test_breadth_empty(self):
        self.assertIsNone(analysis.compute_breadth([]))


class TestMoversFilter(unittest.TestCase):
    def test_illiquid_excluded(self):
        listings = [
            _listing("PUMP", 500.0, 500_000),     # huge % but volume < $1M -> excluded
            _listing("REAL", 10.0, 5_000_000),    # included
            _listing("DUMP", -40.0, 900_000),     # excluded
            _listing("DOWN", -8.0, 3_000_000),    # included
        ]
        m = analysis.top_movers(listings)
        self.assertEqual([r["symbol"] for r in m["gainers"]], ["REAL"])
        self.assertEqual([r["symbol"] for r in m["losers"]], ["DOWN"])
        self.assertEqual(m["considered"], 2)

    def test_ordering(self):
        listings = [_listing("A", 5.0, 2e6), _listing("B", 20.0, 2e6), _listing("C", -20.0, 2e6)]
        m = analysis.top_movers(listings, n=2)
        self.assertEqual(m["gainers"][0]["symbol"], "B")
        self.assertEqual(m["losers"][0]["symbol"], "C")


class TestAnalyseWithFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parent.parent
        fx = root / "fixtures"
        cls.collected = {"_missing": []}
        mapping = {
            "fear_greed_latest": "fear-greed-latest.json",
            "fear_greed_historical": "fear-greed-historical.json",
            "global_metrics": "global-metrics.json",
            "listings": "listings-top100.json",
            "altcoin_season": "altcoin-season-latest.json",
            "cmc100": "cmc100-latest.json",
        }
        for key, fname in mapping.items():
            cls.collected[key] = json.loads((fx / fname).read_text())["data"]
        cls.result = analysis.analyse(cls.collected)

    def test_regime_from_fixture(self):
        r = self.result["regime"]
        self.assertIsNotNone(r)
        self.assertEqual(r["fear_greed"], 13)
        self.assertEqual(r["band_label"], "Extreme fear")
        self.assertEqual(r["weather"], "Storm")

    def test_breadth_from_fixture(self):
        b = self.result["breadth"]
        self.assertEqual(b["count"], 100)
        self.assertTrue(0 <= b["pct_up"] <= 100)

    def test_global_from_fixture(self):
        g = self.result["global"]
        self.assertGreater(g["total_market_cap_usd"], 1e12)
        self.assertTrue(0 < g["btc_dominance_pct"] < 100)

    def test_statements_carry_sources(self):
        for s in self.result["statements"]:
            self.assertIn("source_endpoint", s)
            self.assertIn("figure", s)
            self.assertTrue(s["source_endpoint"].startswith("/v"))

    def test_missing_tolerated(self):
        res = analysis.analyse({"_missing": [], "fear_greed_latest": None,
                                "fear_greed_historical": None, "global_metrics": None,
                                "listings": None, "altcoin_season": None, "cmc100": None})
        self.assertIsNone(res["regime"])
        self.assertIn("fear_greed_latest", res["missing"])


if __name__ == "__main__":
    unittest.main()
