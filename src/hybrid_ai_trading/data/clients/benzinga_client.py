from __future__ import annotations

import datetime as _dt
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, List, Optional, Union

import requests


class BenzingaAPIError(RuntimeError):
    """Unified wrapper error for Benzinga client failures."""


def mask_key(key: Optional[str]) -> str:
    """
    Mask an API key for safe logging.

    Rules:
    - None or empty -> "None"
    - Short (<8) -> returned unchanged
    - ==8 -> show first 4 + '****' + last 4
    - >8 -> show first 4 + stars (len-8) + last 4
    """
    if not key:
        return "None"
    n = len(key)
    if n < 8:
        return key
    if n == 8:
        return f"{key[:4]}****{key[-4:]}"
    return f"{key[:4]}{'*' * (n - 8)}{key[-4:]}"


def _coerce_date_str(d: Optional[Union[str, _dt.date, _dt.datetime, int, float]]) -> Optional[str]:
    """
    Permissive coercion for query params:
    - None -> None
    - datetime/date -> YYYY-MM-DD
    - str/int/float/other -> stringified
    """
    if d is None:
        return None
    if isinstance(d, _dt.datetime):
        return d.date().isoformat()
    if isinstance(d, _dt.date):
        return d.isoformat()
    return str(d)


def _parse_xml_minimal(xml_text: str) -> List[Dict[str, Any]]:
    """
    Minimal XML -> list[dict] for tests:
    Returns [ {tag: text, ...}, ... ] from <result><item>...</item></result>
    """
    try:
        root = ET.fromstring(xml_text)
    except Exception as e:
        raise BenzingaAPIError(f"Invalid XML in response: {e}") from e

    items: List[Dict[str, Any]] = []
    for item in root.findall(".//item"):
        row: Dict[str, Any] = {}
        for child in list(item):
            row[child.tag] = child.text or ""
        items.append(row)
    return items


def _resolve_api_key(explicit: Optional[str]) -> str:
    """
    Resolve API key with strict precedence:
    1) explicit arg
    2) BENZINGA_KEY
    3) BENZINGA_API_KEY
    """
    if explicit:
        return explicit
    env1 = os.environ.get("BENZINGA_KEY")
    if env1:
        return env1
    env2 = os.environ.get("BENZINGA_API_KEY")
    if env2:
        return env2
    raise BenzingaAPIError(
        "Missing Benzinga API key: pass 'api_key' or set BENZINGA_KEY/BENZINGA_API_KEY."
    )


class BenzingaClient:
    """
    Minimal Benzinga News client.

    Notes:
    - API key resolution precedence: api_key arg > BENZINGA_KEY > BENZINGA_API_KEY.
    - Keeps exact param names date_from/date_to.
    - Uses requests.get (not a Session) so tests can monkeypatch requests.get.
    - JSON:
        * list -> returns the list as-is
        * dict with 'data' -> returns list in 'data' (or wraps dict to [dict])
        * dict (single item) -> wraps to [dict]
    - XML: supported when content-type says xml, returns a list of items.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.benzinga.com/api/v2/news",
        timeout_sec: int = 15,
        session: Optional[requests.Session] = None,  # kept for BC; not used
    ) -> None:
        key = _resolve_api_key(api_key)
        self.api_key = key
        self.base_url = base_url
        self.timeout_sec = timeout_sec
        self._session = session  # not used; kept for BC

    def __repr__(self) -> str:
        return (
            f"BenzingaClient(api_key={mask_key(self.api_key)!r}, "
            f"base_url={self.base_url!r}, timeout_sec={self.timeout_sec})"
        )

    @staticmethod
    def _mask_key_local(key: Optional[str]) -> str:
        """Used by tests to cover masking branches."""
        return mask_key(key)

    def get_news(
        self,
        symbols: Optional[Union[str, Iterable[str]]] = None,
        date_from: Optional[Union[str, _dt.date, _dt.datetime, int, float]] = None,
        date_to: Optional[Union[str, _dt.date, _dt.datetime, int, float]] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        **extra_params: Any,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"apikey": self.api_key}

        df = _coerce_date_str(date_from)
        dt = _coerce_date_str(date_to)
        if df:
            params["date_from"] = df
        if dt:
            params["date_to"] = dt

        if symbols is not None:
            params["symbols"] = (
                symbols if isinstance(symbols, str) else ",".join(s for s in symbols)
            )

        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        for k, v in (extra_params or {}).items():
            if k not in params:
                params[k] = v

        try:
            # honor tests' monkeypatch of requests.get
            resp = requests.get(self.base_url, params=params, timeout=self.timeout_sec)

            ctype = (resp.headers.get("content-type") or "").lower()
            # XML path (return list of items)
            if "xml" in ctype or (resp.text or "").lstrip().startswith("<"):
                return _parse_xml_minimal(resp.text)

            # Otherwise normal HTTP + JSON
            resp.raise_for_status()
            try:
                payload = resp.json()
            except Exception as e:
                raise BenzingaAPIError(f"Invalid JSON in response: {e}") from e

            if payload is None:
                raise BenzingaAPIError("Empty JSON payload")

            # Accept list or dict and normalize to list for dict
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict):
                if "data" in payload:
                    data = payload["data"]
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict):
                        return [data]
                    raise BenzingaAPIError(f"Unexpected 'data' type: {type(data).__name__}")
                # single-item dict -> wrap to list
                return [payload]

            raise BenzingaAPIError(
                f"Unexpected response payload type: {type(payload).__name__}; expected dict or list."
            )

        except requests.HTTPError as e:
            raise BenzingaAPIError(f"HTTP error from Benzinga: {e}") from e
        except requests.RequestException as e:
            raise BenzingaAPIError(f"Request to Benzinga failed: {e}") from e
        except BenzingaAPIError:
            raise
        except Exception as e:
            raise BenzingaAPIError(f"Unexpected Benzinga client error: {e}") from e
