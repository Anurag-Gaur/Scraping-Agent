"""
zbrain_scraper.py — ZBrain Agent Store Scraper

Scrapes ZBrain.ai agent store to find agents matching a requirement.
Used as primary scraper before falling back to DuckDuckGo + LLM.

Integration with research_bot:
  Try zbrain_scraper first → if insufficient results → fall back to DuckDuckGo + LLM
"""

import os
import re
import json
import time
import random
import logging
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# CONSTANTS
BASE_URL = "https://zbrain.ai"
AGENTS_INDEX = "https://zbrain.ai/agents/"
CACHE_FILE = "Data/zbrain_cache.json"
REQUEST_DELAY = (1.5, 3.0)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def _make_browser(playwright):
    """Create a Playwright browser and context."""
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    ctx = browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1440, "height": 900},
    )
    return browser, ctx


def _get_soup(page, url: str, wait_selector: str = "body", timeout: int = 20000):
    """Navigate to url, wait for selector, return BeautifulSoup."""
    try:
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        page.wait_for_selector(wait_selector, timeout=timeout)
    except PlaywrightTimeout:
        log.warning(f"Timeout loading {url}")
    time.sleep(random.uniform(*REQUEST_DELAY))
    return BeautifulSoup(page.content(), "html.parser")


def discover_agent_urls(page) -> list[dict]:
    """
    Scrape the ZBrain agent store index page.
    Returns a list of dicts: {name, url, category, department}
    """
    log.info(f"[zbrain_scraper] Loading agent index: {AGENTS_INDEX}")
    soup = _get_soup(page, AGENTS_INDEX, wait_selector="body")

    agents = []
    seen_urls = set()

    # Pattern: /agents/{category}/all/{department}/{slug}/
    agent_link_pattern = re.compile(r"^/agents/.+/.+/.+/.+/$")

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("/"):
            href = BASE_URL + href
        path = href.replace(BASE_URL, "")

        if agent_link_pattern.match(path) and href not in seen_urls:
            seen_urls.add(href)

            name = a_tag.get_text(strip=True)[:100]
            parts = path.strip("/").split("/")
            category = parts[1].replace("-", " ").title() if len(parts) > 1 else ""
            department = parts[3].replace("-", " ").title() if len(parts) > 3 else ""

            agents.append({
                "name": name,
                "url": href,
                "category": category,
                "department": department,
            })

    log.info(f"[zbrain_scraper] Discovered {len(agents)} agent URLs")
    return agents


def _clean(text: str) -> str:
    """Clean whitespace from text."""
    return " ".join(text.split()).strip()


def scrape_agent_summary(page, url: str) -> dict:
    """
    Scrape a single agent page.
    Returns: {url, what_it_does, key_capabilities, problems_it_solves, business_benefits}
    """
    log.info(f"[zbrain_scraper] Scraping: {url}")
    soup = _get_soup(page, url, wait_selector="body")

    result = {
        "url": url,
        "what_it_does": "",
        "key_capabilities": [],
        "problems_it_solves": [],
        "business_benefits": [],
    }

    def get_section_text(heading_fragment: str) -> str:
        """Get all paragraph text after a heading containing fragment."""
        for heading in soup.find_all(["h1", "h2", "h3"]):
            if heading_fragment.lower() in heading.get_text().lower():
                texts = []
                for sib in heading.find_next_siblings():
                    if sib.name in ["h1", "h2", "h3"]:
                        break
                    t = sib.get_text(separator=" ", strip=True)
                    if t and len(t) > 20:
                        texts.append(t)
                return _clean(" ".join(texts))
        return ""

    def get_bullets_after_heading(heading_fragment: str) -> list[str]:
        """Get all bullet points after a heading containing fragment."""
        for heading in soup.find_all(["h2", "h3", "h4", "strong", "p"]):
            if heading_fragment.lower() in heading.get_text().lower():
                items = []
                for sib in heading.find_next_siblings():
                    if sib.name in ["h2", "h3"]:
                        break
                    if sib.name in ["ul", "ol"]:
                        items.extend([_clean(li.get_text()) for li in sib.find_all("li")])
                return items
        return []

    # Extract sections
    about = get_section_text("About the Agent")
    if not about:
        for p in soup.find_all("p"):
            text = _clean(p.get_text())
            if len(text) > 100 and not text.startswith("http"):
                about = text
                break
    result["what_it_does"] = about[:600] if about else ""

    # Key capabilities
    capabilities = get_bullets_after_heading("Key Tasks")
    if not capabilities:
        for heading in soup.find_all(["h2", "h3"]):
            if "how" in heading.get_text().lower() and "works" in heading.get_text().lower():
                for sib in heading.find_next_siblings():
                    if sib.name in ["h2", "h3"]:
                        break
                    if sib.name in ["ul", "ol"]:
                        capabilities = [_clean(li.get_text()) for li in sib.find_all("li")]
                        break
                if capabilities:
                    break
    result["key_capabilities"] = capabilities[:12]

    # Problems it solves
    challenges_text = get_section_text("Challenges")
    problems = get_bullets_after_heading("Challenges")

    if problems:
        result["problems_it_solves"] = problems[:10]
    elif challenges_text:
        sentences = [_clean(s) for s in re.split(r'[.!?]+', challenges_text) if len(_clean(s)) > 30]
        result["problems_it_solves"] = sentences[:6]

    # Business benefits
    benefits = get_bullets_after_heading("Outcome")

    if not benefits:
        benefit_keywords = [
            "reduce", "automate", "improve", "enhance", "accelerate",
            "streamline", "efficiency", "accuracy", "speed", "cost",
            "save", "increase", "eliminate", "faster", "accurate"
        ]
        for elem in soup.find_all(["p", "li"]):
            text = _clean(elem.get_text())
            text_lower = text.lower()
            if any(kw in text_lower for kw in benefit_keywords):
                if len(text) > 50 and text not in benefits:
                    benefits.append(text[:250])

        benefits = benefits[:10]

    result["business_benefits"] = benefits

    return result


