"""Theme adapter mirroring the fe-user dataset plugin (S152-08).

Renders only when ``VBWD_FRONTEND_MODE=theme``; in the default ``vue`` mode the
Vue SPA serves every page. On enable it contributes its templates,
translations and ported stylesheet and registers the three Data-store routes
(their CMS pages through theme_cms's pipeline), the list fragment, the
``DatasetCatalogue`` / ``DatasetDetail`` widget twins (into theme_cms) and the
``dataset`` checkout source (into theme_checkout). It talks to the backend over
the public API only (D3); ``/dashboard/datasets*`` stays the SPA (D7).
"""
from typing import Optional

from flask import current_app

from vbwd.plugins.base import BasePlugin, PluginMetadata

from plugins.theme.theme.page_registry import resolve_theme_plugin
from plugins.theme_checkout.theme_checkout.checkout_sources import (
    THEME_CHECKOUT_PLUGIN_NAME,
)
from plugins.theme_cms.theme_cms.pages import CmsPages
from plugins.theme_cms.theme_cms.registries import THEME_CMS_PLUGIN_NAME
from plugins.theme_dataset.theme_dataset.catalogue import DatasetCatalogue
from plugins.theme_dataset.theme_dataset.checkout_source import DatasetCheckout
from plugins.theme_dataset.theme_dataset.plugin_paths import (
    STYLESHEETS_DIRECTORY,
    TEMPLATES_DIRECTORY,
    TRANSLATIONS_DIRECTORY,
)
from plugins.theme_dataset.theme_dataset.registration import (
    dataset_components,
    dataset_fragments,
    dataset_pages,
)


class ThemeDatasetPlugin(BasePlugin):
    """Theme adapter mirroring the fe-user dataset plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="theme_dataset",
            version="1.0.0",
            author="VBWD Team",
            description="Theme adapter mirroring the fe-user dataset plugin.",
            dependencies=["theme>=1.0", "dataset", "theme_checkout", "theme_cms"],
        )

    def on_enable(self) -> None:
        plugin_manager = getattr(current_app, "plugin_manager")
        # Declared dependencies: enabled before this plugin (dependency order).
        theme_cms_plugin = plugin_manager.get_plugin(THEME_CMS_PLUGIN_NAME)
        plugin_manager.get_plugin(THEME_CHECKOUT_PLUGIN_NAME).source_registry.register(
            DatasetCheckout().checkout_source()
        )
        theme_plugin = resolve_theme_plugin()
        if (
            TEMPLATES_DIRECTORY
            in theme_plugin.theme_registry.contributed_template_paths()
        ):
            return
        catalogue = DatasetCatalogue()
        for component in dataset_components(catalogue):
            theme_cms_plugin.component_registry.register(component)
        theme_registry = theme_plugin.theme_registry
        theme_registry.add_contributed_template_path(TEMPLATES_DIRECTORY)
        theme_registry.add_contributed_translation_path(TRANSLATIONS_DIRECTORY)
        theme_registry.add_contributed_stylesheet_path(STYLESHEETS_DIRECTORY)
        cms_pages = CmsPages(
            theme_cms_plugin.page_type_registry, theme_cms_plugin.component_registry
        )
        for page in dataset_pages(cms_pages):
            theme_plugin.page_registry.register(page)
        for fragment in dataset_fragments(catalogue):
            theme_plugin.fragment_registry.register(fragment)

    def get_url_prefix(self) -> Optional[str]:
        # No blueprint of its own: the theme mounts the registered pages.
        return ""
