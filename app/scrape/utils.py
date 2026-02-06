import hashlib
import time
import logging
import urllib.robotparser
from datetime import datetime
from typing import Optional
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
        return False


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
