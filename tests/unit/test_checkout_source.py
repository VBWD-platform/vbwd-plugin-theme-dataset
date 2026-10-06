"""S152-08 — the "dataset" checkout source, the twin of fe-user
``plugins/dataset/src/checkoutSource.ts``.

``?source=dataset&dataset_slug=<slug>``: one dataset, bought one-time. The slug
comes from the route context, else from the current URL query — the SPA reads
``window.location.search``; a themed fragment request carries the page URL in
htmx's ``HX-Current-URL``. One line at the dataset's price in the operating
currency; no cart; submit = ``POST /api/v1/dataset/orders``.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from plugins.theme.theme.theme_api import ThemeApiError
from plugins.theme_checkout.tests.unit.fakes import FakeCheckoutApi, FakeThemeRequest
from plugins.theme_checkout.theme_checkout.checkout_sources import CheckoutRouteContext
from plugins.theme_dataset.tests.unit.fakes import FakeDatasetApi
from plugins.theme_dataset.theme_dataset.checkout_source import DatasetCheckout

CONTEXT = CheckoutRouteContext(source="dataset")


def _checkout(api=None):
    api = api or FakeDatasetApi()
    checkout = DatasetCheckout(
        api.factory, FakeCheckoutApi(default_currency="EUR").factory
    )
    return checkout, api


def _request(query=None, current_url=None):
    theme_request = FakeThemeRequest(query or {})
    headers = {"HX-Current-URL": current_url} if current_url else {}
    theme_request.http_request = SimpleNamespace(headers=headers)
    return theme_request


def test_the_source_matches_source_dataset_and_has_no_cart():
    source = _checkout()[0].checkout_source()

    assert source.id == "dataset"
    assert source.matches(CONTEXT) is True
    assert source.matches(CheckoutRouteContext(plan_slug="pro")) is False
    assert source.cart_key is None
    assert source.summary_template == "dataset/checkout_summary.html.j2"


def test_the_slug_comes_from_the_query_on_the_page_render():
    checkout, api = _checkout()

    summary = checkout.load_summary(_request({"dataset_slug": "air-quality"}), CONTEXT)

    assert api.calls == [("dataset", "air-quality")]
    assert summary.line_items == (
        {
            "type": "dataset",
            "id": "ds-1",
            "name": "Air Quality",
            "price": 7.0,
            "quantity": 1,
            "currency": "EUR",
        },
    )
    assert summary.order_total == Decimal("7")
    assert summary.currency == "EUR"


def test_a_fragment_request_reads_the_slug_from_the_current_url():
    checkout, api = _checkout()

    checkout.load_summary(
        _request(
            current_url="https://shop.example/checkout?source=dataset&dataset_slug=air-quality"
        ),
        CONTEXT,
    )

    assert api.calls == [("dataset", "air-quality")]


def test_no_slug_is_the_spa_error():
    checkout, api = _checkout()

    with pytest.raises(ThemeApiError) as raised:
        checkout.load_summary(_request(), CONTEXT)

    assert raised.value.message == "No dataset selected"
    assert api.calls == []


def test_the_summary_view_lists_the_dataset_line():
    checkout, _api = _checkout()

    summary = checkout.load_summary(_request({"dataset_slug": "air-quality"}), CONTEXT)

    line = summary.template_context["lines"][0]
    assert line["id"] == "ds-1" and line["name"] == "Air Quality"
    assert line["price"].label == "€7.00"


def test_submit_posts_a_one_time_order_and_answers_its_invoice():
    checkout, api = _checkout()

    result = checkout.submit(
        _request({"dataset_slug": "air-quality"}), CONTEXT, "invoice"
    )

    assert api.calls[-1] == (
        "order",
        {"dataset_slug": "air-quality", "payment_method_code": "invoice"},
    )
    assert result["invoice"]["id"] == "inv-9"
    assert result["invoice"]["status"] == "PENDING"


def test_submit_without_a_payment_method_sends_none():
    checkout, api = _checkout()

    checkout.submit(_request({"dataset_slug": "air-quality"}), CONTEXT, None)

    assert api.calls[-1] == ("order", {"dataset_slug": "air-quality"})
