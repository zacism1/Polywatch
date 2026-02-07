import hashlib
import logging
import re
import time
import urllib.robotparser
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import requests


logger = logging.getLogger("politracker")


def can_fetch(url: str, user_agent: str) -> bool:
    try:
        rp = urllib.robotparser.RobotFileParser()
        robots_url = _robots_url(url)
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        logger.warning("robots.txt fetch failed for %s; proceeding cautiously", url)
        return True


def fetch_url(url: str, user_agent: str, timeout: int, retries: int, delay: float) -> Optional[bytes]:
    if not can_fetch(url, user_agent):
        logger.warning("Blocked by robots.txt: %s", url)
        return None

    headers = {"User-Agent": user_agent}
    for attempt in range(1, retries + 1):
        try:
            time.sleep(delay)
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            logger.warning("Fetch failed (%s/%s) %s: %s", attempt, retries, url, exc)
            if attempt == retries:
                return None
    return None


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_date(date_str: str):
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def keyword_category_match(category: Optional[str], asset_type: Optional[str], company: Optional[str]) -> bool:
    if not category:
        return False
    category = category.lower()
    asset_text = " ".join([asset_type or "", company or ""]).lower()
    keywords = {
        "mining": ["mining", "coal", "iron", "ore", "gas"],
        "energy": ["energy", "oil", "gas", "renewable", "solar"],
        "banking": ["bank", "financial", "insurance"],
        "property": ["property", "real estate", "housing"],
    }

    for key, words in keywords.items():
        if key in category and any(word in asset_text for word in words):
            return True
    return False


def _robots_url(url: str) -> str:
    parts = url.split("/")
    if len(parts) < 3:
        return url
    return f"{parts[0]}//{parts[2]}/robots.txt"


def normalize_name(value: str) -> str:
    if not value:
        return ""
    value = value.lower()
    value = re.sub(r"[^a-z\\s'-]", " ", value)
    value = re.sub(r"\\b(mr|ms|mrs|dr|hon|senator|member)\\b", " ", value)
    value = re.sub(r"\\s+", " ", value).strip()
    return value


def build_name_index(names: List[str]) -> Dict[str, str]:
    index = {}
    for name in names:
        normalized = normalize_name(name)
        if normalized:
            index[normalized] = name
    return index


def build_last_name_index(names: List[str]) -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = {}
    for name in names:
        normalized = normalize_name(name)
        if not normalized:
            continue
        parts = normalized.split()
        if not parts:
            continue
        last = parts[-1]
        index.setdefault(last, []).append(name)
    return index


def build_full_name_index(names: List[str]) -> Dict[str, str]:
    index = {}
    for name in names:
        normalized = normalize_name(name)
        if normalized:
            index[normalized] = name
    return index


def detect_name_in_line(line: str, full_name_index: Dict[str, str]) -> Optional[str]:
    if not line:
        return None
    normalized_line = normalize_name(line)
    if not normalized_line:
        return None
    # Prefer longest match to reduce false positives
    candidates: List[Tuple[int, str]] = []
    for normalized, original in full_name_index.items():
        if normalized and normalized in normalized_line:
            candidates.append((len(normalized), original))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def match_speaker_line(line: str, last_name_index: Dict[str, List[str]]) -> Optional[str]:
    if not line:
        return None
    match = re.match(r"^(Senator|Mr|Ms|Mrs|Dr|Hon)\\s+([A-Z][A-Za-z'\\-]+)", line)
    if not match:
        return None
    last = match.group(2).lower()
    candidates = last_name_index.get(last, [])
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    # If multiple, try to match first initial from line
    initial_match = re.match(r"^(Senator|Mr|Ms|Mrs|Dr|Hon)\\s+([A-Z])[A-Za-z'\\-]+\\s+([A-Z][A-Za-z'\\-]+)", line)
    if initial_match:
        first_initial = initial_match.group(2).lower()
        for name in candidates:
            parts = normalize_name(name).split()
            if parts and parts[0].startswith(first_initial):
                return name
    return None
