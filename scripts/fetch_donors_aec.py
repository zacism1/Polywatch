import csv
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_DONORS = ROOT / "docs" / "data" / "donors.json"

AEC_ZIP_URL = "https://transparency.aec.gov.au/Download/AllAnnualData"
USER_AGENT = "PolywatchBot/1.0 (public data for transparency)"

PARTY_RETURNS = "Party Returns.csv"
DONATIONS_MADE = "Donations Made.csv"


def parse_fin_year(value: str) -> int:
    match = re.match(r"(\d{4})", value or "")
    if not match:
        return 0
    return int(match.group(1))


def load_zip() -> zipfile.ZipFile:
    resp = requests.get(AEC_ZIP_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(resp.content))


def read_csv(z: zipfile.ZipFile, name: str):
    with z.open(name) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
        return list(reader)


def main():
    z = load_zip()
    party_rows = read_csv(z, PARTY_RETURNS)
    if not party_rows:
        raise SystemExit("No party data found")

    latest_year = max(party_rows, key=lambda r: parse_fin_year(r.get("Financial Year", ""))).get(
        "Financial Year", ""
    )

    parties = sorted(
        {
            row["Name"].strip()
            for row in party_rows
            if row.get("Name") and row.get("Financial Year") == latest_year
        }
    )
    party_set = set(parties)

    donation_rows = read_csv(z, DONATIONS_MADE)
    totals = {}
    yearly_totals = {}

    for row in donation_rows:
        fin_year = row.get("Financial Year") or ""
        recipient = (row.get("Donation Made To") or "").strip()
        donor = (row.get("Donor Name") or "").strip()
        if not recipient or not donor:
            continue
        if recipient not in party_set:
            continue
        value_raw = (row.get("Value") or "").replace(",", "").replace("$", "").strip()
        try:
            value = float(value_raw)
        except ValueError:
            continue

        if fin_year == latest_year:
            totals.setdefault(recipient, {})
            totals[recipient][donor] = totals[recipient].get(donor, 0) + value

        yearly_totals.setdefault(recipient, {})
        yearly_totals[recipient][fin_year] = yearly_totals[recipient].get(fin_year, 0) + value

    parties_out = []
    for party in parties:
        donors = totals.get(party, {})
        top = sorted(donors.items(), key=lambda item: item[1], reverse=True)[:10]
        yearly = yearly_totals.get(party, {})
        parties_out.append(
            {
                "party": party,
                "top_donors": [
                    {"name": name, "amount": round(amount, 2)} for name, amount in top
                ],
                "yearly_totals": [
                    {"year": year, "amount": round(amount, 2)}
                    for year, amount in sorted(yearly.items())
                ],
            }
        )

    OUT_DONORS.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "financial_year": latest_year,
        "source": "AEC Transparency Register (Annual Data Download)",
        "parties": parties_out,
    }
    with OUT_DONORS.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote donors for {len(parties_out)} parties")


if __name__ == "__main__":
    main()
