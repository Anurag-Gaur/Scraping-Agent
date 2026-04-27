"""
PostgreSQL Troubleshooting Guide
═════════════════════════════════════════════════════════════════════════
"""

# COMMON ISSUES & SOLUTIONS

## ❌ "psycopg2-binary not installed"

ERROR:
  ImportError: psycopg2-binary not installed

SOLUTION:
  pip install psycopg2-binary

If using conda:
  conda install psycopg2


## ❌ "Failed to connect to database"

ERROR:
  [pg_store] Failed to connect to database: could not translate host name...

CAUSES:
  1. Internet connection down
  2. Railway PostgreSQL server down
  3. Invalid connection string
  4. Firewall blocking connection

SOLUTIONS:
  1. Check internet: ping google.com
  2. Check Railway dashboard (https://railway.app)
  3. Verify connection string in pg_store.py:
     Line ~40: _connection = psycopg2.connect(db_url)
  4. Ensure connection string has correct format:
     postgresql://username:password@host:port/database

  Test connection manually:
    python -c "
    import psycopg2
    conn = psycopg2.connect(
        'postgresql://postgres:YRMdDKECisuzTCHtDzgUlimEziCAGRIp@nozomi.proxy.rlwy.net:59367/railway'
    )
    print('✓ Connected!')
    conn.close()
    "


## ❌ "Table 'agent' already exists"

ERROR:
  psycopg2.errors.DuplicateTable: relation "agent" already exists

This is NORMAL and safe!

SOLUTION:
  This message means the table was already created. You can safely:
  - Re-run: python pg_store.py create (it's idempotent)
  - Continue with: python seed_postgres.py


## ❌ "Unique constraint violation on agent_name"

ERROR:
  psycopg2.errors.UniqueViolation: duplicate key value violates
  unique constraint "agent_name"

CAUSE:
  Trying to insert an agent with a name that already exists

SOLUTIONS:
  Option 1: Update the existing agent (automatic via upsert):
    This happens automatically - agent names are updated in-place.
    No action needed!

  Option 2: Delete and re-insert:
    python pg_store.py delete "Agent Name"
    python pg_store.py upsert "Agent Name"

  Option 3: Check what's already in database:
    python pg_store.py list


## ❌ "Agent stored in database" message but agent is missing

CAUSE:
  The agent was stored but under a different name (case sensitivity)

SOLUTIONS:
  Check stored agents:
    python pg_store.py list

  Search for similar names:
    python pg_store.py list | grep -i "partial_name"

  Note: agent_name is case-sensitive in searches
    "Accounts Payable Agent" ≠ "accounts payable agent"


## ❌ "psycopg2.OperationalError: server closed the connection"

CAUSE:
  Connection timed out or was closed by the database

SOLUTIONS:
  1. Ensure persistent internet connection
  2. Reduce long-running operations
  3. Retry the operation:
     python pg_store.py list


## ❌ "No module named pg_store"

ERROR:
  ModuleNotFoundError: No module named 'pg_store'

CAUSE:
  You're running a script from a different directory

SOLUTIONS:
  1. Make sure you're in the project root:
     cd /path/to/web_scraper/
     python research_bot.py

  2. Check that pg_store.py exists:
     ls -la pg_store.py  (Mac/Linux)
     dir pg_store.py     (Windows)


## ❌ "TypeError: argument of type 'dict' is not iterable"

CAUSE:
  JSON fields not properly formatted when storing

SOLUTIONS:
  This should not happen with the provided code. If it does:
  1. Clear your .pyc files:
     find . -type d -name __pycache__ -exec rm -r {} +

  2. Restart Python:
     python
     >>> import pg_store
     >>> pg_store.create_table()


## ❌ "DATABASE_URL environment variable not found"

CAUSE:
  Environment variable set in one terminal but not visible to Python

SOLUTIONS:
  1. Set in same terminal before running:
     export DATABASE_URL="postgresql://..."
     python pg_store.py create

  2. Or set in .env file:
     Add to .env:
       DATABASE_URL=postgresql://postgres:YRMdDKECisuzTCHtDzgUlimEziCAGRIp@...

     This file is read by python-dotenv in research_bot.py

  3. Verify it's set:
     echo $DATABASE_URL          (Mac/Linux)
     echo $env:DATABASE_URL      (Windows PowerShell)


## ❌ "FATAL: remaining connection slots reserved..."

CAUSE:
  Too many connections to the database

SOLUTIONS:
  1. This is rare with Railway. Wait a few minutes.
  2. Close any other connections:
     python pg_store.py stats  (opens/closes connection quickly)
  3. Check Railway dashboard for connection limits


## ❌ "research_bot.py runs but agent is not stored in PostgreSQL"

CAUSE:
  Either PG_ENABLED is False or upsert failed silently

SOLUTIONS:
  1. Check if pg_store import works:
     python -c "import pg_store; print('✓')"

  2. Check if PostgreSQL is enabled:
     Add this to research_bot.py main() after building spec:
       print(f"PG_ENABLED: {PG_ENABLED}")
       if PG_ENABLED:
           print(f"Storing agent: {build_spec['build_spec']['agent_name']}")
           result = pg_store.upsert_agent(...)
           print(f"Result: {result}")

  3. Try manually:
     python -c "
     import pg_store
     pg_store.upsert_agent({
         'agent_name': 'Test Agent',
         'description': 'Testing storage'
     })
     "


## ❌ "JSONB parsing error"

CAUSE:
  Invalid JSON in features or tech_stack

SOLUTIONS:
  Ensure features and tech_stack are valid JSON:
    
  agent_data = {
      "agent_name": "Agent Name",
      "features": {  # Must be dict or valid JSON string
          "capabilities": [],
          "workflow_steps": []
      },
      "tech_stack": {  # Must be dict or valid JSON string
          "llm": "gpt-4",
          ...
      }
  }

  Validate JSON:
    python -c "
    import json
    json.dumps({'key': 'value'})  # Valid
    "


## ✅ VERIFICATION CHECKLIST

Run through these to verify everything works:

□ pip install psycopg2-binary
  → Should complete without errors

□ python pg_store.py create
  → Should say "[pg_store] ✓ Table 'agent' created/verified"

□ python -c "import pg_store; print(pg_store.stats())"
  → Should show total_agents count

□ python pg_store.py list
  → Should list existing agents (empty array if none)

□ python research_bot.py "Test Requirement"
  → Should include "[PostgreSQL] ✓ Agent stored in database"

□ python pg_store.py get "Test Agent"
  → Should return the agent details


## 📞 STILL STUCK?

1. Read pg_store.py docstring (detailed documentation)
2. Check POSTGRESQL_SETUP.py (comprehensive guide)
3. Review seed_postgres.py (real-world usage example)
4. Check Railway dashboard (https://railway.app)
5. Verify connection string is correct

Connection format:
  postgresql://username:password@host:port/database

Your connection:
  postgresql://postgres:[PASSWORD]@nozomi.proxy.rlwy.net:59367/railway


═════════════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(__doc__)
