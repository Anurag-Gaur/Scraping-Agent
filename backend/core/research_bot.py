"""
research_bot.py — Client Requirement Research Agent

HOW IT WORKS
────────────
You type a client requirement (e.g. "Accounts Payable agent").
The bot then:
  1. Searches DuckDuckGo for that agent on every competitor platform
  2. Scrapes each result — extracting the exact blueprint (features,
     integrations, tech, workflow) from their product pages
  3. Sends everything to Groq to synthesise a build spec
  4. Outputs a ready-to-implement blueprint your team can use

COMPETITORS COVERED (auto-searched for every requirement)
  ZBrain · RelevanceAI · CrewAI · Make · Zapier · Workato
  LangChain · AutoGen · Beam · HighRadius · ServiceNow

USAGE
─────
  python research_bot.py
  → prompts: "Enter client requirement:"
  → type e.g. "accounts payable agent" or "invoice processing agent"

  Or pass it directly:
  python research_bot.py "accounts payable agent"

OUTPUT FILES (saved to Data/research_output/<requirement_slug>/)
  raw_competitor_data.json   — full scraped text per competitor page
  build_spec.json            — final structured build spec (main output)

SELENIUM (optional — improves JS-heavy site scraping)
  Install: pip install undetected-chromedriver selenium
  Set in .env: SELENIUM_MODE=auto  (default)
"""

import os
import sys
import json
import re
import time
import hashlib
import requests
from urllib.parse import quote_plus, unquote
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# ── Add parent directory to path for imports ───────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ── Optional Selenium ─────────────────────────────────────────────────
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

load_dotenv()

# ── RAG store (FAISS + sentence-transformers) ─────────────────────────
try:
    from core import rag_store
    RAG_ENABLED = True
except ImportError:
    RAG_ENABLED = False
    print("[research_bot] WARNING: rag_store unavailable. "
          "Run: pip install faiss-cpu sentence-transformers numpy")

# ── PostgreSQL agent store ────────────────────────────────────────────
try:
    from database import pg_store
    PG_ENABLED = True
except ImportError:
    PG_ENABLED = False
    print("[research_bot] WARNING: pg_store unavailable. "
          "Run: pip install psycopg2-binary")

# ── ZBrain agent scraper (Playwright-based) ────────────────────────────
try:
    from core import zbrain_scraper
    ZBRAIN_ENABLED = True
except ImportError:
    ZBRAIN_ENABLED = False
    print("[research_bot] WARNING: zbrain_scraper unavailable. "
          "Run: pip install playwright && playwright install")

# ============================= CONFIG ================================ #
BOT_NAME        = "research_bot"
STATUS_FILE     = "Maintenance/status_file.lock"
OUTPUT_BASE_DIR = "Data/research_output"

# ── Groq ──────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"   # 128k context
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ── Selenium ──────────────────────────────────────────────────────────
_sel_mode       = os.getenv("SELENIUM_MODE", "auto").lower()
ENABLE_SELENIUM = (SELENIUM_AVAILABLE if _sel_mode == "auto"
                   else _sel_mode == "on")
SELENIUM_PROFILE = os.getenv(
    "SELENIUM_PROFILE",
    r"C:\Users\Abcom\AppData\Local\Google\Chrome\User Data\research_bot"
)

# ── Scraper settings ──────────────────────────────────────────────────
MIN_CONTENT_LINES     = 6     # lines >30 chars to count as useful
CHAR_LIMIT_PER_SOURCE = 6000  # max chars kept per scraped page
SCRAPE_DELAY          = 1.2   # seconds between requests
MAX_PAGES_PER_QUERY   = 4     # competitor pages to scrape per search query

# ── Competitor platforms to search on ─────────────────────────────────
# Each entry: (label, search_template)
# {req} is replaced with the client requirement
COMPETITOR_SEARCHES = [
    ("zbrain",               "ZBrain AI agent {req}"),
    ("relevanceai",          "RelevanceAI agent {req}"),
    ("crewai",               "CrewAI {req} agent"),
    ("make",                 "Make.com automation {req}"),
    ("zapier",               "Zapier AI agent {req}"),
    ("workato",              "Workato {req} automation"),
    ("highradius",           "HighRadius {req} AI"),
    ("servicenow",           "ServiceNow {req} agent automation"),
    ("automation_anywhere",  "Automation Anywhere {req} bot"),
    ("uipath",               "UiPath {req} automation agent"),
]

