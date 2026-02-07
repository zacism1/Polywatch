import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "instance" / "politracker.db"
OUT_PROFILES = ROOT / "docs" / "data" / "profiles.json"


def slugify(name: str) -> str:
    return (
        name.lower()
        .replace("'", "")
        .replace(".", "")
        .replace(",", "")
        .replace(" ", "-")
    )


def format_date(value):
    if not value:
        return ""
    if isinstance(value, str):
        return value
    try:
        return value.strftime("%Y-%m-%d")
    except Exception:
        return str(value)


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Missing database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    politicians = conn.execute("SELECT id, name FROM politicians").fetchall()
    pol_map = {row["id"]: row["name"] for row in politicians}

    profiles = {}
    for row in politicians:
        pol_id = slugify(row["name"])
        profiles[pol_id] = {"investments": [], "policies": [], "correlations": []}

    investments = conn.execute(
        "SELECT politician_id, asset_type, company, date, source_url FROM investments"
    ).fetchall()
    for row in investments:
        name = pol_map.get(row["politician_id"])
        if not name:
            continue
        pol_id = slugify(name)
        profiles[pol_id]["investments"].append(
            {
                "asset": row["company"] or row["asset_type"] or "",
                "date": format_date(row["date"]),
                "source": row["source_url"] or "",
            }
        )

    policies = conn.execute(
        "SELECT politician_id, bill_name, date, source_url FROM policies"
    ).fetchall()
    for row in policies:
        name = pol_map.get(row["politician_id"])
        if not name:
            continue
        pol_id = slugify(name)
        profiles[pol_id]["policies"].append(
            {
                "title": row["bill_name"] or "",
                "date": format_date(row["date"]),
                "source": row["source_url"] or "",
            }
        )

    correlations = conn.execute(
        """
        SELECT c.politician_id, c.details, i.company, i.asset_type, p.bill_name
        FROM correlations c
        JOIN investments i ON c.investment_id = i.id
        JOIN policies p ON c.policy_id = p.id
        """
    ).fetchall()

    for row in correlations:
        name = pol_map.get(row["politician_id"])
        if not name:
            continue
        pol_id = slugify(name)
        profiles[pol_id]["correlations"].append(
            {
                "policy": row["bill_name"] or "",
                "asset": row["company"] or row["asset_type"] or "",
                "details": row["details"] or "",
            }
        )

    OUT_PROFILES.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PROFILES.open("w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)

    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    print(f"Wrote profiles for {len(profiles)} politicians at {timestamp}")


if __name__ == "__main__":
    main()
