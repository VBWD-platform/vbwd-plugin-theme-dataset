"""Render theme_dataset templates through the REAL theme renderer (basic theme +
the templates/translations theme_cms, theme_checkout and theme_dataset contribute).
"""
from flask import Flask

from plugins.theme import ThemePlugin
from plugins.theme_checkout.theme_checkout import plugin_paths as checkout_paths
from plugins.theme_cms.theme_cms import plugin_paths as cms_paths
from plugins.theme_dataset.theme_dataset.plugin_paths import (
    TEMPLATES_DIRECTORY,
    TRANSLATIONS_DIRECTORY,
)


def theme_plugin() -> ThemePlugin:
    plugin = ThemePlugin()
    plugin.on_enable()
    registry = plugin.theme_registry
    for paths in (cms_paths, checkout_paths):
        registry.add_contributed_template_path(paths.TEMPLATES_DIRECTORY)
        registry.add_contributed_translation_path(paths.TRANSLATIONS_DIRECTORY)
    registry.add_contributed_template_path(TEMPLATES_DIRECTORY)
    registry.add_contributed_translation_path(TRANSLATIONS_DIRECTORY)
    return plugin


def render(plugin: ThemePlugin, template: str, context) -> str:
    app = Flask(__name__)
    app.testing = True
    with app.app_context():
        return plugin.renderer.render(
            template, {"language": "en", "default_language": "en", **context}
        )
