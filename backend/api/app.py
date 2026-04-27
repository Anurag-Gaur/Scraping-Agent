"""
api/app.py — REST API Server for Agent Search + Web Scraper Integration

Architecture:
  User Query → Check PostgreSQL
             ├─ Found? → Return agent(s) ✓
             └─ Not found? → Trigger web scraper
                          → Save to PostgreSQL
                          → Return results

Usage:
  python api/app.py
  → Server runs on http://localhost:5000
  → Frontend connects to this server
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import core modules
from database import pg_store
from core import research_bot, zbrain_scraper

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Initialize database
try:
    pg_store.create_table()
    print("[api] ✓ PostgreSQL connected and ready")
except Exception as e:
    print(f"[api] WARNING: PostgreSQL initialization failed: {e}")


# ────────────────────────────── API Routes ─────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "message": "API server is running"}), 200


@app.route("/api/agents/search", methods=["GET"])
def search_agents():
    """
    Search for agents by name or requirement.
    
    Query params:
      - query: Search term (required)
      - search_type: "name" | "requirement" | "all" (default: "all")
    
    Returns:
      - agents: List of matching agents
      - source: "database" | "scraper"
      - total: Number of results
    """
    query = request.args.get("query", "").strip()
    search_type = request.args.get("search_type", "all").lower()

    if not query:
        return jsonify({"error": "query parameter is required"}), 400

    print(f"\n[api] 🔍 Search request: '{query}' (type: {search_type})")

    # ── Step 1: Search PostgreSQL ────────────────────────────────────────
    print(f"[api] Step 1: Checking PostgreSQL...")
    db_agents = search_database(query, search_type)

    if db_agents:
        print(f"[api] ✓ Found {len(db_agents)} agent(s) in database")
        return jsonify({
            "success": True,
            "agents": db_agents,
            "source": "database",
            "total": len(db_agents),
            "message": f"Found {len(db_agents)} agent(s) in database"
        }), 200

    # ── Step 2: If not found, trigger web scraper ────────────────────────
    print(f"[api] ~ Not found in database, triggering web scraper...")
    scraped_result = scrape_and_save(query, search_type)

    if scraped_result["success"]:
        print(f"[api] ✓ Scraper found {len(scraped_result['agents'])} agent(s)")
        return jsonify({
            "success": True,
            "agents": scraped_result["agents"],
            "source": "scraper",
            "total": len(scraped_result["agents"]),
            "message": f"Scraped {len(scraped_result['agents'])} agent(s) from web and saved to database"
        }), 200
    else:
        print(f"[api] ✗ Scraper failed or no results found")
        return jsonify({
            "success": False,
            "agents": [],
            "source": None,
            "total": 0,
            "message": "No agents found in database or web scraper"
        }), 404


@app.route("/api/agents/all", methods=["GET"])
def list_all_agents():
    """List all agents in database."""
    print(f"\n[api] 📋 Listing all agents...")
    try:
        agents = pg_store.get_all_agents()
        return jsonify({
            "success": True,
            "agents": agents,
            "total": len(agents)
        }), 200
    except Exception as e:
        print(f"[api] ERROR: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/agents/<int:agent_id>", methods=["GET"])
def get_agent_details(agent_id):
    """Get agent by ID."""
    print(f"\n[api] 🔍 Getting agent ID: {agent_id}")
    try:
        agent = pg_store.get_agent_by_id(agent_id)
        if agent:
            return jsonify({"success": True, "agent": agent}), 200
        else:
            return jsonify({"success": False, "error": "Agent not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/agents/name/<agent_name>", methods=["GET"])
def get_agent_by_name(agent_name):
    """Get agent by exact name match."""
    print(f"\n[api] 🔍 Getting agent: {agent_name}")
    try:
        agent = pg_store.get_agent_by_name(agent_name)
        if agent:
            return jsonify({"success": True, "agent": agent}), 200
        else:
            return jsonify({"success": False, "error": "Agent not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/agents/scrape", methods=["POST"])
def scrape_requirement():
    """
    Manually trigger web scraper for a requirement.
    
    Body:
      - requirement: What to scrape for (required)
    
    Returns:
      - agent_name: Generated agent name
      - status: "completed" | "error"
    """
    data = request.get_json() or {}
    requirement = data.get("requirement", "").strip()

    if not requirement:
        return jsonify({"error": "requirement field is required"}), 400

    print(f"\n[api] 🌐 Manual scrape triggered: '{requirement}'")

    try:
        result = scrape_and_save(requirement, "requirement")
        if result["success"]:
            return jsonify({
                "success": True,
                "requirement": requirement,
                "agents_found": len(result["agents"]),
                "agents": result["agents"],
                "message": f"Successfully scraped and saved {len(result['agents'])} agent(s)"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Scraper failed or found no results"
            }), 500
    except Exception as e:
        print(f"[api] ERROR: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/agents/stats", methods=["GET"])
def get_stats():
    """Get database statistics."""
    print(f"\n[api] 📊 Getting database stats...")
    try:
        stats = pg_store.stats()
        return jsonify({"success": True, "stats": stats}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ────────────────────────── Helper Functions ────────────────────────────

def search_database(query: str, search_type: str) -> list:
    """
    Search PostgreSQL for agents.
    
    Args:
        query: Search term
        search_type: "name" | "requirement" | "all"
    
    Returns:
        List of matching agents
    """
    try:
        all_agents = pg_store.get_all_agents()

        if not all_agents:
            return []

        query_lower = query.lower()
        matches = []

        for agent in all_agents:
            match_score = 0

            # Name search
            if search_type in ["name", "all"]:
                if query_lower in agent.get("agent_name", "").lower():
                    match_score += 10  # Name matches are higher priority

            # Requirement / description search
            if search_type in ["requirement", "all"]:
                desc = agent.get("description", "").lower()
                features = json.dumps(agent.get("features", {})).lower() if agent.get("features") else ""
                tech = json.dumps(agent.get("tech_stack", {})).lower() if agent.get("tech_stack") else ""

                if query_lower in desc or query_lower in features or query_lower in tech:
                    match_score += 5

            if match_score > 0:
                matches.append({
                    "id": agent.get("id"),
                    "agent_name": agent.get("agent_name"),
                    "description": agent.get("description"),
                    "features": agent.get("features"),
                    "tech_stack": agent.get("tech_stack"),
                    "agent_url": agent.get("agent_url"),
                    "match_score": match_score
                })

        # Sort by match score
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        return matches

    except Exception as e:
        print(f"[api] ERROR searching database: {e}")
        return []


def scrape_and_save(query: str, search_type: str) -> dict:
    """
    Trigger web scraper and save results to database.
    
    Args:
        query: What to scrape for
        search_type: "name" | "requirement" | "all"
    
    Returns:
        {"success": bool, "agents": list}
    """
    try:
        # Run hybrid research (ZBrain + DuckDuckGo)
        print(f"[api] Scraping: '{query}'...")
        raw_data = research_bot.research_requirement_hybrid(query)

        # Analyze with LLM
        print(f"[api] Analyzing with LLM...")
        findings = raw_data.get("findings", {})
        past_context = ""  # Could use RAG here if needed
        build_spec = research_bot.analyse(query, findings, past_context)

        # Extract agent data
        if "build_spec" in build_spec:
            bs = build_spec["build_spec"]
            agent_data = {
                "agent_name": bs.get("agent_name", "Unknown Agent"),
                "description": bs.get("purpose", ""),
                "features": bs.get("core_capabilities", []),
                "tech_stack": bs.get("suggested_tech_stack", {}),
                "source_urls": raw_data.get("zbrain_agents", [])
                    if raw_data.get("zbrain_agents")
                    else [page.get("url") for page in raw_data.get("pages_scraped", []) if page.get("url")]
            }

            # Save to PostgreSQL
            print(f"[api] Saving to PostgreSQL: {agent_data['agent_name']}")
            pg_store.upsert_agent(agent_data)

            return {
                "success": True,
                "agents": [agent_data]
            }
        else:
            return {
                "success": False,
                "agents": [],
                "error": "LLM analysis failed"
            }

    except Exception as e:
        print(f"[api] ERROR in scrape_and_save: {e}")
        return {
            "success": False,
            "agents": [],
            "error": str(e)
        }


# ────────────────────────────── Error Handlers ────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ────────────────────────────── Main ────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  AGENT SEARCH API SERVER")
    print("="*70)
    print("\n[api] Starting server...")
    print("[api] Database: Railway PostgreSQL")
    print("[api] Scraper: ZBrain + DuckDuckGo + LLM")
    print("\n[api] API Endpoints:")
    print("  GET  /api/health                    - Health check")
    print("  GET  /api/agents/search?query=...   - Search by name/requirement")
    print("  GET  /api/agents/all                - List all agents")
    print("  GET  /api/agents/<id>               - Get agent by ID")
    print("  GET  /api/agents/name/<name>        - Get agent by name")
    print("  POST /api/agents/scrape             - Trigger scraper")
    print("  GET  /api/agents/stats              - Database statistics")
    print("\n[api] Frontend can connect to: http://localhost:5000")
    print("="*70 + "\n")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )
