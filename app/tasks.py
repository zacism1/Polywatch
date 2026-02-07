import logging
import os
from datetime import datetime, timedelta
from flask import current_app
from . import db
from .models import Investment, Policy, Correlation, Politician
from .scrape.aph_register import scrape_register_disclosures
from .scrape.aph_hansard import scrape_hansard_updates
from .scrape.market_data import get_price_change
from .scrape.utils import keyword_category_match


logger = logging.getLogger("politracker")


def scheduled_weekly_job():
    with current_app.app_context():
        run_full_pipeline()


def run_full_pipeline():
    _setup_logging()
    logger.info("Starting pipeline")

    new_investments = scrape_register_disclosures()
    new_policies = scrape_hansard_updates()

    logger.info("Scraped %s investments", len(new_investments))
    logger.info("Scraped %s policies", len(new_policies))

    run_correlations()

    logger.info("Pipeline complete")


def run_correlations():
    threshold = current_app.config.get("PRICE_GAIN_THRESHOLD", 0.15)
    window_days = current_app.config.get("CORRELATION_WINDOW_DAYS", 30)

    for politician in Politician.query.all():
        investments = Investment.query.filter_by(politician_id=politician.id).all()
        policies = Policy.query.filter_by(politician_id=politician.id).all()

        for inv in investments:
            for pol in policies:
                if not inv.date or not pol.date:
                    continue

                if abs((pol.date - inv.date).days) > window_days:
                    continue

                if not keyword_category_match(pol.category, inv.asset_type, inv.company):
                    continue

                price_change = get_price_change(inv.company, pol.date, pol.date + timedelta(days=window_days))
                if price_change is None:
                    continue

                if price_change >= threshold:
                    correlation = Correlation(
                        politician_id=politician.id,
                        investment_id=inv.id,
                        policy_id=pol.id,
                        suspicion_score=float(price_change),
                        details=(
                            f"Price gain {price_change:.2%} within {window_days} days of policy vote"
                        ),
                    )
                    db.session.add(correlation)
    db.session.commit()


def _setup_logging():
    if logger.handlers:
        return

    logger.setLevel(logging.INFO)
    log_dir = os.path.abspath("logs")
    os.makedirs(log_dir, exist_ok=True)
    handler = logging.FileHandler(os.path.join(log_dir, "scrape.log"))
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
