import csv
from pathlib import Path
from flask import current_app
from . import db
from .models import Politician
from .tasks import run_full_pipeline
from .scrape.aph_parliamentarians import fetch_parliamentarians, write_parliamentarians_csv


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create database tables."""
        db.create_all()
        print("Database initialized")

    @app.cli.command("seed-politicians")
    def seed_politicians():
        """Seed politicians from a CSV file."""
        csv_path = Path(current_app.config.get("POLITICIANS_CSV", "data/politicians.csv"))
        if not csv_path.exists():
            print(f"CSV not found: {csv_path}")
            return

        count = 0
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("name")
                if not name:
                    continue
                existing = Politician.query.filter_by(name=name).first()
                if existing:
                    continue
                politician = Politician(
                    name=name.strip(),
                    party=row.get("party", "").strip() or None,
                    electorate=row.get("electorate", "").strip() or None,
                    chamber=row.get("chamber", "").strip() or None,
                    aph_id=row.get("aph_id", "").strip() or None,
                )
                db.session.add(politician)
                count += 1
        db.session.commit()
        print(f"Seeded {count} politicians")

    @app.cli.command("fetch-politicians")
    def fetch_politicians():
        """Fetch the current APH parliamentarian list and write to CSV."""
        csv_path = Path(current_app.config.get("POLITICIANS_CSV", "data/politicians.csv"))
        rows = fetch_parliamentarians()
        if not rows:
            print("No parliamentarians fetched")
            return
        write_parliamentarians_csv(csv_path, rows)
        print(f"Wrote {len(rows)} rows to {csv_path}")

    @app.cli.command("run-scrape-once")
    def run_scrape_once():
        """Run the full scrape and analysis pipeline once."""
        run_full_pipeline()
        print("Pipeline finished")
