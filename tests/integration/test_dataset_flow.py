"""S152-08 — theme_dataset on a real ``create_app`` (theme mode).

The S152-00 dataset e2e journeys through the themed renderer: the Data-store
index → category list → dataset detail (CMS pages ``data-store`` /
``dataset-detail`` with their widgets), the list fragment's search, and a
one-time purchase through the themed checkout fragments
(``?source=dataset&dataset_slug=…`` → invoice method → confirmation).
"""
import re
import uuid

import pytest

from plugins.theme_cms.tests.integration.cms_seed import unique
from plugins.theme_checkout.tests.integration.themed_stack import (
    FE_USER_ROOT,
    RENDER,
    confirmation_page,
    contract_drift,
    contract_misses,
    ensure_euro_currency,
    ensure_invoice_payment_method,
    post_island,
    regions_html,
    submit_checkout,
    themed_page_gotos,
)

CONFIRMATION = re.compile(r"^/checkout/confirmation\?invoice_id=([0-9a-f-]+)$")


def _testid(html, testid):
    return re.search(rf'<[^>]*data-testid="{re.escape(testid)}"[^>]*>', html)


def _cms_page(cms, client, slug, component):
    existing = client.get(f"/api/v1/cms/posts/{slug}")
    if existing.status_code == 200:
        return existing.get_json()
    return cms.page_with_widgets([cms.vue_widget(component)], slug=slug)


