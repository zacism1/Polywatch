import logging
import re
from typing import List, Optional
from datetime import date
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from flask import current_app
from .. import db
from ..models import Politician, Policy
from .utils import fetch_url, hash_text, parse_date, normalize_name, build_last_name_index, build_full_name_index, detect_name_in_line, match_speaker_line


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

    politicians = Politician.query.all()
    last_name_index = build_last_name_index([p.name for p in politicians])
    full_name_index = build_full_name_index([p.name for p in politicians])

    for link in items[:60]:
        href = link.get("href")
        text = (link.get_text() or "").strip()
        if not href or "hansard" not in href.lower():
            continue

        full_url = urljoin(base, href)
        page_html = fetch_url(full_url, user_agent, timeout, retries, delay)
        if not page_html:
            continue

        for policy in _parse_policy_page(text, full_url, page_html, last_name_index, full_name_index):
            if policy:
                created.append(policy)

    db.session.commit()
    return created


def _parse_policy_page(title: str, url: str, html: bytes, last_name_index, full_name_index) -> List[Policy]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    date = _extract_date(lines)
    detected = _detect_speakers(lines, last_name_index, full_name_index)
    policies = []

    for pol in detected:
        source_hash = hash_text(f"{pol.id}|{title}|{url}")
        existing = Policy.query.filter_by(source_hash=source_hash).first()
        if existing:
            continue

        policy = Policy(
            politician_id=pol.id,
            bill_name=title[:300],
            vote=None,
            date=date,
            category=_infer_category(title),
            source_url=url,
            source_hash=source_hash,
            raw_text=title,
        )
        db.session.add(policy)
        policies.append(policy)

    return policies


def _detect_speakers(lines, last_name_index, full_name_index) -> List[Politician]:
    matches = []
    seen = set()
    for line in lines:
        name = match_speaker_line(line, last_name_index)
        if not name:
            name = detect_name_in_line(line, full_name_index)
        if not name:
            continue
        politician = Politician.query.filter_by(name=name).first()
        if politician and politician.id not in seen:
            matches.append(politician)
            seen.add(politician.id)
        if len(matches) >= 5:
            break
    return matches


def _extract_date(lines) -> Optional[date]:
    for line in lines[:20]:
        parsed = parse_date(line)
        if parsed:
            return parsed
    return None


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
