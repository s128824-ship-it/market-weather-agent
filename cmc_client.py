"""CoinMarketCap API client — Python standard library only.

Keyless mode (default): base https://pro-api.coinmarketcap.com/public-api
    No API key, no auth header. The X-CMC_PRO_API_KEY header is NEVER sent
    on keyless calls.
Keyed mode: base https://pro-api.coinmarketcap.com
    Header X-CMC_PRO_API_KEY taken from the CMC_API_KEY environment variable
    only. The key is never printed, logged, or included in any record.

Behaviour:
- timeout (default 15s)
- one retry with backoff on HTTP 429 / 5xx
- a response envelope with a non-zero status.error_code counts as failure
  even when HTTP is 200 (CMC does this for unknown paths / busy system)
- HTTP 403 or error_code 1005/1006 -> PlanNotAuthorizedError (clear message)
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

KEYLESS_BASE = "https://pro-api.coinmarketcap.com/public-api"
KEYED_BASE = "https://pro-api.coinmarketcap.com"

PLAN_ERROR_CODES = {1005, 1006, "1005", "1006"}


class CMCError(Exception):
    """Any CMC call failure."""


class PlanNotAuthorizedError(CMCError):
    """403 / plan-gated endpoint (e.g. trending needs Startup or above)."""


@dataclass
class CallRecord:
    endpoint: str          # path + query, no host, no key
    mode: str              # "keyless" | "keyed" | "fixture"
    http_status: int | None
    ok: bool
    error_code: str | None = None
    note: str = ""

    def as_dict(self):
        return {
            "endpoint": self.endpoint,
            "mode": self.mode,
            "http_status": self.http_status,
            "ok": self.ok,
            "error_code": self.error_code,
            "note": self.note,
        }


@dataclass
class CMCClient:
    api_key: str | None = field(default=None)
    timeout: float = 15.0
    retry_delay: float = 1.0
    records: list = field(default_factory=list)

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.environ.get("CMC_API_KEY") or None

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)

    # -- low level ---------------------------------------------------------
    def _raw_get(self, url: str, headers: dict):
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return resp.status, body
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            return e.code, body
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise CMCError(f"network error: {e.__class__.__name__}: {e}") from e

    def _get(self, base: str, mode: str, path: str, params: dict | None):
        params = params or {}
        query = urllib.parse.urlencode(params)
        endpoint = path + (f"?{query}" if query else "")
        url = base + endpoint
        headers = {"Accept": "application/json", "User-Agent": "market-weather-agent/0.1"}
        if mode == "keyed":
            if not self.api_key:
                raise PlanNotAuthorizedError(
                    f"{path}: keyed call requested but CMC_API_KEY is not set"
                )
            headers["X-CMC_PRO_API_KEY"] = self.api_key

        last_exc: Exception | None = None
        for attempt in (0, 1):  # one retry
            try:
                status, body = self._raw_get(url, headers)
            except CMCError as e:
                last_exc = e
                if attempt == 0:
                    time.sleep(self.retry_delay)
                    continue
                self.records.append(CallRecord(endpoint, mode, None, False, None, str(e)))
                raise
            if status in (429,) or status >= 500:
                if attempt == 0:
                    time.sleep(self.retry_delay)
                    continue
            break

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {}
        status_block = payload.get("status") or {}
        error_code = status_block.get("error_code")
        error_msg = status_block.get("error_message") or ""

        if status == 403 or error_code in PLAN_ERROR_CODES:
            note = (
                f"plan/key not authorised for this endpoint "
                f"(HTTP {status}, error {error_code}): {error_msg}"
            )
            self.records.append(CallRecord(endpoint, mode, status, False, str(error_code), note))
            raise PlanNotAuthorizedError(note)
        if status != 200 or error_code not in (0, "0", None):
            note = f"HTTP {status}, error {error_code}: {error_msg}".strip()
            self.records.append(CallRecord(endpoint, mode, status, False,
                                           None if error_code is None else str(error_code), note))
            raise CMCError(note)
        self.records.append(CallRecord(endpoint, mode, status, True, "0", ""))
        return payload.get("data")

    # -- public API --------------------------------------------------------
    def get_keyless(self, path: str, params: dict | None = None):
        return self._get(KEYLESS_BASE, "keyless", path, params)

    def get_keyed(self, path: str, params: dict | None = None):
        return self._get(KEYED_BASE, "keyed", path, params)

    def get_auto(self, path: str, params: dict | None = None):
        """Keyless first; if plan/key-gated and a key exists, try keyed."""
        try:
            return self.get_keyless(path, params)
        except PlanNotAuthorizedError:
            if self.has_key:
                return self.get_keyed(path, params)
            raise
