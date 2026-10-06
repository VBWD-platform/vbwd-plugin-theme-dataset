"""S152-08 — what theme_dataset registers on enable.

The three Data-store routes (fe-user mounts them as ``CmsPage`` with the fixed
slugs ``data-store`` / ``dataset-detail``) render those CMS pages with the
route params in context; the list fragment backs the search and pager; the
``DatasetCatalogue`` / ``DatasetDetail`` widget twins go into theme_cms and the
``dataset`` checkout source into theme_checkout. Everything is owned by fe-user
``dataset`` (same toggle as the SPA).
"""
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import pytest
from flask import Flask

from plugins.theme import ThemePlugin
from plugins.theme_checkout import ThemeCheckoutPlugin
from plugins.theme_checkout.theme_checkout.checkout_sources import CheckoutRouteContext
from plugins.theme_cms import ThemeCmsPlugin
from plugins.theme_cms.theme_cms.pages import DISPATCH_TEMPLATE
from plugins.theme_dataset import ThemeDatasetPlugin
from plugins.theme_dataset.theme_dataset.plugin_paths import (
    STYLESHEETS_DIRECTORY,
    TEMPLATES_DIRECTORY,
    TRANSLATIONS_DIRECTORY,
)
from plugins.theme_dataset.theme_dataset.registration import dataset_pages

FE_USER_DATASET_INDEX = (
    Path(__file__).resolve().parents[5]
    / "vbwd-fe-user"
    / "plugins"
    / "dataset"
    / "index.ts"
)


def _app(plugins):
    app = Flask(__name__)
    app.plugin_manager = SimpleNamespace(get_plugin=plugins.get)
    return app


@pytest.fixture
def enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("VBWD_VAR_DIR", str(tmp_path / "var"))
    plugins = {
        "theme": ThemePlugin(),
        "theme_cms": ThemeCmsPlugin(),
        "theme_checkout": ThemeCheckoutPlugin(),
        "theme_dataset": ThemeDatasetPlugin(),
    }
    with _app(plugins).app_context():
        for plugin in plugins.values():
            plugin.on_enable()
        yield SimpleNamespace(**plugins)


def test_registers_the_three_data_store_routes(enabled):
    pages = {page.rule: page for page in enabled.theme.page_registry.pages()}

    for rule in (
        "/data-store",
        "/data-store/<category_slug>",
        "/data-store/<category_slug>/<dataset_slug>",
    ):
        assert pages[rule].owner_fe_user_plugin == "dataset", rule
        assert pages[rule].template == DISPATCH_TEMPLATE


def test_each_route_renders_its_cms_page_with_the_route_params():
    rendered = []
    fake_cms_pages = SimpleNamespace(
        cms_slug_page_context=lambda request, slug: rendered.append(
            (slug, dict(request.view_args))
        )
        or {}
    )
    pages = {page.rule: page for page in dataset_pages(fake_cms_pages)}

    for rule, view_args in (
        ("/data-store", {}),
        ("/data-store/<category_slug>", {"category_slug": "env"}),
        (
            "/data-store/<category_slug>/<dataset_slug>",
            {"category_slug": "env", "dataset_slug": "air"},
        ),
    ):
        pages[rule].build_context(
            SimpleNamespace(view_args=MappingProxyType(view_args))
        )

    assert rendered == [
        ("data-store", {}),
        ("data-store", {"category_slug": "env"}),
        ("dataset-detail", {"category_slug": "env", "dataset_slug": "air"}),
    ]


def test_registers_the_list_fragment(enabled):
    fragments = {
        fragment.rule: fragment
        for fragment in enabled.theme.fragment_registry.fragments()
    }

    fragment = fragments["/_render/_fragment/dataset/list"]
    assert fragment.methods == ("GET",)
    assert fragment.owner_fe_user_plugin == "dataset"


def test_registers_the_widget_twins_and_the_checkout_source(enabled):
    for name in ("DatasetCatalogue", "DatasetDetail"):
        assert enabled.theme_cms.component_registry.resolve(name) is not None, name
    source = enabled.theme_checkout.source_registry.find(
        CheckoutRouteContext(source="dataset")
    )
    assert source.id == "dataset"


def test_contributes_templates_translations_and_stylesheets(enabled):
    registry = enabled.theme.theme_registry

    assert TEMPLATES_DIRECTORY in registry.contributed_template_paths()
    assert TRANSLATIONS_DIRECTORY in registry.contributed_translation_paths()
    assert STYLESHEETS_DIRECTORY in registry.contributed_stylesheet_paths()


def test_enabling_twice_registers_once(enabled):
    with _app(vars(enabled)).app_context():
        enabled.theme_dataset.on_enable()

    rules = [page.rule for page in enabled.theme.page_registry.pages()]
    assert rules.count("/data-store") == 1


def test_the_routes_and_widgets_are_the_ones_fe_user_registers():
    if not FE_USER_DATASET_INDEX.is_file():
        pytest.skip("fe-user dataset plugin is not next to vbwd-backend (plugin CI)")
    source = FE_USER_DATASET_INDEX.read_text(encoding="utf-8")

    for path in (
        "'/data-store'",
        "'/data-store/:category_slug'",
        "'/data-store/:category_slug/:dataset_slug'",
    ):
        assert f"path: {path}" in source
    for name in ("DatasetCatalogue", "DatasetDetail"):
        assert f"registerCmsVueComponent('{name}'" in source
    assert "props: { slug: 'data-store' }" in source
    assert "props: { slug: 'dataset-detail' }" in source
