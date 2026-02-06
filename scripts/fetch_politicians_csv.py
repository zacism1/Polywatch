import csv
import time
from pathlib import Path
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "data" / "politicians.csv"

USER_AGENT = "PolywatchBot/1.0 (public data for transparency)"
REQUEST_TIMEOUT = 20
REQUEST_DELAY = 1.5
PAGES = (1, 2, 3)

FETCH_URL_TEMPLATE = (
    "https://www.aph.gov.au/Senators_and_Members/Parliamentarian_Search_Results"
    "?gen=0&mem=1&page={page}&par=-1&ps=96&q=&sen=1&st=1"
)


def fetch_html(url: str) -> str:
    time.sleep(REQUEST_DELAY)
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def parse_search_results(html: str) -> List[Dict[str, str]]:
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
        party = ""
        for j in range(idx + 3, min(idx + 10, len(lines))):
            if lines[j].lower() == "party" and j + 1 < len(lines):
                party = lines[j + 1]
                break

        chamber = "Senate" if "senator" in name.lower() else "House"
        results.append(
            {
                "name": name.strip(),
                "party": party.strip(),
                "electorate": electorate.strip(),
                "chamber": chamber,
                "aph_id": "",
            }
        )
    return results


def dedupe(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    out = []
    for row in rows:
        key = (row["name"], row["electorate"], row["chamber"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def write_csv(path: Path, rows: List[Dict[str, str]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "party", "electorate", "chamber", "aph_id"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    all_rows = []
    for page in PAGES:
        url = FETCH_URL_TEMPLATE.format(page=page)
        html = fetch_html(url)
        all_rows.extend(parse_search_results(html))

    rows = dedupe(all_rows)
    write_csv(OUT_CSV, rows)
    print(f"Wrote {len(rows)} rows to {OUT_CSV}")


if __name__ == "__main__":
    main()
