import csv
import logging
from pathlib import Path
from typing import List, Dict
from bs4 import BeautifulSoup
from flask import current_app
from .utils import fetch_url


logger = logging.getLogger("politracker")

FETCH_URL_TEMPLATE = (
    "https://www.aph.gov.au/Senators_and_Members/Parliamentarian_Search_Results"
    "?gen=0&mem=1&page={page}&par=-1&ps=96&q=&sen=1&st=1"
)


def fetch_parliamentarians() -> List[Dict[str, str]]:
    user_agent = current_app.config["USER_AGENT"]
    timeout = current_app.config["REQUEST_TIMEOUT_SECS"]
    retries = current_app.config["REQUEST_RETRIES"]
    delay = current_app.config["REQUEST_DELAY_SECS"]

    results = []
    for page in (1, 2, 3):
        url = FETCH_URL_TEMPLATE.format(page=page)
        html = fetch_url(url, user_agent, timeout, retries, delay)
        if not html:
            continue

        page_results = _parse_search_results(html)
        results.extend(page_results)

    return _dedupe_results(results)


def write_parliamentarians_csv(path: Path, rows: List[Dict[str, str]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "party", "electorate", "chamber", "aph_id"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _parse_search_results(html: bytes) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    results = []
    for idx in range(len(lines) - 1):
        if lines[idx + 1].lower() != "for":
            continue

        name = lines[idx]
        if "search" in name.lower() or "results" in name.lower():
            continue

        if idx + 2 >= len(lines):
            continue

        electorate = lines[idx + 2]
        party = None
        for j in range(idx + 3, min(idx + 10, len(lines))):
            if lines[j].lower() == "party" and j + 1 < len(lines):
                party = lines[j + 1]
                break

        chamber = "Senate" if "senator" in name.lower() else "House"
        results.append(
            {
                "name": name.strip(),
                "party": party or "",
                "electorate": electorate.strip(),
                "chamber": chamber,
                "aph_id": "",
            }
        )
    return results


def _dedupe_results(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    deduped = []
    for row in rows:
        key = (row["name"], row["electorate"], row["chamber"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped
