import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "politicians.csv"
OUT_POLITICIANS = ROOT / "docs" / "data" / "politicians.json"
OUT_PROFILES = ROOT / "docs" / "data" / "profiles.json"
OUT_META = ROOT / "docs" / "data" / "meta.json"
DONORS_PATH = ROOT / "docs" / "data" / "donors.json"


def slugify(name: str) -> str:
    return (
        name.lower()
        .replace("'", "")
        .replace(".", "")
        .replace(",", "")
        .replace(" ", "-")
    )


def load_existing_profiles():
    if OUT_PROFILES.exists():
        with OUT_PROFILES.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_donor_parties():
    if not DONORS_PATH.exists():
        return set()
    with DONORS_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    parties = {p.get("party") for p in payload.get("parties", []) if p.get("party")}
    return parties


def main():
    if not CSV_PATH.exists():
        raise SystemExit(f"Missing {CSV_PATH}")

    politicians = []
    profiles = load_existing_profiles()
    donor_parties = load_donor_parties()

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
            profiles.setdefault(
                pol_id,
                {
                    "investments": [],
                    "policies": [],
                    "correlations": [],
                },
            )

    # Compute featured list based on correlation count
    scored = []
    for pol in politicians:
        corr_count = len(profiles.get(pol["id"], {}).get("correlations", []))
        party_bonus = 1 if pol.get("party") in donor_parties else 0
        score = corr_count + party_bonus
        scored.append((score, pol["id"]))
    scored.sort(reverse=True)
    featured_ids = {pol_id for score, pol_id in scored[:5] if score > 0}

    for pol in politicians:
        pol["featured"] = pol["id"] in featured_ids

    OUT_POLITICIANS.parent.mkdir(parents=True, exist_ok=True)
    OUT_PROFILES.parent.mkdir(parents=True, exist_ok=True)

    with OUT_POLITICIANS.open("w", encoding="utf-8") as f:
        json.dump(politicians, f, indent=2)

    with OUT_PROFILES.open("w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": len(politicians),
        "house": sum(1 for p in politicians if p.get("chamber") == "House"),
        "senate": sum(1 for p in politicians if p.get("chamber") == "Senate"),
    }

    with OUT_META.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"Wrote {len(politicians)} politicians")


if __name__ == "__main__":
    main()