def scrape_zbrain_agents(requirement: str, max_agents: int = 0, use_cache: bool = True) -> list[dict]:
    """
    Full ZBrain scrape pipeline.
    
    Args:
        requirement: What to search for (e.g., "Accounts Payable Agent")
        max_agents: 0 = all; >0 = limit
        use_cache: Load from cache if available
    
    Returns:
        List of agent dicts with details
    """
    if not PLAYWRIGHT_AVAILABLE:
        log.error("[zbrain_scraper] Playwright not available. "
                  "Install: pip install playwright && playwright install")
        return []

    # Try cache first
    if use_cache and Path(CACHE_FILE).exists():
        log.info(f"[zbrain_scraper] Loading from cache: {CACHE_FILE}")
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"[zbrain_scraper] Cache load failed: {e}")

    all_agents = []

    try:
        with sync_playwright() as playwright:
            browser, ctx = _make_browser(playwright)
            page = ctx.new_page()

            # Discover all agents
            agent_stubs = discover_agent_urls(page)
            if max_agents:
                agent_stubs = agent_stubs[:max_agents]

            if not agent_stubs:
                log.warning("[zbrain_scraper] No agent URLs found")
                browser.close()
                return []

            # Scrape each agent
            for idx, stub in enumerate(agent_stubs, 1):
                log.info(f"[zbrain_scraper] [{idx}/{len(agent_stubs)}] {stub['name']}")
                try:
                    summary = scrape_agent_summary(page, stub["url"])
                    merged = {**stub, **summary}
                    all_agents.append(merged)
                except Exception as exc:
                    log.error(f"[zbrain_scraper] Failed to scrape {stub['name']}: {exc}")
                    all_agents.append(stub)

            browser.close()

    except Exception as e:
        log.error(f"[zbrain_scraper] Scrape failed: {e}")
        return []

    # Save cache
    os.makedirs("Data", exist_ok=True)
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(all_agents, f, indent=2)
        log.info(f"[zbrain_scraper] Cached {len(all_agents)} agents → {CACHE_FILE}")
    except Exception as e:
        log.warning(f"[zbrain_scraper] Cache save failed: {e}")

    return all_agents


def filter_agents_by_requirement(agents: list[dict], requirement: str) -> list[dict]:
    """
    Filter agents matching the requirement using keyword matching.
    
    Args:
        agents: List of agent dicts
        requirement: Search term
    
    Returns:
        Matching agents (sorted by relevance)
    """
    if not agents:
        return []

    keywords = [w.lower() for w in re.split(r"\W+", requirement) if len(w) > 3]
    scored = []

    for agent in agents:
        # Build searchable text
        searchable = " ".join(filter(None, [
            agent.get("name", ""),
            agent.get("what_it_does", ""),
            agent.get("category", ""),
            agent.get("department", ""),
            " ".join(agent.get("key_capabilities", [])),
            " ".join(agent.get("problems_it_solves", [])),
            " ".join(agent.get("business_benefits", [])),
        ])).lower()

        score = sum(1 for kw in keywords if kw in searchable)
        if score > 0:
            scored.append((score, agent))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [agent for _, agent in scored]


def format_agent_for_research(agent: dict) -> str:
    """Format agent for display in research output."""
    lines = [
        f"Agent: {agent.get('name', 'Unknown')}",
        f"Category: {agent.get('category', '')} → {agent.get('department', '')}",
        f"URL: {agent.get('url', '')}",
        "",
    ]

    what = agent.get("what_it_does", "")
    if what:
        lines.append(f"What It Does: {what}\n")

    caps = agent.get("key_capabilities", [])
    if caps:
        lines.append("Key Capabilities:")
        for c in caps[:6]:
            lines.append(f"  • {c}")
        lines.append("")

    probs = agent.get("problems_it_solves", [])
    if probs:
        lines.append("Problems It Solves:")
        for p in probs[:5]:
            lines.append(f"  • {p}")
        lines.append("")

    benefits = agent.get("business_benefits", [])
    if benefits:
        lines.append("Business Benefits:")
        for b in benefits[:5]:
            lines.append(f"  • {b}")

    return "\n".join(lines)
