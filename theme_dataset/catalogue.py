"""The DatasetCatalogue + DatasetDetail CMS components — the S110 Data-store views.

``DatasetCatalogue.vue``: at ``/data-store`` the category index, at
``/data-store/<category_slug>`` that category's datasets (search + pager; the
list body is also the ``/_render/_fragment/dataset/list`` fragment).
``DatasetDetail.vue``: one dataset and its "Get Dataset" checkout target.

The list asks ``GET /api/v1/dataset`` with ``category=<slug>`` — the parameter
the public API reads. (The SPA store sends ``category_slug``, which the API
ignores, so the SPA lists every dataset under every category; the themed list
is the filtered one.)
"""
import re
from typing import Any, Callable, Dict, List, Mapping, Optional

from plugins.theme.theme.theme_api import ThemeApiError
from plugins.theme.theme.theme_request import ThemeRequest
from plugins.theme_cms.theme_cms.tags_custom_fields import tags_and_custom_fields

from .dataset_api import DatasetApi

NOT_FOUND_KEY = "dataset.notFound"
CATEGORY_PARAMETER = "category_slug"
QUERY_PARAMETER = "q"
PAGE_PARAMETER = "page"
FIRST_PAGE = 1
WORD_START = re.compile(r"\b\w")

ApiFactory = Callable[[ThemeRequest], Any]


def _page_number(raw_page: Any) -> int:
    try:
        return max(int(raw_page), FIRST_PAGE)
    except (TypeError, ValueError):
        return FIRST_PAGE


def category_label(slug: str, categories: List[Mapping[str, Any]]) -> str:
    """The category's label, else the slug title-cased (``open-data`` → ``Open Data``)."""
    for category in categories:
        if category.get("slug") == slug:
            return str(category.get("label") or slug)
    return WORD_START.sub(lambda match: match.group().upper(), slug.replace("-", " "))


def _pagination(current_page: int, total_pages: int) -> Optional[Dict[str, Any]]:
    if total_pages <= FIRST_PAGE:
        return None
    return {
        "current": current_page,
        "total": total_pages,
        "previous": current_page - 1 if current_page > FIRST_PAGE else None,
        "next": current_page + 1 if current_page < total_pages else None,
    }


def _dataset_card(dataset: Mapping[str, Any], category_slug: str) -> Dict[str, Any]:
    return {
        "title": dataset.get("title") or "",
        "source_attribution": dataset.get("source_attribution") or "",
        "href": f"/data-store/{category_slug}/{dataset.get('slug')}",
    }


class DatasetCatalogue:
    """``build_context`` (the component) and the list fragment's context."""

    def __init__(self, api_factory: ApiFactory = DatasetApi) -> None:
        self._api_factory = api_factory

    def build_context(
        self,
        widget_config: Mapping[str, Any],
        page: Mapping[str, Any],
        route_params: Mapping[str, Any],
        theme_request: ThemeRequest,
    ) -> Dict[str, Any]:
        api = self._api_factory(theme_request)
        try:
            categories = api.categories().get("categories") or []
        except ThemeApiError:
            categories = []
        category_slug = route_params.get(CATEGORY_PARAMETER)
        if not category_slug:
            return {"mode": "index", "categories": categories}
        return {
            "mode": "list",
            "categories": categories,
            "category_label": category_label(category_slug, categories),
            **self._list_context(api, category_slug, theme_request.query_args),
        }

    def list_fragment_context(self, theme_request: ThemeRequest) -> Dict[str, Any]:
        query_args = theme_request.query_args
        return self._list_context(
            self._api_factory(theme_request),
            query_args.get(CATEGORY_PARAMETER) or "",
            query_args,
        )

    @staticmethod
    def _list_context(
        api: Any, category_slug: str, query_args: Mapping[str, Any]
    ) -> Dict[str, Any]:
        current_page = _page_number(query_args.get(PAGE_PARAMETER))
        search_query = (query_args.get(QUERY_PARAMETER) or "").strip()
        request_query: Dict[str, Any] = {
            "category": category_slug,
            "page": current_page,
        }
        if search_query:
            request_query[QUERY_PARAMETER] = search_query
        context: Dict[str, Any] = {
            "category_slug": category_slug,
            "query": search_query,
        }
        try:
            listing = api.datasets(request_query)
        except ThemeApiError as load_error:
            return {**context, "list": {"state": "error", "error": load_error.message}}
        cards = [
            _dataset_card(item, category_slug) for item in listing.get("items") or []
        ]
        return {
            **context,
            "list": {
                "state": "datasets" if cards else "empty",
                "datasets": cards,
                "pagination": _pagination(
                    current_page, int(listing.get("pages") or FIRST_PAGE)
                ),
            },
        }


class DatasetDetail:
    """``build_context(widget_config, page, route_params, theme_request)``."""

    def __init__(self, api_factory: ApiFactory = DatasetApi) -> None:
        self._api_factory = api_factory

    def build_context(
        self,
        widget_config: Mapping[str, Any],
        page: Mapping[str, Any],
        route_params: Mapping[str, Any],
        theme_request: ThemeRequest,
    ) -> Dict[str, Any]:
        slug = route_params.get("dataset_slug") or ""
        try:
            dataset = self._api_factory(theme_request).dataset(slug)
        except ThemeApiError:
            return {"state": "not_found", "not_found_key": NOT_FOUND_KEY}
        return {
            "state": "dataset",
            "dataset": {
                "title": dataset.get("title") or "",
                "source_attribution": dataset.get("source_attribution") or "",
                "description": dataset.get("description") or "",
            },
            "checkout_fields": {
                "source": "dataset",
                "dataset_slug": dataset.get("slug") or slug,
            },
            "tags_custom_fields": tags_and_custom_fields(dataset),
        }
