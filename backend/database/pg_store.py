"""
pg_store.py — PostgreSQL agent storage
═══════════════════════════════════════════════════════════════════════
Stores agent build specifications in Railway PostgreSQL database.

USAGE
─────
  import pg_store
  pg_store.create_table()                           # one-time setup
  pg_store.upsert_agent(agent_data)                 # save agent
  agent = pg_store.get_agent_by_name("Agent Name")  # retrieve agent
  all_agents = pg_store.get_all_agents()            # list all agents

TABLE SCHEMA
────────────
  agent (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    features JSONB,
    tech_stack JSONB,
    agent_url VARCHAR(2048),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )

DATABASE URL
─────────────
  postgresql://postgres:PASSWORD@nozomi.proxy.rlwy.net:59367/railway

REQUIREMENTS
─────────────
  pip install psycopg2-binary
"""

import os
import json
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

# Module-level connection singleton
_connection = None


# ─────────────────────── URL Generation ───────────────────────────── #

def _slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def _generate_agent_url(agent_name: str) -> str:
    """Generate a standard API URL for an agent."""
    slug = _slugify(agent_name)
    return f"/api/agents/{slug}/"


def _get_connection():
    """Get or create database connection."""
    global _connection
    
    if _connection is not None:
        return _connection
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        raise ImportError(
            "psycopg2-binary not installed. "
            "Run: pip install psycopg2-binary"
        )
    
    # Get connection string from environment or use provided URL
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:YRMdDKECisuzTCHtDzgUlimEziCAGRIp@nozomi.proxy.rlwy.net:59367/railway"
    )
    
    try:
        _connection = psycopg2.connect(db_url)
        print("[pg_store] ✓ Connected to PostgreSQL")
        return _connection
    except Exception as e:
        raise Exception(f"[pg_store] Failed to connect to database: {e}")


def _close_connection():
    """Close the database connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def create_table():
    """Create the agent table if it doesn't exist, and add missing columns."""
    import psycopg2
    
    conn = _get_connection()
    cursor = conn.cursor()
    
    try:
        # Create table with all required columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent (
                id SERIAL PRIMARY KEY,
                agent_name VARCHAR(255) UNIQUE NOT NULL,
                description TEXT,
                features JSONB,
                tech_stack JSONB,
                agent_url VARCHAR(2048),
                source_urls JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Add source_urls column if it doesn't exist (for backward compatibility)
        cursor.execute("""
            ALTER TABLE agent
            ADD COLUMN IF NOT EXISTS source_urls JSONB;
        """)
        
        # Create index on agent_name for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_name 
            ON agent(agent_name);
        """)
        
        conn.commit()
        print("[pg_store] ✓ Table 'agent' created/verified")
        return True
        
    except psycopg2.Error as e:
        conn.rollback()
        print(f"[pg_store] ✗ Error creating table: {e}")
        return False
    finally:
        cursor.close()


def upsert_agent(agent_data: Dict[str, Any]) -> bool:
    """
    Insert or update an agent record.
    
    Parameters
    ----------
    agent_data : dict
        Must contain keys: agent_name
        Optional: description, features, tech_stack, agent_url, source_urls
        If agent_url is not provided, it will be auto-generated from agent_name
        source_urls should be a list of URLs where data was scraped from
        
    Returns
    -------
    bool  True if successful, False otherwise.
    """
    import psycopg2
    import psycopg2.extras
    
    if not agent_data.get("agent_name"):
        print("[pg_store] ✗ Missing required field: agent_name")
        return False
    
    conn = _get_connection()
    cursor = conn.cursor()
    
    try:
        # Convert features and tech_stack to JSON if they're dicts
        features = agent_data.get("features")
        if isinstance(features, dict):
            features = json.dumps(features)
        elif isinstance(features, str):
            features = json.dumps(json.loads(features))  # validate JSON
        
        tech_stack = agent_data.get("tech_stack")
        if isinstance(tech_stack, dict):
            tech_stack = json.dumps(tech_stack)
        elif isinstance(tech_stack, str):
            tech_stack = json.dumps(json.loads(tech_stack))  # validate JSON
        
        # Handle source_urls (list of URLs where data came from)
        source_urls = agent_data.get("source_urls", [])
        if isinstance(source_urls, list):
            source_urls = json.dumps(source_urls)
        elif isinstance(source_urls, str):
            source_urls = json.dumps(json.loads(source_urls))  # validate JSON
        
        # Generate URL if not provided
        agent_url = agent_data.get("agent_url") or _generate_agent_url(agent_data.get("agent_name"))
        
        # UPSERT: insert or update on conflict
        cursor.execute("""
            INSERT INTO agent (agent_name, description, features, tech_stack, agent_url, source_urls)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (agent_name) 
            DO UPDATE SET
                description = EXCLUDED.description,
                features = EXCLUDED.features,
                tech_stack = EXCLUDED.tech_stack,
                agent_url = EXCLUDED.agent_url,
                source_urls = EXCLUDED.source_urls,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
        """, (
            agent_data.get("agent_name"),
            agent_data.get("description"),
            features,
            tech_stack,
            agent_url,
            source_urls
        ))
        
        agent_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"[pg_store] ✓ Upserted agent (ID: {agent_id}, Name: {agent_data.get('agent_name')}, URL: {agent_url})")
        return True
        
    except psycopg2.Error as e:
        conn.rollback()
        print(f"[pg_store] ✗ Error upserting agent: {e}")
        return False
    finally:
        cursor.close()


def get_agent_by_name(agent_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve an agent by name.
    
    Parameters
    ----------
    agent_name : str  The name of the agent to retrieve.
    
    Returns
    -------
    dict or None  Agent data if found, None otherwise.
    """
    import psycopg2.extras
    
    conn = _get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT id, agent_name, description, features, tech_stack, agent_url, 
                   created_at, updated_at
            FROM agent
            WHERE agent_name = %s;
        """, (agent_name,))
        
        result = cursor.fetchone()
        if result:
            return dict(result)
        return None
        
    except Exception as e:
        print(f"[pg_store] ✗ Error retrieving agent: {e}")
        return None
    finally:
        cursor.close()


def get_agent_by_id(agent_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve an agent by ID.
    
    Parameters
    ----------
    agent_id : int  The ID of the agent to retrieve.
    
    Returns
    -------
    dict or None  Agent data if found, None otherwise.
    """
    import psycopg2.extras
    
    conn = _get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT id, agent_name, description, features, tech_stack, agent_url,
                   created_at, updated_at
            FROM agent
            WHERE id = %s;
        """, (agent_id,))
        
        result = cursor.fetchone()
        if result:
            return dict(result)
        return None
        
    except Exception as e:
        print(f"[pg_store] ✗ Error retrieving agent: {e}")
        return None
    finally:
        cursor.close()


def get_all_agents() -> List[Dict[str, Any]]:
    """
    Retrieve all agents from the database.
    
    Returns
    -------
    list  List of agent dicts, or empty list if none found.
    """
    import psycopg2.extras
    
    conn = _get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT id, agent_name, description, features, tech_stack, agent_url,
                   created_at, updated_at
            FROM agent
            ORDER BY created_at DESC;
        """)
        
        results = cursor.fetchall()
        return [dict(row) for row in results]
        
    except Exception as e:
        print(f"[pg_store] ✗ Error retrieving agents: {e}")
        return []
    finally:
        cursor.close()


