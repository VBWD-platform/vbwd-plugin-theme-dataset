"""Test doubles for the theme_dataset unit tests: a scripted ``DatasetApi``."""
from plugins.theme.theme.theme_api import ThemeApiError

DATASET = {
    "id": "ds-1",
    "slug": "air-quality",
    "title": "Air Quality",
    "description": "Hourly readings",
    "source_attribution": "EEA",
    "price": 7,
    "is_active": True,
}
CATEGORIES = {
    "categories": [
        {"id": "t-1", "slug": "environment", "label": "Environment"},
        {"id": "t-2", "slug": "finance", "label": "Finance"},
    ]
}


class FakeDatasetApi:
    """Same methods as ``DatasetApi``; answers by method name (exceptions are raised)."""

    def __init__(self, **answers):
        self.answers = {
            "categories": CATEGORIES,
            "datasets": {
                "items": [DATASET],
                "total": 1,
                "page": 1,
                "per_page": 12,
                "pages": 1,
            },
            "dataset": DATASET,
            "order": {
                "invoice_id": "inv-9",
                "invoice_number": "DS-1",
                "status": "PENDING",
                "total_amount": "7.00",
                "currency": "EUR",
            },
            **answers,
        }
        self.calls = []

    def factory(self, theme_request):
        self.theme_request = theme_request
        return self

    def _answer(self, name, *arguments):
        self.calls.append((name,) + arguments)
        answer = self.answers.get(name)
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            raise ThemeApiError(404, "Not found")
        return answer

    def categories(self):
        return self._answer("categories")

    def datasets(self, query):
        return self._answer("datasets", dict(query))

    def dataset(self, slug):
        return self._answer("dataset", slug)

    def create_order(self, payload):
        return self._answer("order", dict(payload))
