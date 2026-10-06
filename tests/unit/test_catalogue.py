"""S152-08 — the DatasetCatalogue + DatasetDetail CMS components (S110 views).

* ``/data-store`` (no ``category_slug``): the category index from
  ``GET /api/v1/dataset/categories``;
* ``/data-store/<category_slug>``: the category's datasets from
  ``GET /api/v1/dataset`` (``category`` + ``page`` + ``q``), titled with the
  category label (else the title-cased slug);
* ``/data-store/<category>/<dataset_slug>``: ``GET /api/v1/dataset/<slug>``;
  "Get Dataset" submits to ``/checkout?source=dataset&dataset_slug=<slug>``.
"""
from plugins.theme.theme.theme_api import ThemeApiError
from plugins.theme_checkout.tests.unit.fakes import FakeThemeRequest
from plugins.theme_dataset.tests.unit.fakes import FakeDatasetApi
from plugins.theme_dataset.theme_dataset.catalogue import (
    DatasetCatalogue,
    DatasetDetail,
)


def _catalogue(route_params, query=None, api=None):
    api = api or FakeDatasetApi()
    context = DatasetCatalogue(api.factory).build_context(
        {}, {}, route_params, FakeThemeRequest(query or {})
    )
    return context, api


def test_the_index_lists_the_categories():
    context, api = _catalogue({})

    assert context["mode"] == "index"
    assert [category["slug"] for category in context["categories"]] == [
        "environment",
        "finance",
    ]
    assert api.calls == [("categories",)]


def test_a_category_lists_its_datasets_under_its_label():
    context, api = _catalogue(
        {"category_slug": "environment"}, {"q": "air", "page": "2"}
    )

    assert context["mode"] == "list"
    assert context["category_label"] == "Environment"
    assert context["list"]["state"] == "datasets"
    assert (
        context["list"]["datasets"][0]["href"] == "/data-store/environment/air-quality"
    )
    assert ("datasets", {"category": "environment", "page": 2, "q": "air"}) in api.calls


def test_an_unknown_category_label_is_the_title_cased_slug():
    context, _api = _catalogue({"category_slug": "open-data"})

    assert context["category_label"] == "Open Data"


def test_list_states_empty_error_and_pagination():
    empty, _api = _catalogue(
        {"category_slug": "x"}, api=FakeDatasetApi(datasets={"items": [], "pages": 1})
    )
    failed, _api = _catalogue(
        {"category_slug": "x"}, api=FakeDatasetApi(datasets=ThemeApiError(500, "boom"))
    )
    paged, _api = _catalogue(
        {"category_slug": "x"},
        {"page": "2"},
        api=FakeDatasetApi(datasets={"items": [], "page": 2, "pages": 3}),
    )

    assert empty["list"]["state"] == "empty"
    assert failed["list"]["state"] == "error" and failed["list"]["error"] == "boom"
    assert paged["list"]["pagination"] == {
        "current": 2,
        "total": 3,
        "previous": 1,
        "next": 3,
    }


def test_the_categories_failing_degrade_to_none():
    context, _api = _catalogue(
        {}, api=FakeDatasetApi(categories=ThemeApiError(500, "x"))
    )

    assert context["categories"] == []


def _detail(route_params, api=None):
    api = api or FakeDatasetApi()
    return DatasetDetail(api.factory).build_context(
        {}, {}, route_params, FakeThemeRequest()
    )


def test_the_detail_shows_the_dataset_and_its_checkout_target():
    context = _detail({"category_slug": "environment", "dataset_slug": "air-quality"})

    assert context["state"] == "dataset"
    assert context["dataset"]["title"] == "Air Quality"
    assert context["dataset"]["source_attribution"] == "EEA"
    assert context["checkout_fields"] == {
        "source": "dataset",
        "dataset_slug": "air-quality",
    }
    assert context["tags_custom_fields"] is None


def test_an_unknown_dataset_is_not_found():
    context = _detail(
        {"dataset_slug": "nope"},
        api=FakeDatasetApi(dataset=ThemeApiError(404, "Not found")),
    )

    assert context["state"] == "not_found"