# ── JS-heavy domains — use Selenium automatically ─────────────────────
JS_HEAVY = re.compile(
    r"(zbrain\.ai|relevanceai\.com|crewai\.com|make\.com|"
    r"zapier\.com|workato\.com|servicenow\.com|automationanywhere\.com)",
    re.IGNORECASE,
)
# ===================================================================== #

os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
os.makedirs("Maintenance", exist_ok=True)


# ─────────────────────────── Helpers ─────────────────────────────────

def slugify(text: str) -> str:
    """Convert requirement text to a safe folder name."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:50]


def update_status(status: str):
    try:
        with open(STATUS_FILE, "a") as f:
            f.write(f"{BOT_NAME}: {status}\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        pass
    print(f"[{BOT_NAME}] {status}")


# ───────────────────────── Scraper engine ────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def clean_html(html: str, limit: int = CHAR_LIMIT_PER_SOURCE) -> str:
    """Strip boilerplate, return clean readable text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer",
                     "header", "aside", "iframe", "svg", "meta", "link",
                     "button", "form", "input", "select", "template"]):
        tag.decompose()
    main = (soup.find("main") or soup.find("article") or
            soup.find(id=re.compile(r"content|main", re.I)) or
            soup.find(class_=re.compile(r"content|main|article|product", re.I)))
    text = (main or soup).get_text(separator="\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:limit]


def quality(text: str) -> int:
    return len([l for l in text.splitlines() if len(l.strip()) > 30])


def scrape_static(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        return clean_html(r.text)
    except Exception as e:
        return f"[scrape failed: {e}]"


def scrape_selenium(url: str) -> str:
    if not SELENIUM_AVAILABLE:
        return scrape_static(url)
    opts = uc.ChromeOptions()
    opts.add_argument(f"--user-data-dir={SELENIUM_PROFILE}")
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = None
    try:
        driver = uc.Chrome(options=opts, use_subprocess=True)
        driver.get(url)
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)
        return clean_html(driver.page_source)
    except Exception as e:
        return f"[selenium failed: {e}]"
    finally:
        if driver:
            try: driver.quit()
            except: pass


def smart_scrape(url: str, label: str) -> dict:
    """Scrape a URL — auto-selects Selenium for JS-heavy domains."""
    is_js = bool(JS_HEAVY.search(url)) and ENABLE_SELENIUM
    text  = scrape_selenium(url) if is_js else scrape_static(url)

    # Upgrade to Selenium if static result is thin
    if (not is_js and quality(text) < MIN_CONTENT_LINES
            and ENABLE_SELENIUM and SELENIUM_AVAILABLE):
        print(f"  [{label}] static thin ({quality(text)} lines) → retrying with Selenium")
        selenium_text = scrape_selenium(url)
        if quality(selenium_text) > quality(text):
            text = selenium_text
            is_js = True

    q = ("good" if quality(text) >= MIN_CONTENT_LINES * 2 else
         "ok"   if quality(text) >= MIN_CONTENT_LINES else "poor")
    icon = {"good": "✓", "ok": "~", "poor": "✗"}[q]
    method = "selenium" if is_js else "static"
    print(f"  [{icon}] {label} ({method}) — {len(text)} chars, quality={q}")
    return {"label": label, "url": url, "text": text, "quality": q}


# ─────────────────────── DuckDuckGo search ───────────────────────────

SKIP = re.compile(
    r"(twitter|x\.com|linkedin|youtube|facebook|reddit|quora|"
    r"pinterest|instagram|tiktok|mailto:|javascript:)",
    re.IGNORECASE,
)


def ddg_search(query: str, max_results: int = MAX_PAGES_PER_QUERY) -> list:
    """
    Search DuckDuckGo using the duckduckgo-search package (primary),
    falling back to HTML scraping if the package is not installed.
    Install: pip install duckduckgo-search
    """
    # ── Primary: duckduckgo-search package ───────────────────────────
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results * 2):
                href  = r.get("href", "")
                title = r.get("title", "")[:100]
                if not href.startswith("http") or SKIP.search(href):
                    continue
                results.append({"url": href, "title": title})
                if len(results) >= max_results:
                    break
        return results

    except ImportError:
        print("  [DDG] duckduckgo-search not installed — using HTML fallback")
        print("        Run: pip install duckduckgo-search")

    except Exception as e:
        print(f"  [DDG] duckduckgo-search failed for '{query}': {e} — trying HTML fallback")

    # ── Fallback: HTML scraping ───────────────────────────────────────
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup    = BeautifulSoup(r.text, "html.parser")
        results = []
        items   = soup.select(".result__body") or soup.select(".results_links")
        if items:
            for item in items[:max_results * 2]:
                a = (item.select_one(".result__a") or item.find("a", href=True))
                if not a: continue
                href  = a.get("href", "")
                match = re.search(r"uddg=([^&]+)", href)
                if match: href = unquote(match.group(1))
                if not href.startswith("http") or SKIP.search(href): continue
                results.append({"url": href, "title": a.get_text(strip=True)[:100]})
                if len(results) >= max_results: break
        else:
            for a in soup.find_all("a", href=True):
                href  = a["href"]
                match = re.search(r"uddg=([^&]+)", href)
                if not match: continue
                href = unquote(match.group(1))
                if not href.startswith("http") or SKIP.search(href): continue
                title = a.get_text(strip=True)
                if len(title) < 5: continue
                results.append({"url": href, "title": title[:100]})
                if len(results) >= max_results: break
        return results
    except Exception as e:
        print(f"  [DDG] HTML fallback also failed for '{query}': {e}")
        return []


