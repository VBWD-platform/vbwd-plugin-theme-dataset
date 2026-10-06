"""The public dataset API the fe-user plugin calls, always through core C2 (D3).

``categories`` / ``datasets`` / ``dataset`` → ``GET /api/v1/dataset/categories``,
``GET /api/v1/dataset``, ``GET /api/v1/dataset/<slug>`` (``datasetApi``);
``create_order`` → ``POST /api/v1/dataset/orders`` (the checkout source). The
caller's headers are forwarded; a non-2xx answer raises ``ThemeApiError``.
"""
from typing import Any, Mapping
from urllib.parse import quote

from plugins.theme.theme.theme_api import call_api
from plugins.theme.theme.theme_request import ThemeRequest

DATASET_API_PREFIX = "/api/v1/dataset"


class DatasetApi:
    """The dataset endpoints for one themed request."""

    def __init__(self, theme_request: ThemeRequest) -> None:
        self._theme_request = theme_request

    def categories(self) -> Any:
        return call_api(self._theme_request, "GET", f"{DATASET_API_PREFIX}/categories")

    def datasets(self, query: Mapping[str, Any]) -> Any:
        return call_api(
            self._theme_request, "GET", DATASET_API_PREFIX, query=dict(query)
        )

    def dataset(self, slug: str) -> Any:
        return call_api(
            self._theme_request, "GET", f"{DATASET_API_PREFIX}/{quote(slug, safe='')}"
        )

    def create_order(self, payload: Mapping[str, Any]) -> Any:
        return call_api(
            self._theme_request,
            "POST",
            f"{DATASET_API_PREFIX}/orders",
            json=dict(payload),
        )
