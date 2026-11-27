"""Run browser-level catalog regressions against a disposable local database.

Build the frontend with NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8028, install
the backend and Python Playwright, then run this script from any directory.
Use CATALOG_CHROMIUM to select an installed Chromium executable.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from zipfile import ZipFile

from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
WEB = "http://127.0.0.1:3028"
API = "http://127.0.0.1:8028"


def seed():
    from app.db.models import GeneratedTag, SceneSegment, Transcript, VideoAsset
    from app.db.session import Base, SessionLocal, get_engine

    Base.metadata.create_all(get_engine())
    with SessionLocal.begin() as session:
        session.add_all(
            [
                VideoAsset(
                    id=71,
                    title="Estuary",
                    status="published",
                    original_filename="coast.mp4",
                    storage_key="coast.mp4",
                    summary="The tide rises.",
                    duration_seconds=12,
                ),
                VideoAsset(
                    id=72,
                    title="Mountain",
                    status="review_ready",
                    original_filename="peak.mp4",
                    storage_key="peak.mp4",
                    duration_seconds=24,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                GeneratedTag(
                    video_id=71,
                    tag_type="genre",
                    tag_value="Nature",
                    status="approved",
                    source="manual",
                ),
                Transcript(video_id=71, text="The tide rises.", language="en"),
                SceneSegment(
                    video_id=71,
                    start_time_seconds=0,
                    end_time_seconds=12,
                    summary="High tide",
                ),
            ]
        )


@contextmanager
def server(command, cwd, url, log):
    with log.open("wb") as output:
        proc = subprocess.Popen(command, cwd=cwd, stdout=output, stderr=output)
        try:
            for _ in range(120):
                if proc.poll() is not None:
                    raise RuntimeError(log.read_text())
                try:
                    with urlopen(url, timeout=2) as response:
                        if response.status == 200:
                            break
                except (TimeoutError, URLError):
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError(f"Server startup timed out: {log.read_text()}")
            yield
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def check_catalog(page: Page):
    page.goto(WEB + "/catalog")
    expect(page.get_by_text("2 matching records", exact=True)).to_be_visible()
    page.get_by_role("searchbox", name="Search videos").fill("Estuary")
    page.get_by_role("button", name="Search", exact=True).click()
    expect(page.get_by_text("1 matching records", exact=True)).to_be_visible()
    page.get_by_text("Saved views (0)", exact=True).click()
    page.get_by_label("Name this view").fill("Coastal films")
    page.get_by_role("button", name="Save on this device").click()
    page.reload()
    page.get_by_text("Saved views (1)", exact=True).click()
    page.get_by_role("button", name="Coastal films · Videos").click()
    expect(page.get_by_text("1 matching records", exact=True)).to_be_visible()
    page.get_by_label("Export format").select_option("json")
    with page.expect_download() as event:
        page.get_by_role("button", name="Export matching records").click()
    records = json.loads(event.value.path().read_bytes())
    assert [record["title"] for record in records] == ["Estuary"]
    page.get_by_role("button", name="Remove search").click()
    page.get_by_role("button", name="Breakdown", exact=True).click()
    page.get_by_text("Measurement statistics", exact=True).click()
    expect(page.get_by_text("2 measured · 0 missing")).to_be_visible()
    page.get_by_role("button", name="published", exact=True).click()
    expect(page.get_by_role("cell", name="Estuary", exact=True)).to_be_visible()


def check_quality(page: Page):
    page.get_by_role("button", name="Quality checks").click()
    page.get_by_text("Quality snapshots", exact=True).click()
    with page.expect_download() as event:
        page.get_by_role("button", name="Download current snapshot").click()
    baseline = json.loads(event.value.path().read_bytes())
    missing = next(
        c
        for c in baseline["checks"]
        if c["dataset"] == "videos" and c["preset"] == "missing_summary"
    )
    assert missing["count"] == 1
    missing["count"] = 0
    section = page.locator("details").filter(
        has=page.get_by_text("Quality snapshots", exact=True)
    )
    section.get_by_label("Compare with a saved snapshot").set_input_files(
        {
            "name": "baseline.json",
            "mimeType": "application/json",
            "buffer": json.dumps(baseline).encode(),
        }
    )
    expect(section.get_by_role("cell", name="+1", exact=True)).to_be_visible()
    section.get_by_role("button", name="Missing summary", exact=True).click()
    expect(page.get_by_role("cell", name="Mountain", exact=True)).to_be_visible()


def check_compare(page: Page):
    page.get_by_role("link", name="Compare videos", exact=True).click()
    page.get_by_role("button", name="Select first video").click()
    page.get_by_role("button", name="Estuary · #71").click()
    page.get_by_role("button", name="Select second video").click()
    page.get_by_role("button", name="Mountain · #72").click()
    expect(page.get_by_role("heading", name="Media and analysis")).to_be_visible()
    assert "left=71&right=72" in page.url
    page.get_by_role("button", name="Swap videos").click()
    expect(page.get_by_role("heading", name="Only in Estuary (1)")).to_be_visible()
    page.reload()
    expect(page.get_by_role("heading", name="Media and analysis")).to_be_visible()
    assert "left=72&right=71" in page.url


def check_editorial(page: Page):
    page.goto(WEB + "/videos/71")
    page.get_by_text("Review notes", exact=True).click()
    page.get_by_role("button", name="Add note").click()
    page.get_by_label("Note", exact=True).fill("Check the cut after the opening shot.")
    page.get_by_label("Time in video (optional)").fill("0:03.250")
    page.get_by_role("button", name="Save note", exact=True).click()
    expect(page.get_by_text("0:03.25", exact=True)).to_be_visible()
    page.get_by_role("button", name="Resolve note").click()
    page.get_by_role("button", name=re.compile(r"^resolved \(1\)$", re.I)).click()
    page.get_by_text("Revision history", exact=True).click()
    expect(page.get_by_text("Marked resolved", exact=True)).to_be_visible()
    expect(page.get_by_text("Note created", exact=True)).to_be_visible()
    page.get_by_text("Export video metadata", exact=True).click()
    with page.expect_download() as event:
        page.get_by_role("button", name="Download delivery ZIP").click()
    with ZipFile(event.value.path()) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["media"]["video_id"] == 71
        assert manifest["chapters"][0]["title"] == "High tide"
        assert archive.read("transcript.txt").decode() == "The tide rises."


def main():
    sys.path.insert(0, str(ROOT / "backend"))
    with (
        tempfile.TemporaryDirectory(prefix="cinetag-browser-") as temp,
        ExitStack() as stack,
    ):
        work = Path(temp)
        os.environ.update(
            {
                "DATABASE_URL": f"sqlite:///{work / 'test.db'}",
                "APP_ENV": "local",
                "AUTH_ENABLED": "false",
                "STORAGE_BACKEND": "local",
                "LOCAL_STORAGE_DIR": str(work / "store"),
                "CORS_ALLOWED_ORIGINS": WEB,
                "NEXT_PUBLIC_API_BASE_URL": API,
            }
        )
        seed()
        stack.enter_context(
            server(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8028",
                ],
                ROOT / "backend",
                API + "/health",
                work / "api.log",
            )
        )
        stack.enter_context(
            server(
                [
                    "node",
                    "node_modules/next/dist/bin/next",
                    "start",
                    "-H",
                    "127.0.0.1",
                    "-p",
                    "3028",
                ],
                ROOT / "frontend",
                WEB + "/catalog",
                work / "frontend.log",
            )
        )
        driver = stack.enter_context(sync_playwright())
        browser = driver.chromium.launch(
            executable_path=os.environ.get("CATALOG_CHROMIUM")
        )
        stack.callback(browser.close)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        for check in (check_catalog, check_quality, check_compare, check_editorial):
            check(page)
            print(f"Passed {check.__name__}", flush=True)


if __name__ == "__main__":
    main()