# ────────────────── Main research function ───────────────────────────

def research_requirement(requirement: str) -> dict:
    """
    For a given client requirement:
      1. Search each competitor platform for that agent
      2. Scrape the top results
      3. Return structured dict of all findings
    """
    print(f"\n[{BOT_NAME}] Researching: '{requirement}'")
    print(f"[{BOT_NAME}] Searching {len(COMPETITOR_SEARCHES)} competitor platforms...\n")

    findings      = {}   # label → scraped text
    pages_scraped = []   # metadata list

    for platform, template in COMPETITOR_SEARCHES:
        query = template.replace("{req}", requirement)
        print(f"  Searching {platform}: \"{query}\"")

        results = ddg_search(query)
        time.sleep(1.0)

        if not results:
            print(f"  [–] {platform}: no results found")
            continue

        # Scrape top results for this platform
        platform_texts = []
        for i, result in enumerate(results[:MAX_PAGES_PER_QUERY]):
            label = f"{platform}_{i+1}"
            data  = smart_scrape(result["url"], label)
            data["title"]    = result["title"]
            data["platform"] = platform
            data["query"]    = query

            if data["quality"] != "poor":
                platform_texts.append(f"[{result['title']}]\n{data['text']}")

            pages_scraped.append(data)
            time.sleep(SCRAPE_DELAY)

        if platform_texts:
            findings[platform] = "\n\n---\n\n".join(platform_texts)
        else:
            print(f"  [–] {platform}: all pages were poor quality")

    good = sum(1 for p in pages_scraped if p["quality"] == "good")
    ok   = sum(1 for p in pages_scraped if p["quality"] == "ok")
    poor = sum(1 for p in pages_scraped if p["quality"] == "poor")
    print(f"\n[{BOT_NAME}] Scraping done — "
          f"✓ good={good}  ~ ok={ok}  ✗ poor={poor}  "
          f"({len(pages_scraped)} pages total)")

    return {"requirement": requirement, "findings": findings,
            "pages_scraped": pages_scraped, "scraped_at": datetime.now().isoformat()}


# ────────────────── Parallel Research (ZBrain + DuckDuckGo + Competitors) ──────

