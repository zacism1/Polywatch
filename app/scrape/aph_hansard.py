import logging
from typing import List
from bs4 import BeautifulSoup
from flask import current_app
from .. import db
from ..models import Politician, Policy
from .utils import fetch_url, hash_text, parse_date


logger = logging.getLogger("politracker")


def scrape_hansard_updates() -> List[Policy]:
    user_agent = current_app.config["USER_AGENT"]
    timeout = current_app.config["REQUEST_TIMEOUT_SECS"]
    retries = current_app.config["REQUEST_RETRIES"]
    delay = current_app.config["REQUEST_DELAY_SECS"]

    base = current_app.config["APH_HANSARD_BASE"]
    html = fetch_url(base, user_agent, timeout, retries, delay)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("a")
    created = []

    for link in items[:50]:
        href = link.get("href")
        text = (link.get_text() or "").strip()
        if not href or "hansard" not in href.lower():
            continue

        policy = _parse_policy_stub(text, href)
        if not policy:
            continue

        created.append(policy)

    db.session.commit()
    return created


def _parse_policy_stub(title: str, url: str) -> Policy:
    politician = Politician.query.first()
    if not politician:
        return None

    source_hash = hash_text(f"{title}|{url}")
    existing = Policy.query.filter_by(source_hash=source_hash).first()
    if existing:
        return None

    policy = Policy(
        politician_id=politician.id,
        bill_name=title[:300],
        vote=None,
        date=parse_date(""),
        category=_infer_category(title),
        source_url=url,
        source_hash=source_hash,
        raw_text=title,
    )
    db.session.add(policy)
    return policy


def _infer_category(text: str) -> str:
    lower = text.lower()
    if "mining" in lower or "coal" in lower:
        return "mining"
    if "energy" in lower or "renewable" in lower:
        return "energy"
    if "bank" in lower or "finance" in lower:
        return "banking"
    if "housing" in lower or "property" in lower:
        return "property"
    return "other"