def delete_agent(agent_name: str) -> bool:
    """
    Delete an agent by name.
    
    Parameters
    ----------
    agent_name : str  The name of the agent to delete.
    
    Returns
    -------
    bool  True if successful, False otherwise.
    """
    import psycopg2
    
    conn = _get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM agent WHERE agent_name = %s;", (agent_name,))
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"[pg_store] ✓ Deleted agent: {agent_name}")
            return True
        else:
            print(f"[pg_store] ℹ Agent not found: {agent_name}")
            return False
            
    except psycopg2.Error as e:
        conn.rollback()
        print(f"[pg_store] ✗ Error deleting agent: {e}")
        return False
    finally:
        cursor.close()


def stats() -> Dict[str, Any]:
    """Return summary statistics about the agent store."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM agent;")
        total_agents = cursor.fetchone()[0]
        
        return {
            "total_agents": total_agents,
            "database": "PostgreSQL (Railway)",
            "table": "agent",
        }
        
    except Exception as e:
        print(f"[pg_store] ✗ Error getting stats: {e}")
        return {"error": str(e)}
    finally:
        cursor.close()


# ─────────────────────── CLI convenience mode ─────────────────────── #

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print(json.dumps(stats(), indent=2))
    elif sys.argv[1] == "create":
        create_table()
    elif sys.argv[1] == "stats":
        print(json.dumps(stats(), indent=2))
    elif sys.argv[1] == "list":
        agents = get_all_agents()
        print(json.dumps([dict(a) for a in agents], indent=2, default=str))
    elif sys.argv[1] == "get" and len(sys.argv) >= 3:
        name = " ".join(sys.argv[2:])
        agent = get_agent_by_name(name)
        if agent:
            print(json.dumps(dict(agent), indent=2, default=str))
        else:
            print(f"Agent not found: {name}")
    else:
        print("Usage:")
        print("  python pg_store.py                    # show stats")
        print("  python pg_store.py create              # create table")
        print("  python pg_store.py stats               # show stats")
        print("  python pg_store.py list                # list all agents")
        print('  python pg_store.py get "Agent Name"   # retrieve agent')
