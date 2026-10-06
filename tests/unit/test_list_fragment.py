"""S152-08 — the dataset list fragment backs the catalogue's search and pager.

``GET /_render/_fragment/dataset/list?category_slug=…&q=…&page=…`` re-renders
the list body from the same ``GET /api/v1/dataset`` the page uses.
"""
from plugins.theme_checkout.tests.unit.fakes import FakeThemeRequest
from plugins.theme_dataset.tests.unit.fakes import FakeDatasetApi
from plugins.theme_dataset.theme_dataset.catalogue import DatasetCatalogue


def test_the_fragment_lists_the_posted_category_query_and_page():
    api = FakeDatasetApi()

    context = DatasetCatalogue(api.factory).list_fragment_context(
        FakeThemeRequest({"category_slug": "environment", "q": "air", "page": "3"})
    )

    assert api.calls == [
        ("datasets", {"category": "environment", "page": 3, "q": "air"})
    ]
    assert context["list"]["state"] == "datasets"
    assert context["category_slug"] == "environment"


def test_a_garbage_page_is_page_one_and_an_empty_query_is_dropped():
    api = FakeDatasetApi()

    DatasetCatalogue(api.factory).list_fragment_context(
        FakeThemeRequest({"category_slug": "environment", "q": " ", "page": "x"})
    )

    assert api.calls == [("datasets", {"category": "environment", "page": 1})]