def research_requirement_hybrid(requirement: str) -> dict:
    """
    Parallel research approach:
      1. Scrape ZBrain agents simultaneously with DuckDuckGo search
      2. Combine ALL findings (both ZBrain agents + competitor sites)
      3. Return comprehensive results with both sources
    
    This provides maximum coverage — agent specs from ZBrain + competitor
    implementations from DuckDuckGo, all in one analysis.
    """
    print(f"\n[{BOT_NAME}] Research Strategy: Parallel (ZBrain + DuckDuckGo + Competitors)")
    print(f"[{BOT_NAME}] Requirement: '{requirement}'")

    zbrain_agents = []
    ddg_findings = {}
    pages_scraped = []

    # ── TIER 1: ZBrain Agent Scraper (Parallel) ───────────────────────────
    zbrain_success = False
    if ZBRAIN_ENABLED:
        print(f"\n[{BOT_NAME}] [Parallel] Searching ZBrain Agent Store...")
        try:
            all_agents = zbrain_scraper.scrape_zbrain_agents(requirement, max_agents=0, use_cache=True)
            matching_agents = zbrain_scraper.filter_agents_by_requirement(all_agents, requirement)

            if matching_agents:
                zbrain_agents = matching_agents[:5]  # Top 5 matches
                zbrain_success = True
                print(f"[{BOT_NAME}] ✓ [ZBrain] Found {len(zbrain_agents)} matching agents")

                # Format agents for inclusion in findings
                ddg_findings["zbrain_agents"] = "\n\n---\n\n".join([
                    zbrain_scraper.format_agent_for_research(agent)
                    for agent in zbrain_agents
                ])
            else:
                print(f"[{BOT_NAME}] ~ [ZBrain] No matching agents found (will supplement with competitors)")

        except Exception as e:
            print(f"[{BOT_NAME}] ✗ [ZBrain] Error: {e} (will continue with competitors)")

    else:
        print(f"[{BOT_NAME}] ~ [ZBrain] Skipped — zbrain_scraper not available")

    # ── TIER 2: DuckDuckGo + Competitor Platforms (Parallel) ──────────────
    print(f"\n[{BOT_NAME}] [Parallel] Searching competitor platforms via DuckDuckGo...")
    try:
        ddg_result = research_requirement(requirement)
        
        # Merge findings
        ddg_findings.update(ddg_result.get("findings", {}))
        pages_scraped = ddg_result.get("pages_scraped", [])
        
        good = sum(1 for p in pages_scraped if p["quality"] == "good")
        ok   = sum(1 for p in pages_scraped if p["quality"] == "ok")
        print(f"[{BOT_NAME}] ✓ [DuckDuckGo] Scraped {len(pages_scraped)} pages "
              f"(✓ good={good}  ~ ok={ok})")

    except Exception as e:
        print(f"[{BOT_NAME}] ✗ [DuckDuckGo] Error: {e}")

    # ── Return combined results ────────────────────────────────────────────
    tier_used = []
    if zbrain_success:
        tier_used.append("zbrain")
    if pages_scraped:
        tier_used.append("ddg_competitors")
    
    print(f"\n[{BOT_NAME}] ═══════════════════════════════════════════════════════")
    print(f"[{BOT_NAME}] Combined Research Complete")
    print(f"[{BOT_NAME}] Sources: {' + '.join(tier_used) if tier_used else 'none'}")
    if zbrain_agents:
        print(f"[{BOT_NAME}] ZBrain agents: {len(zbrain_agents)}")
    if pages_scraped:
        print(f"[{BOT_NAME}] Competitor pages: {len(pages_scraped)}")
    print(f"[{BOT_NAME}] ═══════════════════════════════════════════════════════")

    return {
        "requirement": requirement,
        "findings": ddg_findings,
        "pages_scraped": pages_scraped,
        "scraped_at": datetime.now().isoformat(),
        "tier_used": tier_used,
        "zbrain_agents": zbrain_agents,
    }


# ────────────────────────── LLM analysis ─────────────────────────────

def build_prompt(requirement: str, findings: dict, past_context: str = "") -> str:
    # Build competitor sections
    competitor_blocks = []
    for platform, text in findings.items():
        block = f"=== {platform.upper()} ===\n{text[:2000]}"
        competitor_blocks.append(block)

    competitors_text = "\n\n".join(competitor_blocks) or "No competitor data found."

    # Inject RAG context block if available
    rag_section = ""
    if past_context:
        rag_section = f"""
--- KNOWLEDGE BASE CONTEXT (from FAISS RAG store) ---
The following snippets were retrieved from our internal knowledge store
based on semantic similarity to this requirement. Use them to enrich
and cross-reference the build spec — but prioritise the live competitor
data above if there is any conflict.

{past_context}
--- END KNOWLEDGE BASE CONTEXT ---
"""

    return f"""You are a senior AI solutions architect. A client has requested:

CLIENT REQUIREMENT: "{requirement}"

Below is what the leading AI agent platforms currently offer for this requirement.
Analyse all of it and produce a detailed build specification.

{competitors_text}
{rag_section}
---

Return ONLY valid JSON with no preamble and no markdown fences:

{{
  "requirement": "{requirement}",
  "build_spec": {{
    "agent_name": "...",
    "purpose": "...",
    "target_user": "...",

    "core_capabilities": [
      {{"capability": "...", "description": "..."}}
    ],

    "workflow_steps": [
      {{"step": 1, "action": "...", "detail": "..."}}
    ],

    "integrations": [
      {{"system": "...", "purpose": "..."}}
    ],

    "data_inputs": ["..."],
    "data_outputs": ["..."],

    "suggested_tech_stack": {{
      "llm": "...",
      "orchestration": "...",
      "database": "...",
      "integrations": ["..."]
    }},

    "build_complexity": "low|medium|high",
    "estimated_build_days": 0,

    "what_competitors_have": "...",
    "our_differentiation": "..."
  }},

  "competitor_summary": {{
    "zbrain":       "...",
    "relevanceai":  "...",
    "crewai":       "...",
    "others":       "..."
  }}
}}"""


