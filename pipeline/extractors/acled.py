"""ACLED API extractor using OAuth token auth."""

import json
import logging
from datetime import date

import requests

from pipeline.config import (
    ACLED_BASE_URL, ACLED_CLIENT_ID, ACLED_OAUTH_URL, ACLED_PAGE_SIZE,
    ACLED_PASSWORD, ACLED_USERNAME, ACLED_RAW_DIR, DASHBOARD_START_DATE,
)
from pipeline.extractors.base import BaseExtractor
from pipeline.utils.retry import retry

logger = logging.getLogger(__name__)

ACLED_FIELDS = "|".join([
    "event_id_cnty", "event_date", "event_type", "sub_event_type",
    "disorder_type", "actor1", "actor2", "interaction", "country",
    "iso3", "admin1", "admin2", "location", "latitude", "longitude",
    "geo_precision", "civilian_targeting", "fatalities", "notes",
    "source", "source_scale",
])


class ACLEDExtractor(BaseExtractor):
    SOURCE_NAME = "ACLED"

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    def is_available(self) -> bool:
        if ACLED_USERNAME and ACLED_PASSWORD:
            return True
        logger.warning(
            "ACLED credentials not set. Provide ACLED_USERNAME + ACLED_PASSWORD "
            "for OAuth token auth."
        )
        return False

    def extract(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        **kwargs,
    ) -> None:
        ACLED_RAW_DIR.mkdir(parents=True, exist_ok=True)
        start = start_date or DASHBOARD_START_DATE
        end = end_date or date.today()
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        logger.info("ACLED auth mode: OAuth token")
        self._login_with_password()

        logger.info("ACLED extraction: %s → %s", start_str, end_str)
        page = 1
        total_saved = 0

        while True:
            params = {
                "event_date": f"{start_str}|{end_str}",
                "event_date_where": "BETWEEN",
                "limit": ACLED_PAGE_SIZE,
                "page": page,
                "fields": ACLED_FIELDS,
                "_format": "json",
            }
            headers = {"Authorization": f"Bearer {self._access_token}"}

            data = self._get_json(
                params=params,
                headers=headers,
                use_token_auth=True,
            )
            records = data.get("data", [])
            if not records:
                break

            out_file = ACLED_RAW_DIR / f"{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}_page{page:04d}.json"
            with open(out_file, "w") as fh:
                json.dump(records, fh)

            total_saved += len(records)
            logger.info("ACLED page %d: %d records (total %d)", page, len(records), total_saved)

            if len(records) < ACLED_PAGE_SIZE:
                break
            page += 1

        logger.info("ACLED extraction complete: %d records", total_saved)

    @retry(max_attempts=4, backoff_base=3.0, exceptions=(requests.RequestException,))
    def _request_token(self, payload: dict[str, str]) -> dict:
        resp = requests.post(ACLED_OAUTH_URL, data=payload, timeout=60)
        resp.raise_for_status()
        token_data = resp.json()
        if not isinstance(token_data, dict):
            raise RuntimeError("ACLED token response JSON is not an object")
        return token_data

    def _login_with_password(self) -> None:
        token_data = self._request_token(
            {
                "username": ACLED_USERNAME or "",
                "password": ACLED_PASSWORD or "",
                "grant_type": "password",
                "client_id": ACLED_CLIENT_ID,
            }
        )
        self._set_tokens(token_data)

    def _refresh_access_token(self) -> bool:
        if not self._refresh_token:
            return False
        try:
            token_data = self._request_token(
                {
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                    "client_id": ACLED_CLIENT_ID,
                }
            )
        except requests.RequestException:
            return False
        self._set_tokens(token_data)
        return bool(self._access_token)

    def _set_tokens(self, token_data: dict) -> None:
        self._access_token = token_data.get("access_token")
        self._refresh_token = token_data.get("refresh_token", self._refresh_token)
        if not self._access_token:
            raise RuntimeError("ACLED token response missing access_token")

    @retry(max_attempts=4, backoff_base=3.0, exceptions=(requests.RequestException,))
    def _get_json(
        self,
        params: dict,
        headers: dict[str, str] | None = None,
        use_token_auth: bool = False,
    ) -> dict:
        resp = requests.get(ACLED_BASE_URL, params=params, headers=headers, timeout=60)
        if use_token_auth and resp.status_code == 401:
            logger.info("ACLED token unauthorized/expired; attempting refresh")
            if not self._refresh_access_token():
                logger.info("ACLED refresh failed; requesting new access token")
                self._login_with_password()
            refreshed_headers = dict(headers or {})
            refreshed_headers["Authorization"] = f"Bearer {self._access_token}"
            resp = requests.get(ACLED_BASE_URL, params=params, headers=refreshed_headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError("ACLED response JSON is not an object")
        return data
