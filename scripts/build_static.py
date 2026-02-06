import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "politicians.csv"
OUT_POLITICIANS = ROOT / "docs" / "data" / "politicians.json"
OUT_PROFILES = ROOT / "docs" / "data" / "profiles.json"


def slugify(name: str) -> str:
    return (
        name.lower()
        .replace("'", "")
        .replace(".", "")
        .replace(",", "")
        .replace(" ", "-")
    )


def main():
    if not CSV_PATH.exists():
        raise SystemExit(f"Missing {CSV_PATH}")

    politicians = []
    profiles = {}

    with CSV_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            pol_id = slugify(name)
            politician = {
                "id": pol_id,
                "name": name,
                "party": (row.get("party") or "").strip(),
                "electorate": (row.get("electorate") or "").strip(),
                "chamber": (row.get("chamber") or "").strip() or "House",
                "featured": False,
            }
            politicians.append(politician)
            profiles[pol_id] = {
                "investments": [],
                "policies": [],
                "correlations": [],
            }

    OUT_POLITICIANS.parent.mkdir(parents=True, exist_ok=True)
    OUT_PROFILES.parent.mkdir(parents=True, exist_ok=True)

    with OUT_POLITICIANS.open("w", encoding="utf-8") as f:
        json.dump(politicians, f, indent=2)

    with OUT_PROFILES.open("w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)

    print(f"Wrote {len(politicians)} politicians")


if __name__ == "__main__":
    main()
