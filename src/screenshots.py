"""Takes a full-length screenshot of every dashboard page for the report.

Start the dashboard first (streamlit run src/dashboard/app.py), then:

    python src/screenshots.py                      uses http://localhost:8501
    python src/screenshots.py --url http://localhost:8502

Images are written to docs/task3/app_screenshots/ (the design mockups in docs/task3/screenshots/ are left alone).
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "task3" / "app_screenshots"
PAGES = [
    ("1_overview", ""), ("2_gc_classifications", "gc"), ("3_stages", "stages"), ("4_time_trials", "time_trials"),
    ("5_riders", "riders"), ("6_teams", "teams"), ("7_nations", "nations"), ("8_about", "about"),
]
WIDTH = 1440


def settle(page):
    """Waits until Streamlit has finished running the page and the charts have drawn."""
    page.wait_for_selector("[data-testid='stMainBlockContainer']")
    page.wait_for_timeout(1500)
    page.wait_for_function("!document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=60000)
    page.wait_for_timeout(1500)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8501")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": 1000}, device_scale_factor=2)
        for name, slug in PAGES:
            page.goto(f"{args.url}/{slug}")
            settle(page)
            # Streamlit scrolls inside its main pane, so the window is made as tall as the content
            height = page.evaluate("document.querySelector('[data-testid=\"stMainBlockContainer\"]').scrollHeight")
            page.set_viewport_size({"width": WIDTH, "height": int(height) + 40})
            settle(page)
            page.screenshot(path=OUT / f"{name}.png", full_page=True)
            print(f"Saved {name}.png ({WIDTH} x {int(height) + 40})")
        browser.close()


if __name__ == "__main__":
    main()
