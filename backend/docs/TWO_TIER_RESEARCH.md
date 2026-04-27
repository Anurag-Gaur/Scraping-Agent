## Parallel Research System (ZBrain + DuckDuckGo + Competitors)

Your research_bot now uses an intelligent parallel approach to find comprehensive agent blueprints:

### How It Works

```
1️⃣  Tier 1: ZBrain Agent Scraper (Parallel)
    ├─ Scrapes zbrain.ai/agents/ catalog
    ├─ Finds agents matching your requirement
    └─ If found → adds to results (doesn't stop)
    
2️⃣  Tier 2: DuckDuckGo + Competitors (Parallel)
    ├─ Searches 10+ competitor platforms
    ├─ Scrapes competitor implementations
    ├─ Uses Groq LLM to synthesize blueprint
    └─ Always runs (adds to ZBrain results if available)

📊 Result: COMBINED findings from BOTH sources
```

### Key Difference

**Old approach (Sequential/Fallback):**
- Try ZBrain
- If successful → return (stop searching)
- If failed → fall back to DuckDuckGo

**New approach (Parallel/Combined):**
- Run ZBrain scraper AND DuckDuckGo simultaneously
- Always get both ZBrain agents AND competitor analysis
- Merge all findings into one comprehensive report

### Example Flow

```
$ python run.py "Accounts Payable Agent"

[research_bot] Research Strategy: Parallel (ZBrain + DuckDuckGo + Competitors)

[Parallel] Searching ZBrain Agent Store...
├─ [ZBrain] Found 5 matching agents ✓
│   └─ Added to findings

[Parallel] Searching competitor platforms via DuckDuckGo...
├─ [DuckDuckGo] Scraped 15 competitor pages ✓
│   ├─ zbrain: 3 pages
│   ├─ crewai: 3 pages
│   ├─ make: 2 pages
│   └─ others: 7 pages
│   └─ Added to findings

[research_bot] Combined Research Complete
├─ Sources: zbrain + ddg_competitors
├─ ZBrain agents: 5
└─ Competitor pages: 15

Output: COMPREHENSIVE agent blueprint based on:
├─ Direct ZBrain specifications (5 agents)
└─ Competitor analysis (15 pages from 10 platforms)
```

This gives you:
- ✅ Actual agent specifications from ZBrain
- ✅ How competitors implement similar agents
- ✅ LLM synthesis combining both perspectives
- ✅ More comprehensive, accurate build spec

### Installation Requirements

For Tier 1 (ZBrain scraper) to work, install Playwright:

```bash
pip install playwright
playwright install
```

**Note:** The first run will take ~5 minutes (downloads chromium). Subsequent runs use cached data.

If Playwright is not installed, Tier 1 is automatically skipped and system falls back to Tier 2.

### Output Files (Same as Before)

Both tiers save to the same location:
```
Data/research_output/<requirement_slug>/
  ├── scrape_source.json        ← Scraped data (with URLs)
  ├── build_spec.json           ← LLM-generated blueprint
  ├── raw_competitor_data.json  ← Full scraped text
  └── Agent_<name>.docx         ← Word document
```

### Configuration

**Default Behavior:**
- Always attempts Tier 1 (ZBrain) first
- Falls back to Tier 2 (DuckDuckGo+LLM) if insufficient results
- Threshold: If <1 matching agents found in ZBrain

**To force specific tier:**

```python
# Force Tier 1 only (ZBrain)
from core import zbrain_scraper
agents = zbrain_scraper.scrape_zbrain_agents("requirement")

# Force Tier 2 only (DuckDuckGo+LLM)
from core import research_bot
raw_data = research_bot.research_requirement("requirement")
```

### Key Files

| File | Purpose |
|------|---------|
| `core/zbrain_scraper.py` | Playwright-based ZBrain agent store scraper |
| `core/research_bot.py` | Modified to use two-tier research |
| `run.py` | Main entry point (unchanged) |

### Workflow

