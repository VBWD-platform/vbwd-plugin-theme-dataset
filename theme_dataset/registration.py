"""What theme_dataset puts into the theme platform (owner fe-user ``dataset``).

fe-user mounts the three Data-store routes as ``CmsPage`` with fixed slugs
(``data-store``, ``dataset-detail``): each themed route renders that CMS page
through theme_cms's pipeline with the route params in context (S152-06 §7).
"""
from typing import Any, Callable, Dict, List

from plugins.theme.theme.fragment_registry import ThemeFragment
from plugins.theme.theme.page_registry import PUBLIC_PAGE, ThemePage
from plugins.theme.theme.theme_request import ThemeRequest
from plugins.theme_cms.theme_cms.pages import DISPATCH_TEMPLATE
from plugins.theme_cms.theme_cms.registries import ComponentTemplate

from .catalogue import DatasetCatalogue, DatasetDetail

DATASET_FE_USER_PLUGIN = "dataset"
DATASET_PAGE_PRIORITY = 50
CATALOGUE_CMS_SLUG = "data-store"
DETAIL_CMS_SLUG = "dataset-detail"
LIST_FRAGMENT_RULE = "/_render/_fragment/dataset/list"
PAGE_ROUTES = (
    ("/data-store", "dataset_store_index", CATALOGUE_CMS_SLUG),
    ("/data-store/<category_slug>", "dataset_store_list", CATALOGUE_CMS_SLUG),
    (
        "/data-store/<category_slug>/<dataset_slug>",
        "dataset_store_detail",
        DETAIL_CMS_SLUG,
    ),
)


def _cms_page_context(
    cms_pages: Any, cms_slug: str
) -> Callable[[ThemeRequest], Dict[str, Any]]:
    def build_context(theme_request: ThemeRequest) -> Dict[str, Any]:
        page_context: Dict[str, Any] = cms_pages.cms_slug_page_context(
            theme_request, cms_slug
        )
        return page_context

    return build_context


def dataset_pages(cms_pages: Any) -> List[ThemePage]:
    return [
        ThemePage(
            rule=rule,
            endpoint=endpoint,
            owner_fe_user_plugin=DATASET_FE_USER_PLUGIN,
            priority=DATASET_PAGE_PRIORITY,
            auth=PUBLIC_PAGE,
            template=DISPATCH_TEMPLATE,
            build_context=_cms_page_context(cms_pages, cms_slug),
        )
        for rule, endpoint, cms_slug in PAGE_ROUTES
    ]


def dataset_fragments(catalogue: DatasetCatalogue) -> List[ThemeFragment]:
    return [
        ThemeFragment(
            rule=LIST_FRAGMENT_RULE,
            endpoint="dataset_list_fragment",
            owner_fe_user_plugin=DATASET_FE_USER_PLUGIN,
            template="dataset/_list_fragment.html.j2",
            build_context=catalogue.list_fragment_context,
        )
    ]


def dataset_components(catalogue: DatasetCatalogue) -> List[ComponentTemplate]:
    """The twins of fe-user ``registerCmsVueComponent`` (same names)."""
    return [
        ComponentTemplate(
            "DatasetCatalogue",
            "dataset/components/dataset_catalogue.html.j2",
            catalogue.build_context,
        ),
        ComponentTemplate(
            "DatasetDetail",
            "dataset/components/dataset_detail.html.j2",
            DatasetDetail().build_context,
        ),
    ]