def call_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY missing — add it to your .env file")
    print(f"[{BOT_NAME}] Prompt size: {len(prompt)} chars (~{len(prompt)//4} tokens)")
    resp = requests.post(
        GROQ_API_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                 "Content-Type": "application/json"},
        json={"model": GROQ_MODEL,
              "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.2,
              "max_tokens": 4096},
        timeout=90,
    )
    if not resp.ok:
        print(f"[ERROR] Groq {resp.status_code}: {resp.text[:400]}")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def analyse(requirement: str, findings: dict, past_context: str = "") -> dict:
    print(f"\n[{BOT_NAME}] Sending to Groq for analysis...")
    prompt = build_prompt(requirement, findings, past_context)
    raw    = call_groq(prompt)

    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.rstrip())
        raw = raw.strip()

    try:
        result = json.loads(raw)
        print(f"[{BOT_NAME}] Analysis complete.")
        return result
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse failed: {e}\nRaw:\n{raw[:400]}")
        return {"error": "JSON parse failed", "raw": raw}


# ──────────────────────────── Save ───────────────────────────────────

# ──────────────────────────── Save ───────────────────────────────────

def save_as_docx(build_spec: dict, output_dir: str, requirement: str) -> str:
    """
    Generate a formatted Word document using python-docx (no Node.js needed).
    pip install python-docx
    """
    try:
        from docx import Document as DocxDocument
        from docx.shared import Pt, RGBColor, Inches, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        import copy
    except ImportError:
        print("  [WARN] python-docx not installed — run: pip install python-docx")
        return None

    bs  = build_spec.get("build_spec", {})
    cs  = build_spec.get("competitor_summary", {})

    BLUE  = RGBColor(0x1F, 0x4E, 0x79)
    LBLUE = RGBColor(0x2E, 0x75, 0xB6)
    GRAY  = RGBColor(0x59, 0x59, 0x59)
    WHITE = RGBColor(0xFF, 0xFF, 0xFF)

    def set_cell_bg(cell, hex_color):
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd  = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  hex_color)
        tcPr.append(shd)

    def add_heading(doc, text, level=1):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after  = Pt(6)
        run = p.add_run(text)
        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(16) if level == 1 else Pt(13)
        run.font.color.rgb = BLUE if level == 1 else LBLUE
        # bottom border on h1
        if level == 1:
            pPr  = p._p.get_or_add_pPr()
            pBdr = OxmlElement("w:pBdr")
            bot  = OxmlElement("w:bottom")
            bot.set(qn("w:val"),   "single")
            bot.set(qn("w:sz"),    "6")
            bot.set(qn("w:space"), "4")
            bot.set(qn("w:color"), "2E75B6")
            pBdr.append(bot)
            pPr.append(pBdr)
        return p

    def add_body(doc, text, bold=False, color=None):
        p   = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after  = Pt(2)
        run = p.add_run(str(text) if text else "—")
        run.font.name  = "Arial"
        run.font.size  = Pt(11)
        run.bold       = bold
        run.font.color.rgb = color or RGBColor(0x22, 0x22, 0x22)
        return p

    def add_label_value(doc, label, value):
        p    = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after  = Pt(3)
        run1 = p.add_run(label + ": ")
        run1.bold = True
        run1.font.name = "Arial"
        run1.font.size = Pt(11)
        run1.font.color.rgb = BLUE
        run2 = p.add_run(str(value) if value else "—")
        run2.font.name = "Arial"
        run2.font.size = Pt(11)
        run2.font.color.rgb = RGBColor(0x22, 0x22, 0x22)

    def add_bullet(doc, text):
        p   = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after  = Pt(1)
        run = p.add_run(str(text) if text else "")
        run.font.name = "Arial"
        run.font.size = Pt(11)

    def add_numbered(doc, text):
        p   = doc.add_paragraph(style="List Number")
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after  = Pt(1)
        run = p.add_run(str(text) if text else "")
        run.font.name = "Arial"
        run.font.size = Pt(11)

    def make_table(doc, headers, rows, col_widths):
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        # Header row
        hdr = table.rows[0]
        for i, (h, w) in enumerate(zip(headers, col_widths)):
            cell = hdr.cells[i]
            cell.width = Inches(w)
            set_cell_bg(cell, "D6E4F0")
            cell.paragraphs[0].clear()
            run = cell.paragraphs[0].add_run(h)
            run.bold = True
            run.font.name = "Arial"
            run.font.size = Pt(10)
            run.font.color.rgb = BLUE
        # Data rows
        for ri, row_data in enumerate(rows):
            row = table.add_row()
            fill = "F2F2F2" if ri % 2 == 0 else "FFFFFF"
            for i, (val, w) in enumerate(zip(row_data, col_widths)):
                cell = row.cells[i]
                cell.width = Inches(w)
                set_cell_bg(cell, fill)
                cell.paragraphs[0].clear()
                run = cell.paragraphs[0].add_run(str(val) if val else "—")
                run.font.name = "Arial"
                run.font.size = Pt(10)
        return table

    # ── Build document ──────────────────────────────────────────────
    doc = DocxDocument()

    # Page margins
    for section in doc.sections:
        section.top_margin    = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin   = Inches(1)
        section.right_margin  = Inches(1)

    # Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_after = Pt(4)
    tr = title_p.add_run("AI Agent Build Specification")
    tr.bold = True
    tr.font.name = "Arial"
    tr.font.size = Pt(26)
    tr.font.color.rgb = BLUE

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(2)
    sr = sub_p.add_run(requirement.upper())
    sr.bold = True
    sr.font.name = "Arial"
    sr.font.size = Pt(14)
    sr.font.color.rgb = LBLUE

    date_p = doc.add_paragraph()
    date_p.paragraph_format.space_after = Pt(12)
    dr = date_p.add_run("Generated: " + datetime.now().strftime("%d %B %Y"))
    dr.font.name = "Arial"
    dr.font.size = Pt(10)
    dr.font.color.rgb = GRAY

    doc.add_paragraph()

    # ── At a glance ─────────────────────────────────────────────────
    add_heading(doc, "At a glance")
    tstack = bs.get("suggested_tech_stack", {})
    make_table(doc,
        ["Field", "Value"],
        [
            ["Agent name",        bs.get("agent_name", "—")],
            ["Target user",       bs.get("target_user", "—")],
            ["Build complexity",  bs.get("build_complexity", "—")],
            ["Estimated days",    str(bs.get("estimated_build_days", "—"))],
            ["LLM",               tstack.get("llm", "—")],
            ["Orchestration",     tstack.get("orchestration", "—")],
            ["Database",          tstack.get("database", "—")],
        ],
        [2.2, 4.3]
    )
    doc.add_paragraph()

    # ── Purpose ─────────────────────────────────────────────────────
    add_heading(doc, "Purpose")
    add_body(doc, bs.get("purpose", "—"))
    doc.add_paragraph()

    # ── Core capabilities ────────────────────────────────────────────
    add_heading(doc, "Core capabilities")
    caps = bs.get("core_capabilities", [])
    if caps:
        make_table(doc,
            ["Capability", "Description"],
            [[c.get("capability",""), c.get("description","")] for c in caps],
            [2.2, 4.3]
        )
    doc.add_paragraph()

    # ── Workflow steps ───────────────────────────────────────────────
    add_heading(doc, "Workflow steps")
    for s in bs.get("workflow_steps", []):
        p   = doc.add_paragraph(style="List Number")
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after  = Pt(2)
        r1  = p.add_run((s.get("action","")) + " — ")
        r1.bold = True
        r1.font.name = "Arial"
        r1.font.size = Pt(11)
        r1.font.color.rgb = BLUE
        r2  = p.add_run(s.get("detail",""))
        r2.font.name = "Arial"
        r2.font.size = Pt(11)
    doc.add_paragraph()

    # ── Data ────────────────────────────────────────────────────────
    add_heading(doc, "Data")
    add_heading(doc, "Inputs", level=2)
    for d in bs.get("data_inputs", []):
        add_bullet(doc, d)
    add_heading(doc, "Outputs", level=2)
    for d in bs.get("data_outputs", []):
        add_bullet(doc, d)
    doc.add_paragraph()

    # ── Integrations ─────────────────────────────────────────────────
    add_heading(doc, "Integrations")
    ints = bs.get("integrations", [])
    if ints:
        make_table(doc,
            ["System", "Purpose"],
            [[i.get("system",""), i.get("purpose","")] for i in ints],
            [2.5, 4.0]
        )
    doc.add_paragraph()

    # ── Tech stack ───────────────────────────────────────────────────
    add_heading(doc, "Suggested tech stack")
    add_label_value(doc, "LLM",           tstack.get("llm"))
    add_label_value(doc, "Orchestration", tstack.get("orchestration"))
    add_label_value(doc, "Database",      tstack.get("database"))
    extras = tstack.get("integrations", [])
    if extras:
        add_body(doc, "Additional integrations:", bold=True, color=BLUE)
        for e in extras:
            add_bullet(doc, e)
    doc.add_paragraph()

    # ── Differentiation ──────────────────────────────────────────────
    add_heading(doc, "Competitive differentiation")
    add_heading(doc, "What competitors have", level=2)
    add_body(doc, bs.get("what_competitors_have"))
    add_heading(doc, "Our differentiation", level=2)
    add_body(doc, bs.get("our_differentiation"))
    doc.add_paragraph()

    # ── Competitor analysis ──────────────────────────────────────────
    add_heading(doc, "Competitor analysis")
    comp_rows = [[k.capitalize(), v] for k, v in cs.items()
                 if v and v not in ("—", "No data available", "No data available.")]
    if comp_rows:
        make_table(doc, ["Platform", "What they offer"], comp_rows, [1.8, 4.7])
    else:
        add_body(doc, "No competitor data was found for this requirement.")
    doc.add_paragraph()

    # ── Save ─────────────────────────────────────────────────────────
    docx_path = os.path.join(output_dir, f"{slugify(requirement)}_build_spec.docx")
    doc.save(docx_path)
    print(f"  {slugify(requirement)}_build_spec.docx  ← Word document (open this!)")
    return docx_path


