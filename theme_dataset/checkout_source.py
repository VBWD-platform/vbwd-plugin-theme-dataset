"""The "dataset" checkout source — fe-user ``plugins/dataset/src/checkoutSource.ts``.

``?source=dataset&dataset_slug=<slug>`` buys one dataset one-time. The slug
comes from the request's query (the page render), else from the page URL — the
SPA reads ``window.location.search``; an htmx fragment request carries the page
URL in ``HX-Current-URL``. One line at the dataset's price in the operating
currency, no coupon, no cart; submit = ``POST /api/v1/dataset/orders``, which
answers the PENDING invoice the dispatch table routes.
"""
from decimal import Decimal
from typing import Any, Callable, Dict, Mapping, Optional
from urllib.parse import parse_qs, urlsplit

from plugins.theme.theme.theme_api import ThemeApiError
from plugins.theme.theme.theme_request import ThemeRequest
from plugins.theme_checkout.theme_checkout.checkout_api import CheckoutApi
from plugins.theme_checkout.theme_checkout.checkout_sources import (
    CheckoutRouteContext,
    CheckoutSource,
    CheckoutSummary,
)
from plugins.theme_checkout.theme_checkout.price_display import price_display_view

from .dataset_api import DatasetApi

DATASET_SOURCE_ID = "dataset"
SUMMARY_TEMPLATE = "dataset/checkout_summary.html.j2"
DATASET_SLUG_PARAMETER = "dataset_slug"
CURRENT_URL_HEADER = "HX-Current-URL"
NO_DATASET_SELECTED = "No dataset selected"
BAD_REQUEST = 400

ApiFactory = Callable[[ThemeRequest], Any]


def matches_dataset(context: CheckoutRouteContext) -> bool:
    return context.source == DATASET_SOURCE_ID


def selected_dataset_slug(theme_request: ThemeRequest) -> Optional[str]:
    """``?dataset_slug=`` of the request, else of the page the fragment came from."""
    slug = theme_request.query_args.get(DATASET_SLUG_PARAMETER)
    if slug:
        return str(slug)
    http_request = theme_request.http_request
    current_url = http_request.headers.get(CURRENT_URL_HEADER) if http_request else None
    if not current_url:
        return None
    return parse_qs(urlsplit(current_url).query).get(DATASET_SLUG_PARAMETER, [None])[0]


class DatasetCheckout:
    """Prices and submits the one-time dataset purchase of one checkout request."""

    def __init__(
        self,
        api_factory: ApiFactory = DatasetApi,
        checkout_api_factory: ApiFactory = CheckoutApi,
    ) -> None:
        self._api_factory = api_factory
        self._checkout_api_factory = checkout_api_factory

    def checkout_source(self) -> CheckoutSource:
        return CheckoutSource(
            id=DATASET_SOURCE_ID,
            matches=matches_dataset,
            load_summary=self.load_summary,
            submit=self.submit,
            summary_template=SUMMARY_TEMPLATE,
            cart_key=None,
        )

    @staticmethod
    def _required_slug(theme_request: ThemeRequest) -> str:
        slug = selected_dataset_slug(theme_request)
        if not slug:
            raise ThemeApiError(BAD_REQUEST, NO_DATASET_SELECTED)
        return slug

    def load_summary(
        self, theme_request: ThemeRequest, context: CheckoutRouteContext
    ) -> CheckoutSummary:
        dataset = self._api_factory(theme_request).dataset(
            self._required_slug(theme_request)
        )
        currency = self._checkout_api_factory(theme_request).default_currency()
        price = float(dataset.get("price") or 0)
        line = {
            "type": "dataset",
            "id": dataset.get("id"),
            "name": dataset.get("title"),
            "price": price,
            "quantity": 1,
            "currency": currency,
        }
        return CheckoutSummary(
            line_items=(line,),
            order_total=Decimal(str(price)),
            currency=currency,
            template_context={
                "lines": [
                    {
                        "id": line["id"],
                        "name": line["name"] or "",
                        "price": price_display_view(price, price, currency),
                    }
                ]
            },
        )

    def submit(
        self,
        theme_request: ThemeRequest,
        context: CheckoutRouteContext,
        payment_method_code: Optional[str],
    ) -> Mapping[str, Any]:
        payload: Dict[str, Any] = {
            DATASET_SLUG_PARAMETER: self._required_slug(theme_request)
        }
        if payment_method_code:
            payload["payment_method_code"] = payment_method_code
        order = self._api_factory(theme_request).create_order(payload)
        return {
            "invoice": {
                "id": order.get("invoice_id"),
                "invoice_number": order.get("invoice_number"),
                "status": order.get("status"),
                "total_amount": order.get("total_amount"),
                "currency": order.get("currency"),
            },
            "message": "Order created",
        }