```
research_bot.py / run.py
    │
    ├─→ research_requirement_hybrid()
    │       │
    │       ├─→ [PARALLEL] Tier 1: zbrain_scraper.scrape_zbrain_agents()
    │       │        ├─ discover_agent_urls()
    │       │        ├─ scrape_agent_summary() for each agent
    │       │        └─ filter_agents_by_requirement()
    │       │
    │       ├─→ [PARALLEL] Tier 2: research_requirement()
    │       │        ├─ ddg_search() × 10 platforms
    │       │        ├─ smart_scrape() for each result
    │       │        └─ [saves pages_scraped data]
    │       │
    │       └─→ MERGE results (ZBrain agents + DuckDuckGo findings)
    │
    ├─→ RAG indexing (FAISS)
    │
    ├─→ analyse() [LLM synthesis with both sources]
    │
    └─→ save_outputs()
```

### Performance Notes

**Parallel execution (both tiers run simultaneously):**
- **ZBrain scraping:** ~2-3 minutes first run, <10 seconds cached
- **DuckDuckGo scraping:** ~3-5 minutes (10+ platforms)
- **LLM analysis:** ~1-2 minutes
- **Total (parallel):** ~4-6 minutes (not 5-8, thanks to parallelization)

**Speed benefits:**
- Running both tiers in parallel is faster than running them sequentially
- Cached ZBrain data makes subsequent runs much faster
- Even with both sources, total time is reasonable

### Troubleshooting

**"PlaywrightTimeout" errors?**
→ Increase timeout in `zbrain_scraper.py` line ~92:
```python
def scrape_zbrain_agents(..., timeout: int = 20000):  # ← increase this
```

**Cache not working?**
→ Clear cache and re-scrape:
```bash
rm Data/zbrain_cache.json
python run.py "requirement"
```

**Want to use only Tier 1?**
→ Set environment variable:
```bash
set RESEARCH_TIER=zbrain_only
python run.py "requirement"
```

### What's New

✅ **Parallel Research** — Both ZBrain + DuckDuckGo run simultaneously
✅ **Comprehensive Results** — Get agents from ZBrain + competitor analysis
✅ **More Accurate LLM Input** — Groq has both specs and implementations to synthesize from
✅ **Better Coverage** — No single point of failure
✅ **Same output format** — No changes to downstream pipeline
✅ **Backward compatible** — Works with existing research_bot workflow
✅ **Efficient** — Parallel execution doesn't increase total time much

### Architecture

```
zbrain_scraper.py
├─ scrape_zbrain_agents()        ← Main entry point
├─ discover_agent_urls()         ← Find all agents
├─ scrape_agent_summary()        ← Extract details
├─ filter_agents_by_requirement()← Keyword matching
└─ format_agent_for_research()   ← Display formatting
```

### Caching Strategy

ZBrain cache is stored in: `Data/zbrain_cache.json`

- ✓ Speeds up repeated requirements
- ✓ Reduces load on zbrain.ai
- ✓ Works offline (after first run)
- ⚠ Can become stale (manually delete to refresh)

### Example Usage Patterns

**Single requirement:**
```bash
python run.py "Accounts Payable Agent"
```

**Multiple requirements (in loop):**
```bash
python run.py "Invoice Processing Agent"
python run.py "Procurement Agent"
python run.py "Financial Close Agent"
```

**From Python code (parallel combined):**
```python
from core import research_bot
result = research_bot.research_requirement_hybrid("Your Requirement")
print(f"Sources used: {', '.join(result['tier_used'])}")
print(f"ZBrain agents: {len(result.get('zbrain_agents', []))}")
print(f"Competitor pages: {len(result.get('pages_scraped', []))}")
```

**Or use only ZBrain (faster):**
```python
from core import zbrain_scraper
agents = zbrain_scraper.scrape_zbrain_agents("requirement")
matching = zbrain_scraper.filter_agents_by_requirement(agents, "requirement")
print(f"Found {len(matching)} matching agents")
```

**Or use only competitors (traditional):**
```python
from core import research_bot
result = research_bot.research_requirement("requirement")
print(f"Found {len(result['pages_scraped'])} competitor pages")
```

---

**Questions or issues?** Check:
- `docs/README_POSTGRES.md` — Setup
- `docs/TROUBLESHOOTING_POSTGRES.py` — Common issues
- `STRUCTURE.md` — Project layout
