"""S152-08 — theme_dataset markup keeps the SPA's DOM contract (D2).

``DatasetCatalogue.vue`` (index + list, ``dataset-catalogue-index`` /
``dataset-catalogue-list`` / ``dataset-card`` with its href / ``dataset-search``),
``DatasetDetail.vue`` (``h1.dataset-detail-name``, ``dataset-get-btn`` submitting
to ``/checkout?source=dataset&dataset_slug=…``) and ``DatasetCheckoutSummary.vue``
(``dataset-checkout-summary`` / ``dataset-line-item-<id>``).
"""
import re

import pytest

from plugins.theme.theme.theme_api import ThemeApiError
from plugins.theme_checkout.tests.unit.fakes import FakeCheckoutApi, FakeThemeRequest
from plugins.theme_checkout.theme_checkout.checkout_sources import CheckoutRouteContext
from plugins.theme_dataset.tests.unit.fakes import FakeDatasetApi
from plugins.theme_dataset.tests.unit.template_harness import render, theme_plugin
from plugins.theme_dataset.theme_dataset.catalogue import (
    DatasetCatalogue,
    DatasetDetail,
)
from plugins.theme_dataset.theme_dataset.checkout_source import DatasetCheckout

CATALOGUE = "dataset/components/dataset_catalogue.html.j2"
DETAIL = "dataset/components/dataset_detail.html.j2"
LIST_FRAGMENT = "dataset/_list.html.j2"


@pytest.fixture(scope="module")
def plugin():
    return theme_plugin()


@pytest.fixture(autouse=True)
def isolated_var_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("VBWD_VAR_DIR", str(tmp_path / "var"))


def _testid(html, testid):
    return re.search(rf'<[^>]*data-testid="{re.escape(testid)}"[^>]*>', html)


def _catalogue_html(plugin, route_params, api=None):
    context = DatasetCatalogue((api or FakeDatasetApi()).factory).build_context(
        {}, {}, route_params, FakeThemeRequest()
    )
    return render(plugin, CATALOGUE, {"component_context": context})


def test_the_index_links_each_category(plugin):
    html = _catalogue_html(plugin, {})

    assert re.search(
        r'<div class="dataset-category-index" data-testid="dataset-catalogue-index">',
        html,
    )
    assert re.search(
        r'<h1 class="dataset-category-index__title">\s*Data Store\s*</h1>', html
    )
    assert re.search(
        r'<a href="/data-store/environment" class="dataset-category-card">'
        r'<h2 class="dataset-category-card__title">Environment</h2></a>',
        html,
    )


def test_the_list_has_the_search_and_linked_cards(plugin):
    html = _catalogue_html(plugin, {"category_slug": "environment"})

    assert _testid(html, "dataset-catalogue-list")
    assert re.search(r'<h1 class="dataset-list-title">Environment</h1>', html)
    search = _testid(html, "dataset-search").group(0)
    assert 'placeholder="Search datasets..."' in search
    assert 'hx-get="/_render/_fragment/dataset/list"' in search
    assert re.search(
        r'<a href="/data-store/environment/air-quality" class="dataset-card" data-testid="dataset-card">',
        html,
    )
    assert '<span class="dataset-card-source">by EEA</span>' in html


def test_list_states(plugin):
    empty = _catalogue_html(
        plugin,
        {"category_slug": "x"},
        FakeDatasetApi(datasets={"items": [], "pages": 1}),
    )
    failed = _catalogue_html(
        plugin,
        {"category_slug": "x"},
        FakeDatasetApi(datasets=ThemeApiError(500, "boom")),
    )

    assert '<div class="dataset-empty">No datasets found.</div>' in empty
    assert '<div class="dataset-error">boom</div>' in failed


def test_the_detail_cta_submits_to_the_dataset_checkout(plugin):
    context = DatasetDetail(FakeDatasetApi().factory).build_context(
        {}, {}, {"dataset_slug": "air-quality"}, FakeThemeRequest()
    )

    html = render(plugin, DETAIL, {"component_context": context})

    assert re.search(r'<h1 class="dataset-detail-name">\s*Air Quality\s*</h1>', html)
    assert re.search(r'<p class="dataset-detail-source">\s*by EEA\s*</p>', html)
    form = re.search(
        r'<form method="get" action="/checkout"[^>]*>(.*?)</form>', html, re.S
    )
    assert form is not None
    fields = re.findall(
        r'<input type="hidden" name="(\w+)" value="([^"]*)">', form.group(1)
    )
    assert fields == [("source", "dataset"), ("dataset_slug", "air-quality")]
    assert re.search(r'data-testid="dataset-get-btn">\s*Get Dataset\s*<', form.group(1))
    assert '<p class="dataset-detail-description">' in html


def test_a_missing_dataset_shows_not_found(plugin):
    context = DatasetDetail(
        FakeDatasetApi(dataset=ThemeApiError(404, "Not found")).factory
    ).build_context({}, {}, {"dataset_slug": "nope"}, FakeThemeRequest())

    html = render(plugin, DETAIL, {"component_context": context})

    assert '<div class="dataset-error">Dataset not found.</div>' in html


def test_the_checkout_summary_lists_the_dataset_line(plugin):
    checkout = DatasetCheckout(
        FakeDatasetApi().factory, FakeCheckoutApi(default_currency="EUR").factory
    )
    summary = checkout.load_summary(
        FakeThemeRequest({"dataset_slug": "air-quality"}),
        CheckoutRouteContext(source="dataset"),
    )

    html = render(
        plugin,
        "dataset/checkout_summary.html.j2",
        {"summary": {"line_items": summary.line_items, **summary.template_context}},
    )

    assert _testid(html, "dataset-checkout-summary")
    assert re.search(
        r'<div class="plan-row" data-testid="dataset-line-item-ds-1"><span>Air Quality</span>'
        r'<span><span class="price-display">',
        html,
    )
