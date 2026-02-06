import io
import logging
from typing import List
from flask import current_app
from PyPDF2 import PdfReader
from .. import db
from ..models import Politician, Investment
from .utils import fetch_url, hash_text


logger = logging.getLogger("politracker")


def scrape_register_disclosures() -> List[Investment]:
    user_agent = current_app.config["USER_AGENT"]
    timeout = current_app.config["REQUEST_TIMEOUT_SECS"]
    retries = current_app.config["REQUEST_RETRIES"]
    delay = current_app.config["REQUEST_DELAY_SECS"]

    created = []
    for chamber, url in current_app.config["APH_REGISTER_URLS"].items():
        pdf_bytes = fetch_url(url, user_agent, timeout, retries, delay)
        if not pdf_bytes:
            continue

        try:
            text = _pdf_to_text(pdf_bytes)
        except Exception as exc:
            logger.warning("PDF parse failed %s: %s", url, exc)
            continue

        for inv in _extract_investments(text, url):
            created.append(inv)

    db.session.commit()
    return created


def _pdf_to_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_investments(text: str, source_url: str) -> List[Investment]:
    results = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    current_name = None
    for line in lines:
        if line.lower().startswith("member:") or line.lower().startswith("senator:"):
            current_name = line.split(":", 1)[-1].strip()
            continue

        if not current_name:
            continue

        if any(keyword in line.lower() for keyword in ("share", "stock", "equity", "property", "real estate")):
            politician = Politician.query.filter_by(name=current_name).first()
            if not politician:
                continue

            source_hash = hash_text(f"{current_name}|{line}")
            existing = Investment.query.filter_by(source_hash=source_hash).first()
            if existing:
                continue

            investment = Investment(
                politician_id=politician.id,
                asset_type="declared asset",
                company=line[:200],
                value=None,
                date=None,
                source_url=source_url,
                source_hash=source_hash,
                raw_text=line,
            )
            db.session.add(investment)
            results.append(investment)
    return results