def save_outputs(requirement: str, raw_data: dict, build_spec: dict):
    slug       = slugify(requirement)
    output_dir = os.path.join(OUTPUT_BASE_DIR, slug)
    os.makedirs(output_dir, exist_ok=True)

    # Save scraping output
    scrape_path = os.path.join(output_dir, "scrape_source.json")
    raw_path    = os.path.join(output_dir, "raw_competitor_data.json")
    spec_path   = os.path.join(output_dir, "build_spec.json")

    # Create enhanced scrape_source.json with URLs and metadata
    scrape_source = {
        "requirement": raw_data.get("requirement", requirement),
        "scraped_at": raw_data.get("scraped_at"),
        "summary": {
            "total_pages_scraped": len(raw_data.get("pages_scraped", [])),
            "platforms_found": list(raw_data.get("findings", {}).keys()),
        },
        "pages_scraped_with_urls": [
            {
                "label": page.get("label"),
                "platform": page.get("platform"),
                "url": page.get("url"),
                "title": page.get("title"),
                "quality": page.get("quality"),
                "text": page.get("text")[:500] + "..." if len(page.get("text", "")) > 500 else page.get("text"),
                "text_full": page.get("text"),
            }
            for page in raw_data.get("pages_scraped", [])
        ],
        "findings_by_platform": raw_data.get("findings", {}),
    }
    
    # Save enhanced scrape source
    with open(scrape_path, "w", encoding="utf-8") as f:
        json.dump(scrape_source, f, indent=2)
    
    # Keep raw_competitor_data.json for backward compatibility
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, indent=2)

    # Save LLM-generated spec
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(build_spec, f, indent=2)

    print(f"\n[{BOT_NAME}] Saved to: {output_dir}/")
    print(f"  scrape_source.json        ← all scraped pages WITH URLs")
    print(f"  raw_competitor_data.json  ← (legacy format)")
    print(f"  build_spec.json           ← LLM-generated blueprint")

    # ─────── Store agent data to PostgreSQL ──────────────────────────
    if PG_ENABLED and "build_spec" in build_spec:
        bs = build_spec["build_spec"]
        
        # Extract unique source URLs from scraped pages
        source_urls = list(set([
            page.get("url") for page in raw_data.get("pages_scraped", [])
            if page.get("url") and page.get("quality") != "poor"
        ]))
        
        agent_data = {
            "agent_name": bs.get("agent_name", "Unknown Agent"),
            "description": bs.get("purpose", ""),
            "features": {
                "capabilities": bs.get("core_capabilities", []),
                "workflow_steps": bs.get("workflow_steps", []),
                "integrations": bs.get("integrations", []),
            },
            "tech_stack": {
                "llm": bs.get("suggested_tech_stack", {}).get("llm", ""),
                "orchestration": bs.get("suggested_tech_stack", {}).get("orchestration", ""),
                "database": bs.get("suggested_tech_stack", {}).get("database", ""),
                "integrations": bs.get("suggested_tech_stack", {}).get("integrations", []),
                "build_complexity": bs.get("build_complexity", ""),
                "estimated_days": bs.get("estimated_build_days", ""),
            },
            "source_urls": source_urls,  # Add source URLs
        }
        if pg_store.upsert_agent(agent_data):
            print(f"  [PostgreSQL] ✓ Agent stored in database")
            print(f"  [PostgreSQL] ✓ Stored {len(source_urls)} source URLs")
        else:
            print(f"  [PostgreSQL] ✗ Failed to store agent in database")

    # Generate Word doc (pure Python — no Node.js needed)
    docx_path = save_as_docx(build_spec, output_dir, requirement)

    return spec_path, docx_path


