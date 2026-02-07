import io
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin
from flask import current_app
from PyPDF2 import PdfReader
from .. import db
from ..models import Politician, Investment
from .utils import fetch_url, hash_text, build_name_index, normalize_name, build_full_name_index, detect_name_in_line
from bs4 import BeautifulSoup


logger = logging.getLogger("politracker")


def scrape_register_disclosures() -> List[Investment]:
    user_agent = current_app.config["USER_AGENT"]
    timeout = current_app.config["REQUEST_TIMEOUT_SECS"]
    retries = current_app.config["REQUEST_RETRIES"]
    delay = current_app.config["REQUEST_DELAY_SECS"]

    created = []
    names = [p.name for p in Politician.query.all()]
    name_index = build_name_index(names)
    full_name_index = build_full_name_index(names)
    for chamber, url in current_app.config["APH_REGISTER_URLS"].items():
        pdf_urls = _resolve_register_pdfs(url, user_agent, timeout, retries, delay)
        for pdf_url in pdf_urls:
            pdf_bytes = fetch_url(pdf_url, user_agent, timeout, retries, delay)
            if not pdf_bytes:
                continue

            try:
                text = _pdf_to_text(pdf_bytes)
            except Exception as exc:
                logger.warning("PDF parse failed %s: %s", pdf_url, exc)
                continue

            for inv in _extract_investments(text, pdf_url, name_index, full_name_index):
                created.append(inv)

    db.session.commit()
    return created


def _pdf_to_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_investments(text: str, source_url: str, name_index, full_name_index) -> List[Investment]:
    results = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    current_name = None
    family_name = None
    given_names = None
    current_section = None
    for line in lines:
        family = _extract_family_name(line)
        if family:
            family_name = family

        given = _extract_given_names(line)
        if given:
            given_names = given

        if family_name and given_names and not current_name:
            combined = f"{given_names} {family_name}"
            normalized = normalize_name(combined)
            current_name = name_index.get(normalized, combined)

        if line.lower().startswith("member:") or line.lower().startswith("senator:"):
            raw_name = line.split(":", 1)[-1].strip()
            normalized = normalize_name(raw_name)
            current_name = name_index.get(normalized, raw_name)
            continue

        if not current_name:
            detected = detect_name_in_line(line, full_name_index)
            if detected:
                current_name = detected
                continue

        if not current_name:
            parsed_name = _parse_comma_name(line, name_index)
            if parsed_name:
                current_name = parsed_name
                continue

        if not current_name:
            continue

        section_match = re.match(r"^\\d+\\.\\s+(.*)$", line)
        if section_match:
            current_section = section_match.group(1).strip().lower()
            continue

        if current_section and _is_data_line(line):
            politician = Politician.query.filter_by(name=current_name).first()
            if not politician:
                continue

            source_hash = hash_text(f"{current_name}|{line}")
            existing = Investment.query.filter_by(source_hash=source_hash).first()
            if existing:
                continue

            investment = Investment(
                politician_id=politician.id,
                asset_type=_infer_asset_type_from_section(current_section, line),
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


def _looks_like_investment(line: str) -> bool:
    keywords = ("share", "stock", "equity", "property", "real estate", "holding", "investment", "asset")
    text = line.lower()
    return any(keyword in text for keyword in keywords)


def _infer_asset_type(line: str) -> str:
    text = line.lower()
    if "property" in text or "real estate" in text:
        return "property"
    if "share" in text or "stock" in text or "equity" in text:
        return "equity"
    if "trust" in text:
        return "trust"
    return "declared asset"


def _infer_asset_type_from_section(section: str, line: str) -> str:
    text = f"{section} {line}".lower()
    if "real estate" in text or "property" in text:
        return "property"
    if "share" in text or "company" in text or "equity" in text:
        return "equity"
    if "trust" in text:
        return "trust"
    if "bond" in text or "debenture" in text:
        return "fixed income"
    if "liability" in text or "debt" in text:
        return "liability"
    return _infer_asset_type(line)


def _is_data_line(line: str) -> bool:
    text = line.strip()
    if not text or len(text) < 3:
        return False
    lowered = text.lower()
    if lowered in {"nil", "none", "not applicable", "n/a"}:
        return False
    if any(
        lowered.startswith(prefix)
        for prefix in (
            "name of",
            "nature of",
            "type of",
            "member for",
            "register of",
            "statement of",
            "family name",
            "given names",
            "electoral division",
            "state",
            "notes",
        )
    ):
        return False
    if lowered.startswith("part ") or lowered.startswith("section "):
        return False
    return True


def _extract_family_name(line: str) -> Optional[str]:
    match = re.match(r"^FAMILY NAME\\s+(.+)$", line, re.IGNORECASE)
    if match:
        return match.group(1).strip().title()
    return None


def _extract_given_names(line: str) -> Optional[str]:
    match = re.match(r"^GIVEN NAMES\\s+(.+)$", line, re.IGNORECASE)
    if match:
        return match.group(1).strip().title()
    return None


def _resolve_register_pdfs(url: str, user_agent: str, timeout: int, retries: int, delay: float) -> List[str]:
    if url.lower().endswith(".pdf"):
        return [url]

    html = fetch_url(url, user_agent, timeout, retries, delay)
    if not html:
        return [url]

    soup = BeautifulSoup(html, "html.parser")
    pdf_links = []
    for link in soup.select("a"):
        href = link.get("href")
        if not href:
            continue
        if ".pdf" in href.lower():
            pdf_links.append(urljoin(url, href))

    return pdf_links or [url]


def _parse_comma_name(line: str, name_index):
    if "," not in line:
        return None
    parts = [p.strip() for p in line.split(",", 1)]
    if len(parts) < 2:
        return None
    last = parts[0]
    first = parts[1].split()[0]
    candidate = f"{first} {last}"
    normalized = normalize_name(candidate)
    return name_index.get(normalized)
