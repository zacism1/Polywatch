import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT_DISCLOSURES = ROOT / "docs" / "data" / "disclosures.json"

HOUSE_URL = "https://www.aph.gov.au/Senators_and_Members/Members/Register"
SENATE_URL = "https://www.aph.gov.au/Parliamentary_Business/Committees/Senate/Senators_Interests/Tabled_volumes"

USER_AGENT = "PolywatchBot/1.0 (public data for transparency)"


def normalize_key(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z]", "", value)
    return value


def fetch_html(url: str, retries: int = 3, backoff: float = 1.5) -> str:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last_err = exc
            time.sleep(backoff * attempt)
    raise last_err


def parse_house_disclosures() -> dict:
    html = fetch_html(HOUSE_URL)
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select("a"):
        href = a.get("href")
        if not href or ".pdf" not in href.lower():
            continue
        if "register/48p" not in href.lower():
            continue
        full = urljoin(HOUSE_URL, href)
        links.append(full)

    results = {}
    for url in links:
        filename = url.split("/")[-1]
        base = filename.replace("_48P.pdf", "").replace("_48p.pdf", "")
        last = base.replace("_", " ").strip()
        key = normalize_key(last)
        results.setdefault(key, [])
        results[key].append({
            "label": last.title(),
            "url": url,
        })
    return results


def parse_senate_disclosures() -> list:
    html = fetch_html(SENATE_URL)
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for a in soup.select("a"):
        href = a.get("href")
        if not href or ".pdf" not in href.lower():
            continue
        full = urljoin(SENATE_URL, href)
        text = (a.get_text() or "").strip() or href.split("/")[-1]
        results.append({"label": text, "url": full})
    return results


def main():
    try:
        house = parse_house_disclosures()
    except requests.RequestException as exc:
        print(f"Failed to fetch House register page: {exc}")
        house = {}

    try:
        senate = parse_senate_disclosures()
    except requests.RequestException as exc:
        print(f"Failed to fetch Senate register page: {exc}")
        senate = []

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "house": house,
        "senate": senate,
    }

    if not house and not senate and OUT_DISCLOSURES.exists():
        print("No disclosures fetched; keeping existing disclosures.json")
        return

    OUT_DISCLOSURES.parent.mkdir(parents=True, exist_ok=True)
    with OUT_DISCLOSURES.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote disclosures for {len(house)} House surnames and {len(senate)} Senate PDFs")


if __name__ == "__main__":
    main()
