"""HTTP client for reports, editorial comparisons, and delivery sidecars."""

from __future__ import annotations

from urllib.parse import quote, urlsplit

import httpx
from pydantic import ValidationError

from app.catalog.comparison import Comparison
from app.catalog.schema import (
    BreakdownQuery,
    BreakdownResult,
    CatalogSchema,
    ExportQuery,
    QualityReport,
    TableQuery,
    TableResult,
)
from app.delivery.schema import DeliveryFormat, DeliveryPreview


class CatalogError(Exception):
    """An actionable error to display in the terminal."""


class CatalogClient:
    def __init__(
        self, base_url: str, key: str | None = None, *, timeout: float = 30, transport=None
    ):
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise CatalogError(
                "Set the API URL to an HTTP(S) base URL without credentials, query, or fragment."
            )
        headers = {"X-API-Key": key} if key else {}
        self.http = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            headers=headers,
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
        )

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.http.close()

    def request(self, method, path, **options):
        try:
            response = self.http.request(method, path, **options)
        except httpx.RequestError as exc:
            raise CatalogError(f"Could not reach the CineTag API ({type(exc).__name__}).") from exc
        if not response.is_success:
            detail = response.reason_phrase
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    message = payload.get("detail")
                    if isinstance(message, str):
                        detail = message
                    elif isinstance(message, list):
                        detail = ", ".join(
                            str(item.get("msg", "Validation error"))
                            for item in message
                            if isinstance(item, dict)
                        )
            except ValueError:
                pass
            raise CatalogError(f"API returned {response.status_code}: {detail}")
        return response

    def model(self, schema, method, path, **options):
        response = self.request(method, path, **options)
        try:
            return schema.model_validate_json(response.content)
        except ValidationError as exc:
            raise CatalogError(
                f"Unexpected response for {path}. Check that the API supports this command."
            ) from exc

    def schema(self) -> CatalogSchema:
        return self.model(CatalogSchema, "GET", "api/catalog/schema")

    def quality(self) -> QualityReport:
        return self.model(QualityReport, "GET", "api/catalog/quality")

    def table(self, dataset: str, query: TableQuery) -> TableResult:
        return self.model(
            TableResult,
            "POST",
            f"api/catalog/{quote(dataset, safe='')}/query",
            json=query.model_dump(mode="json"),
        )

    def groups(self, dataset: str, query: BreakdownQuery) -> BreakdownResult:
        return self.model(
            BreakdownResult,
            "POST",
            f"api/catalog/{quote(dataset, safe='')}/groups",
            json=query.model_dump(mode="json"),
        )

    def export(self, dataset: str, query: ExportQuery) -> bytes:
        return self.request(
            "POST",
            f"api/catalog/{quote(dataset, safe='')}/export",
            json=query.model_dump(mode="json"),
        ).content

    def compare(self, left: int, right: int) -> Comparison:
        return self.model(
            Comparison, "GET", "api/catalog/compare", params={"left": left, "right": right}
        )

    def preview(self, video: int) -> DeliveryPreview:
        return self.model(DeliveryPreview, "GET", f"api/videos/{video}/delivery")

    def file(self, video: int, fmt: DeliveryFormat) -> bytes:
        return self.request("GET", f"api/videos/{video}/delivery/files/{fmt.value}").content
