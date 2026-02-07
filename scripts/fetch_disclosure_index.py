import json
import re
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


def normalize_name(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z\s'-]", " ", value)
    value = re.sub(r"\b(mr|ms|mrs|dr|hon|senator|member)\b", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def slugify(name: str) -> str:
    return (
        name.lower()
        .replace("'", "")
        .replace(".", "")
        .replace(",", "")
        .replace(" ", "-")
    )


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


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
        text = (a.get_text() or "").strip()
        links.append((text, full))

    results = {}
    for text, url in links:
        filename = url.split("/")[-1]
        # e.g., Abdo_48P.pdf -> Abdo
        base = filename.replace("_48P.pdf", "").replace("_48p.pdf", "")
        last = base.replace("_", " ").strip()
        results[last.lower()] = {
            "label": last.title(),
            "url": url,
        }
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
    house = parse_house_disclosures()
    senate = parse_senate_disclosures()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "house": house,
        "senate": senate,
    }

    OUT_DISCLOSURES.parent.mkdir(parents=True, exist_ok=True)
    with OUT_DISCLOSURES.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote disclosures for {len(house)} House members and {len(senate)} Senate PDFs")


if __name__ == "__main__":
    main()
