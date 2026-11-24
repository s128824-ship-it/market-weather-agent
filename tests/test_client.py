import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cmc_client
from cmc_client import CMCClient, PlanNotAuthorizedError


def _payload(data, error_code=0):
    return json.dumps({"data": data, "status": {"error_code": error_code,
                                                "error_message": ""}})


class TestClient(unittest.TestCase):
    def test_keyless_sends_no_key_header(self):
        client = CMCClient(api_key="TESTKEY-should-not-be-sent-keyless")
        captured = {}

        def fake_raw(url, headers):
            captured.update(headers)
            return 200, _payload({"value": 13})

        with mock.patch.object(client, "_raw_get", side_effect=fake_raw):
            data = client.get_keyless("/v3/fear-and-greed/latest")
        self.assertEqual(data, {"value": 13})
        self.assertNotIn("X-CMC_PRO_API_KEY", captured)

    def test_keyed_sends_header_and_never_records_key(self):
        client = CMCClient(api_key="TESTKEY123")
        captured = {}

        def fake_raw(url, headers):
            captured.update(headers)
            return 200, _payload({"ok": True})

        with mock.patch.object(client, "_raw_get", side_effect=fake_raw):
            client.get_keyed("/v1/cryptocurrency/trending/latest")
        self.assertEqual(captured.get("X-CMC_PRO_API_KEY"), "TESTKEY123")
        for rec in client.records:
            self.assertNotIn("TESTKEY123", json.dumps(rec.as_dict()))

    def test_403_raises_plan_error(self):
        client = CMCClient(api_key=None)
        body = json.dumps({"status": {"error_code": 1006,
                                      "error_message": "plan not authorised"}})
        with mock.patch.object(client, "_raw_get", return_value=(403, body)):
            with self.assertRaises(PlanNotAuthorizedError):
                client.get_keyless("/v1/cryptocurrency/trending/latest")
        self.assertFalse(client.records[-1].ok)
        self.assertEqual(client.records[-1].http_status, 403)

    def test_envelope_error_on_http_200_is_failure(self):
        client = CMCClient()
        body = json.dumps({"status": {"error_code": "500",
                                      "error_message": "system busy"}})
        with mock.patch.object(client, "_raw_get", return_value=(200, body)):
            with self.assertRaises(cmc_client.CMCError):
                client.get_keyless("/v3/index/cmc100-latest")

    def test_retry_on_429(self):
        client = CMCClient(retry_delay=0)
        calls = {"n": 0}

        def flaky(url, headers):
            calls["n"] += 1
            if calls["n"] == 1:
                return 429, "{}"
            return 200, _payload({"value": 1})

        with mock.patch.object(client, "_raw_get", side_effect=flaky):
            data = client.get_keyless("/v3/fear-and-greed/latest")
        self.assertEqual(data, {"value": 1})
        self.assertEqual(calls["n"], 2)


if __name__ == "__main__":
    unittest.main()
