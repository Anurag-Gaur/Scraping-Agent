"""
seed_postgres.py — Load existing agent data into PostgreSQL
═════════════════════════════════════════════════════════════════════════
Walks Data/research_output/ and loads all build_spec.json files
into the Railway PostgreSQL 'agent' table.

Run once to migrate existing data:
  python seed_postgres.py

This reads from local build_spec.json files and populates the PostgreSQL
database with agent name, description, features, and tech_stack.
"""

import os
import sys
import json

# ── Add parent directory to path for imports ───────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from database import pg_store

OUTPUT_BASE = "Data/research_output"


def extract_agent_data(build_spec_path: str) -> dict:
    """
    Extract agent data from a build_spec.json file.
    
    Parameters
    ----------
    build_spec_path : str
        Path to build_spec.json
        
    Returns
    -------
    dict with keys: agent_name, description, features, tech_stack, source_urls
    """
    try:
        with open(build_spec_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"    [error] Failed to read {build_spec_path}: {e}")
        return None
    
    build_spec = data.get("build_spec", {})
    
    # Extract agent name
    agent_name = build_spec.get("agent_name", "Unknown Agent")
    
    # Extract description
    description = build_spec.get("purpose", "")
    
    # Extract features (core_capabilities)
    core_capabilities = build_spec.get("core_capabilities", [])
    features = {
        "capabilities": core_capabilities,
        "workflow_steps": build_spec.get("workflow_steps", []),
        "integrations": build_spec.get("integrations", []),
    }
    
    # Extract tech stack
    tech_stack_raw = build_spec.get("suggested_tech_stack", {})
    tech_stack = {
        "llm": tech_stack_raw.get("llm", ""),
        "orchestration": tech_stack_raw.get("orchestration", ""),
        "database": tech_stack_raw.get("database", ""),
        "integrations": tech_stack_raw.get("integrations", []),
        "build_complexity": build_spec.get("build_complexity", ""),
        "estimated_days": build_spec.get("estimated_build_days", ""),
    }
    
    # Try to extract source URLs from raw_competitor_data.json
    source_urls = []
    build_dir = os.path.dirname(build_spec_path)
    raw_data_path = os.path.join(build_dir, "raw_competitor_data.json")
    if os.path.exists(raw_data_path):
        try:
            with open(raw_data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                pages = raw_data.get("pages_scraped", [])
                source_urls = list(set([
                    page.get("url") for page in pages
                    if page.get("url") and page.get("quality") != "poor"
                ]))
        except Exception as e:
            print(f"    [warn] Could not extract URLs from raw_competitor_data.json: {e}")
    
    return {
        "agent_name": agent_name,
        "description": description,
        "features": features,
        "tech_stack": tech_stack,
        "source_urls": source_urls,
    }


def main():
    """Main seeding function."""
    if not os.path.isdir(OUTPUT_BASE):
        print(f"[seed_postgres] '{OUTPUT_BASE}' not found — nothing to seed.")
        return
    
    # Create table first
    print("[seed_postgres] Creating table schema...")
    pg_store.create_table()
    print()
    
    # Find all agent directories
    agent_dirs = [
        d for d in os.listdir(OUTPUT_BASE)
        if os.path.isdir(os.path.join(OUTPUT_BASE, d))
    ]
    
    if not agent_dirs:
        print("[seed_postgres] No agent folders found under Data/research_output/")
        return
    
    print(f"[seed_postgres] Found {len(agent_dirs)} agent folder(s)\n")
    
    total_loaded = 0
    total_failed = 0
    
    for agent_dir in sorted(agent_dirs):
        spec_path = os.path.join(OUTPUT_BASE, agent_dir, "build_spec.json")
        
        if not os.path.exists(spec_path):
            print(f"  [skip] {agent_dir}/ — no build_spec.json")
            continue
        
        print(f"  [load] {agent_dir}/")
        
        # Extract agent data from build_spec.json
        agent_data = extract_agent_data(spec_path)
        
        if not agent_data:
            print(f"         ✗ Failed to extract data")
            total_failed += 1
            continue
        
        # Insert into PostgreSQL
        success = pg_store.upsert_agent(agent_data)
        
        if success:
            total_loaded += 1
        else:
            total_failed += 1
    
    print()
    print(f"[seed_postgres] ✓ Seeding complete!")
    print(f"                 • Loaded: {total_loaded}")
    print(f"                 • Failed: {total_failed}")
    
    # Show stats
    stats = pg_store.stats()
    print(f"\n[seed_postgres] Database stats:")
    print(f"                 • Total agents in DB: {stats['total_agents']}")


if __name__ == "__main__":
    main()
