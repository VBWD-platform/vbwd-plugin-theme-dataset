"""S152-08 — the SPA's structural CSS for the Data-store views.

S152-06c rules (theme ``tests/css_inventory`` helpers): every class a theme_dataset
template uses that the mirrored Vue component styles has a ported rule (minus
documented exclusions), no invented rule, no colour outside a
``var(--…, fallback)`` chain. The S110 dataset views hard-code their colours,
so only geometry is ported. The coverage half skips without fe-user.
"""
from pathlib import Path

import pytest

from plugins.theme.tests.css_inventory import (
    hard_coded_colours,
    is_used,
    rule_classes,
    template_class_usage,
    vue_style_text,
)
from plugins.theme_dataset.theme_dataset.plugin_paths import (
    STYLESHEETS_DIRECTORY,
    TEMPLATES_DIRECTORY,
)

FE_USER_ROOT = Path(__file__).resolve().parents[4].parent / "vbwd-fe-user"
DATASET_SOURCE = FE_USER_ROOT / "plugins" / "dataset" / "src"
SOURCE_STYLE_FILES = (
    DATASET_SOURCE / "views" / "DatasetCatalogue.vue",
    DATASET_SOURCE / "views" / "DatasetDetail.vue",
    DATASET_SOURCE / "components" / "DatasetCheckoutSummary.vue",
)

needs_spa_checkout = pytest.mark.skipif(
    not DATASET_SOURCE.is_dir(), reason="fe-user is not next to vbwd-backend"
)


def _ported_css():
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(STYLESHEETS_DIRECTORY.rglob("*.css"))
    )


def _used_styled_classes():
    static_classes, prefixes = template_class_usage(TEMPLATES_DIRECTORY.rglob("*.j2"))
    source_classes = set()
    for source in SOURCE_STYLE_FILES:
        source_classes |= rule_classes(
            vue_style_text(source.read_text(encoding="utf-8"))
        )
    return {
        class_name
        for class_name in source_classes
        if is_used(class_name, static_classes, prefixes)
    }


@needs_spa_checkout
def test_every_used_styled_class_has_a_ported_rule():
    assert _used_styled_classes() - rule_classes(_ported_css()) == set()


@needs_spa_checkout
def test_every_ported_class_is_used_and_styled_in_the_spa():
    assert rule_classes(_ported_css()) - _used_styled_classes() == set()


def test_the_ported_css_styles_the_catalogue():
    ported = rule_classes(_ported_css())

    for class_name in ("dataset-grid", "dataset-card", "dataset-detail-header"):
        assert class_name in ported


def test_the_ported_css_carries_no_hard_coded_colour():
    assert hard_coded_colours(_ported_css()) == []