# ─────────────────────────────── Main ────────────────────────────────

def main():
    _sel = ("ON ✓" if ENABLE_SELENIUM and SELENIUM_AVAILABLE else
            "OFF (requests+BS4 fallback)")

    print(f"\n{'='*58}")
    print(f"  CLIENT REQUIREMENT RESEARCH AGENT")
    print(f"  Model    : {GROQ_MODEL}")
    print(f"  Selenium : {_sel}")
    print(f"  Platforms: {len(COMPETITOR_SEARCHES)} competitors")
    print(f"{'='*58}\n")

    # Get requirement — from CLI arg or interactive prompt
    if len(sys.argv) > 1:
        requirement = " ".join(sys.argv[1:]).strip()
    else:
        requirement = input("Enter client requirement: ").strip()

    if not requirement:
        print("[ERROR] No requirement entered. Exiting.")
        sys.exit(1)

    update_status(f"starting — requirement: {requirement}")

    # Step 1: Research competitors (Two-Tier: ZBrain → DuckDuckGo+LLM fallback)
    update_status("researching agents (tier 1: zbrain → tier 2: ddg+llm)")
    raw_data = research_requirement_hybrid(requirement)

    # Step 2 (NEW): Index this run's findings into FAISS, then retrieve
    #               relevant past context for the LLM prompt
    past_context = ""
    if RAG_ENABLED:
        update_status("indexing findings into FAISS RAG store")
        rag_store.upsert(requirement, raw_data["findings"])

        update_status("querying FAISS RAG store for past context")
        past_context = rag_store.query(requirement)
        if past_context:
            print(f"[{BOT_NAME}] RAG: injecting past context into prompt "
                  f"({len(past_context)} chars)")
        else:
            print(f"[{BOT_NAME}] RAG: no relevant past context found "
                  f"(index may be new).")

    # Step 3: LLM analysis (with RAG context if available)
    update_status("analysing")
    build_spec = analyse(requirement, raw_data["findings"], past_context)

    # Step 3: Save JSON + Word doc
    update_status("saving")
    spec_path, docx_path = save_outputs(requirement, raw_data, build_spec)

    update_status("done")
    if docx_path:
        print(f"\n[{BOT_NAME}] Done! Open your Word doc: {docx_path}\n")
    else:
        print(f"\n[{BOT_NAME}] Done! Open: {spec_path}\n")

    # Console summary
    if "build_spec" in build_spec:
        bs = build_spec["build_spec"]
        print(f"  Agent      : {bs.get('agent_name', '?')}")
        print(f"  Purpose    : {bs.get('purpose', '?')}")
        print(f"  Complexity : {bs.get('build_complexity', '?')} "
              f"(~{bs.get('estimated_build_days', '?')} days)")
        caps = bs.get("core_capabilities", [])
        if caps:
            print(f"  Capabilities ({len(caps)}):")
            for c in caps[:5]:
                print(f"    • {c.get('capability', '')}")


if __name__ == "__main__":
    main()