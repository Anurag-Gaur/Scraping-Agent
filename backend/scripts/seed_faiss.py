"""
seed_faiss.py — One-time backfill for the FAISS RAG store & PostgreSQL
════════════════════════════════════════════════════════════════════════
Walks every folder under Data/research_output/ and:
  1. Indexes all raw_competitor_data.json files into the FAISS store
  2. Stores agent build specs in Railway PostgreSQL

Run once after adding rag_store.py to an existing project:
  python seed_faiss.py

After this, research_bot.py will automatically keep both stores
up to date on every new run.
"""

import os
import sys
import json

# ── Add parent directory to path for imports ───────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core import rag_store
from database import pg_store

OUTPUT_BASE = "Data/research_output"

def load_findings(raw_path: str) -> dict:
    """
    raw_competitor_data.json can be stored in two shapes:
      Shape A (new): {"requirement": "...", "findings": {...}, "pages_scraped": [...], ...}
      Shape B (old): {"platform": "scraped text", ...}

    'findings' only contains pages rated ok/good quality.
    When it is empty we fall back to 'pages_scraped' which stores every
    page regardless of quality rating — filtering out hard failures only.

    Returns a {platform_label: text} dict.
    """
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return {}

    # Shape A — try findings first
    findings = data.get("findings", {})
    if findings:
        return findings

    # findings is empty — fall back to pages_scraped
    pages = data.get("pages_scraped", [])
    if pages:
        recovered = {}
        skipped   = 0
        for page in pages:
            text  = page.get("text", "")
            label = page.get("label") or page.get("platform", "unknown")
            # Skip hard scrape failures (no useful text at all)
            if not text or text.startswith("[scrape failed") or text.startswith("[selenium failed"):
                skipped += 1
                continue
            if len(text) < 80:
                skipped += 1
                continue
            # Merge multiple pages from same platform under one key
            if label in recovered:
                recovered[label] += "\n\n---\n\n" + text
            else:
                recovered[label] = text
        print(f"    [fallback] pages_scraped: {len(recovered)} usable pages, {skipped} skipped")
        return recovered

    # Shape B — flat dict of platform → text (older format)
    return {k: v for k, v in data.items()
            if isinstance(v, str) and len(v) > 80}


def main():
    if not os.path.isdir(OUTPUT_BASE):
        print(f"[seed] '{OUTPUT_BASE}' not found — nothing to seed.")
        return

    slugs = [d for d in os.listdir(OUTPUT_BASE)
             if os.path.isdir(os.path.join(OUTPUT_BASE, d))]

    if not slugs:
        print("[seed] No requirement folders found under Data/research_output/")
        return

    print(f"[seed] Found {len(slugs)} requirement folder(s): {slugs}\n")
    
    # Create PostgreSQL table on first run
    print("[seed] Setting up PostgreSQL table...")
    pg_store.create_table()
    print()

    total_added = 0
    pg_agents_added = 0

    for slug in slugs:
        raw_path = os.path.join(OUTPUT_BASE, slug, "raw_competitor_data.json")
        spec_path = os.path.join(OUTPUT_BASE, slug, "build_spec.json")
        
        if not os.path.exists(raw_path):
            print(f"  [skip] {slug}/ — no raw_competitor_data.json")
            continue

        # Try to get the human-readable requirement name from build_spec.json
        requirement = slug.replace("_", " ")   # fallback
        if os.path.exists(spec_path):
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    spec = json.load(f)
                requirement = spec.get("requirement", requirement)
            except Exception:
                pass

        print(f"  → Seeding: '{requirement}' (folder: {slug}/)")
        
        # ─── FAISS SEEDING ─────────────────────────────────────────────
        findings = load_findings(raw_path)

        if not findings:
            print(f"    [warn] findings dict is empty — skipping FAISS")
        else:
            platforms = list(findings.keys())
            total_text = sum(len(v) for v in findings.values() if isinstance(v, str))
            print(f"    [FAISS] platforms : {platforms}")
            print(f"    [FAISS] total text: {total_text:,} chars")

            added = rag_store.upsert(requirement, findings)
            total_added += added
            print(f"    [FAISS] chunks added: {added}")
        
        # ─── PostgreSQL SEEDING ────────────────────────────────────────
        if os.path.exists(spec_path):
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                build_spec = data.get("build_spec", {})
                
                # Extract agent data
                agent_data = {
                    "agent_name": build_spec.get("agent_name", "Unknown Agent"),
                    "description": build_spec.get("purpose", ""),
                    "features": {
                        "capabilities": build_spec.get("core_capabilities", []),
                        "workflow_steps": build_spec.get("workflow_steps", []),
                        "integrations": build_spec.get("integrations", []),
                    },
                    "tech_stack": {
                        "llm": build_spec.get("suggested_tech_stack", {}).get("llm", ""),
                        "orchestration": build_spec.get("suggested_tech_stack", {}).get("orchestration", ""),
                        "database": build_spec.get("suggested_tech_stack", {}).get("database", ""),
                        "integrations": build_spec.get("suggested_tech_stack", {}).get("integrations", []),
                        "build_complexity": build_spec.get("build_complexity", ""),
                        "estimated_days": build_spec.get("estimated_build_days", ""),
                    },
                }
                
                if pg_store.upsert_agent(agent_data):
                    pg_agents_added += 1
                print(f"    [PG] Agent stored: {agent_data['agent_name']}")
                
            except Exception as e:
                print(f"    [PG] Error storing agent: {e}")
        
        print()

    # ── Final stats ────────────────────────────────────────────────────
    print("═" * 70)
    s = rag_store.stats()
    pg_stats = pg_store.stats()
    print(f"  Seeding complete!")
    print(f"\n  FAISS Vector Store:")
    print(f"    • New chunks added   : {total_added}")
    print(f"    • Total in store     : {s['total_chunks']}")
    print(f"    • Requirements       : {s['unique_requirements']}")
    print(f"    • Platforms          : {len(s['platforms'])}")
    print(f"    • Store location     : {s['store_dir']}")
    print(f"\n  PostgreSQL Agent Store:")
    print(f"    • Agents added       : {pg_agents_added}")
    print(f"    • Total in database  : {pg_stats['total_agents']}")
    print("═" * 70)

    if s["total_chunks"] == 0:
        print("\n[warn] FAISS store is still empty after seeding.")
        print("  Most likely cause: all scraped pages were 'poor' quality")
        print("  and stored as empty strings in raw_competitor_data.json.")
        print("  Run research_bot.py again — if scraping succeeds this time,")
        print("  findings will be indexed automatically.")


if __name__ == "__main__":
    main()
