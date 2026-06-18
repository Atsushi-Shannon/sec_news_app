from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMETER_PREFIXES = ("utm_",)
TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "dclid",
    "gbraid",
    "wbraid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "mkt_tok",
    "spm",
    "vero_id",
}


def is_safe_http_url(url: str) -> bool:
    try:
        parsed = urlsplit(url.strip())
    except ValueError:
        return False
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def normalize_url(url: str) -> str:
    text = url.strip()
    if not text:
        return ""

    parsed = urlsplit(text)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    if scheme not in {"http", "https"} or not netloc:
        return text

    params = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lower_key = key.lower()
        if lower_key in TRACKING_PARAMETERS:
            continue
        if any(lower_key.startswith(prefix) for prefix in TRACKING_PARAMETER_PREFIXES):
            continue
        params.append((key, value))

    query = urlencode(sorted(params), doseq=True)
    path = parsed.path or ""
    path = path.rstrip("/") if path != "/" else ""

    return urlunsplit((scheme, netloc, path, query, ""))
