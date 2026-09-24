"""One audited HTTPS-only opener for every factory surface.

The estate Python standard (crew#620) flags S310 on bare ``urllib.request`` because it
allows ``file://`` and custom schemes. Every factory surface talks to a real HTTPS API,
so the honest fix is a single opener that *refuses* any non-https URL before the request
is sent. Call sites use ``https_request`` + ``open_https`` instead of ``urllib.request``.
"""

from __future__ import annotations

import urllib.request
import urllib.parse
from typing import Any, Optional


class UnsupportedScheme(ValueError):
    pass


def assert_https(url: str) -> str:
    """Return ``url`` unchanged when it is https, refuse anything else."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise UnsupportedScheme(
            f"factory refuses non-https URLs (got scheme {parsed.scheme!r} for {url!r})"
        )
    return url


def https_request(
    url: str,
    *,
    method: Optional[str] = None,
    data: Optional[bytes] = None,
    headers: Optional[dict[str, str]] = None,
) -> urllib.request.Request:
    """Build a Request, but only after the target is proven https."""
    assert_https(url)
    # S310 is the whole reason this module exists: the scheme audit above is the guard,
    # and this is the single place in the repo where a raw Request is constructed.
    return urllib.request.Request(  # noqa: S310
        url, method=method, data=data, headers=headers or {}
    )


def open_https(req: Any, timeout: float) -> Any:
    """urlopen, but only after the request target is proven https."""
    if isinstance(req, urllib.request.Request):
        assert_https(req.full_url)
    else:
        assert_https(str(req))
    # S310 is the whole reason this module exists: the scheme audit above is the guard,
    # and this is the single place in the repo where a raw urlopen is permitted.
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310
