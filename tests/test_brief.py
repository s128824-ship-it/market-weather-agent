import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent
import brief as brief_mod


class TestBriefRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data, records = agent.load_fixtures()
        import analysis
        cls.a = analysis.analyse(data)
        cls.meta = {"generated_at": datetime(2026, 11, 18, 1, 30, tzinfo=timezone.utc),
                    "endpoints": records, "mode": "demo-test"}

    def test_en_contains_figures_disclaimer_endpoints(self):
        md = brief_mod.render_markdown(self.a, self.meta)
        self.assertIn("13", md)                       # fear & greed figure
        self.assertIn(brief_mod.DISCLAIMER, md)
        self.assertIn("/v3/fear-and-greed/latest", md)
        self.assertIn("/v1/global-metrics/quotes/latest", md)
        self.assertIn("HTTP 200", md)
        self.assertIn("2026-11-18 01:30 UTC", md)
        self.assertIn("10:30 JST", md)

    def test_ja_contains_disclaimer_and_figures(self):
        md = brief_mod.render_markdown_ja(self.a, self.meta)
        self.assertIn(brief_mod.DISCLAIMER, md)
        self.assertIn("嵐", md)                        # Storm weather in JA
        self.assertIn("13", md)
        self.assertIn("/v3/index/cmc100-latest", md)

    def test_dashboard_self_contained(self):
        doc = brief_mod.render_dashboard(self.a, self.meta)
        self.assertIn(brief_mod.DISCLAIMER, doc)
        self.assertIn("Storm", doc)
        self.assertNotIn("http://", doc.replace("http://www.w3.org", ""))
        self.assertNotIn("<script src", doc)
        self.assertNotIn("<link", doc)
        self.assertIn("/v1/cryptocurrency/listings/latest", doc)


if __name__ == "__main__":
    unittest.main()