@pytest.fixture
def seeded(client, admin_headers, cms):
    """One active dataset in its own category + the two Data-store CMS pages."""
    ensure_euro_currency(client, admin_headers)
    term = cms.term("dataset_category", "S152-08 Datasets", slug=unique("s152-08-cat"))
    slug = f"s152-08-dataset-{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/api/v1/admin/datasets",
        json={
            "slug": slug,
            "title": "S152-08 Themed Dataset",
            "description": "Seeded by the theme_dataset integration tests.",
            "source_attribution": "S152 fixture",
            "price": 7,
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.get_json()
    dataset = created.get_json()
    assigned = client.post(
        f"/api/v1/admin/datasets/{dataset['id']}/categories",
        json={"term_id": term["id"]},
        headers=admin_headers,
    )
    assert assigned.status_code in (200, 201), assigned.get_json()
    _cms_page(cms, client, "data-store", "DatasetCatalogue")
    _cms_page(cms, client, "dataset-detail", "DatasetDetail")
    return {"dataset": dataset, "category_slug": term["slug"]}


def test_browse_index_category_and_detail(client, seeded):
    category, dataset = seeded["category_slug"], seeded["dataset"]

    index = client.get("/data-store", headers=RENDER).get_data(as_text=True)
    listing = client.get(f"/data-store/{category}", headers=RENDER).get_data(
        as_text=True
    )
    detail = client.get(
        f"/data-store/{category}/{dataset['slug']}", headers=RENDER
    ).get_data(as_text=True)

    assert '<meta name="vbwd-frontend" content="theme">' in index
    assert _testid(index, "dataset-catalogue-index")
    assert f'href="/data-store/{category}"' in index
    assert _testid(listing, "dataset-catalogue-list")
    assert re.search(
        rf'<a href="/data-store/{category}/{dataset["slug"]}" class="dataset-card" data-testid="dataset-card">',
        listing,
    )
    assert re.search(
        r'<h1 class="dataset-detail-name">\s*S152-08 Themed Dataset\s*</h1>', detail
    )
    assert _testid(detail, "dataset-get-btn")


def test_the_list_fragment_searches_within_the_category(client, seeded):
    category = seeded["category_slug"]

    hit = client.get(
        "/_render/_fragment/dataset/list",
        query_string={"category_slug": category, "q": "Themed Dataset"},
    ).get_data(as_text=True)
    miss = client.get(
        "/_render/_fragment/dataset/list",
        query_string={"category_slug": category, "q": "zzz-no-such-dataset"},
    ).get_data(as_text=True)

    assert _testid(hit, "dataset-card")
    assert "No datasets found." in miss


def test_the_routes_fall_back_to_the_spa_without_the_render_marker(client, seeded):
    assert client.get("/data-store").status_code == 404


def test_a_full_themed_dataset_checkout(client, bearer, admin_headers, cms, seeded):
    dataset = seeded["dataset"]
    ensure_invoice_payment_method(client, admin_headers)
    confirmation_page(cms, client)
    checkout_url = f"/checkout?source=dataset&dataset_slug={dataset['slug']}"
    page = client.get(checkout_url, headers=RENDER).get_data(as_text=True)
    fields = {"source": "dataset", "tarif_plan_id": "", "cart_type": "", "is_cart": ""}
    from_page = {**bearer, "HX-Current-URL": f"http://localhost{checkout_url}"}

    island = post_island(client, from_page, fields)
    submitted = submit_checkout(client, from_page, fields)

    holder = re.search(r'<div class="checkout-island"[^>]*>', page).group(0)
    assert "data-vbwd-cart=" not in holder
    assert re.search(
        rf'data-testid="dataset-line-item-{dataset["id"]}"><span>S152-08 Themed Dataset</span>',
        island,
    )
    assert submitted.status_code == 200, submitted.get_data(as_text=True)
    invoice_id = CONFIRMATION.match(submitted.headers["HX-Redirect"]).group(1)
    confirmation = regions_html(
        client, bearer, f"/checkout/confirmation?invoice_id={invoice_id}"
    )
    assert _testid(confirmation, "invoice-details")
    assert re.search(
        r'data-testid="line-item-row"><td>[^<]*S152-08 Themed Dataset', confirmation
    )


# ── e2e DOM contract (plugins/dataset/tests/e2e) ─────────────────────────────

BROWSE_SPEC = "plugins/dataset/tests/e2e/data-store-browse.spec.ts"
CHECKOUT_SPEC = "plugins/dataset/tests/e2e/dataset-checkout.spec.ts"
DASHBOARD_SPEC = "plugins/dataset/tests/e2e/dataset-dashboard.spec.ts"
FIXTURES = "plugins/dataset/tests/e2e/support/datasetFixtures.ts"


def _dataset_contract(seeded):
    category, dataset = seeded["category_slug"], seeded["dataset"]
    detail_href = f"/data-store/{category}/{dataset['slug']}"
    return [
        (
            '[data-testid="dataset-catalogue-index"]',
            BROWSE_SPEC,
            37,
            "index",
            r'data-testid="dataset-catalogue-index"',
        ),
        (
            'a[href="/data-store/${seeded.categorySlug}"]',
            BROWSE_SPEC,
            39,
            "index",
            rf'<a href="/data-store/{category}"',
        ),
        (
            '[data-testid="dataset-catalogue-list"]',
            BROWSE_SPEC,
            44,
            "list",
            r'data-testid="dataset-catalogue-list"',
        ),
        (
            '[data-testid="dataset-card"][href="/data-store/',
            BROWSE_SPEC,
            52,
            "list",
            rf'href="{detail_href}" class="dataset-card" data-testid="dataset-card"',
        ),
        (
            "h1.dataset-detail-name",
            BROWSE_SPEC,
            58,
            "detail",
            r'<h1 class="dataset-detail-name">',
        ),
        (
            '[data-testid="dataset-get-btn"]',
            BROWSE_SPEC,
            59,
            "detail",
            r'data-testid="dataset-get-btn"',
        ),
        (
            '[data-testid="dataset-get-btn"]',
            CHECKOUT_SPEC,
            43,
            "detail",
            r'<form method="get" action="/checkout">',
        ),
        (
            '[data-testid="dataset-line-item-${seeded.datasetId}"]',
            CHECKOUT_SPEC,
            57,
            "island",
            rf'data-testid="dataset-line-item-{dataset["id"]}"',
        ),
        (
            '[data-testid="payment-method-invoice"]',
            FIXTURES,
            89,
            "island",
            r'data-testid="payment-method-invoice"',
        ),
        (
            '[data-testid="terms-checkbox"]',
            FIXTURES,
            90,
            "island",
            r'data-testid="terms-checkbox"',
        ),
        (
            '[data-testid="confirm-checkout"]',
            CHECKOUT_SPEC,
            60,
            "island",
            r'data-testid="confirm-checkout"',
        ),
        (
            '[data-testid="confirmation-banner"]',
            CHECKOUT_SPEC,
            67,
            "confirmation",
            r'data-testid="confirmation-banner"',
        ),
        (
            '[data-testid="invoice-details"]',
            CHECKOUT_SPEC,
            68,
            "confirmation",
            r'data-testid="invoice-details"',
        ),
        (
            '[data-testid="line-item-row"]',
            CHECKOUT_SPEC,
            69,
            "confirmation",
            r'data-testid="line-item-row"><td>[^<]*S152-08 Themed Dataset',
        ),
    ]


def test_every_dataset_spec_selector_is_in_the_themed_output(
    client, bearer, admin_headers, cms, seeded
):
    category, dataset = seeded["category_slug"], seeded["dataset"]
    ensure_invoice_payment_method(client, admin_headers)
    confirmation_page(cms, client)
    checkout_url = f"/checkout?source=dataset&dataset_slug={dataset['slug']}"
    from_page = {**bearer, "HX-Current-URL": f"http://localhost{checkout_url}"}
    fields = {"source": "dataset", "tarif_plan_id": "", "cart_type": "", "is_cart": ""}
    island = post_island(client, from_page, fields)
    invoice_id = CONFIRMATION.match(
        submit_checkout(client, from_page, fields).headers["HX-Redirect"]
    ).group(1)
    outputs = {
        "index": client.get("/data-store", headers=RENDER).get_data(as_text=True),
        "list": client.get(f"/data-store/{category}", headers=RENDER).get_data(
            as_text=True
        ),
        "detail": client.get(
            f"/data-store/{category}/{dataset['slug']}", headers=RENDER
        ).get_data(as_text=True),
        "island": island,
        "confirmation": regions_html(
            client, bearer, f"/checkout/confirmation?invoice_id={invoice_id}"
        ),
    }

    assert contract_misses(_dataset_contract(seeded), outputs) == []


def test_the_dataset_spec_lines_still_use_these_selectors():
    if not (FE_USER_ROOT / BROWSE_SPEC).is_file():
        pytest.skip("fe-user is not next to vbwd-backend (plugin CI)")
    seeded = {"category_slug": "c", "dataset": {"id": "i", "slug": "s"}}

    assert contract_drift(_dataset_contract(seeded)) == []


def test_the_dashboard_spec_drives_only_the_spa():
    """dataset-dashboard.spec.ts checks ``/dashboard/datasets`` (never themed, D7)."""
    if not (FE_USER_ROOT / DASHBOARD_SPEC).is_file():
        pytest.skip("fe-user is not next to vbwd-backend (plugin CI)")

    assert themed_page_gotos(DASHBOARD_SPEC) == []
