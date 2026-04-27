"""
POSTGRESQL MIGRATION GUIDE
════════════════════════════════════════════════════════════════════════

This guide walks you through migrating from FAISS-only storage to
a hybrid approach: FAISS for RAG + PostgreSQL for agent metadata.

ARCHITECTURE OVERVIEW
─────────────────────────────────────────────────────────────────────

Before (FAISS only):
  research_bot.py → scrape & analyze → save JSON locally only
                → index raw text chunks into FAISS for retrieval

After (FAISS + PostgreSQL):
  research_bot.py → scrape & analyze → save JSON locally
                → index raw text into FAISS for retrieval
                → store agent metadata in PostgreSQL (Railway)

WHAT GETS STORED WHERE
──────────────────────────────────────────────────────────────────────

Local (FAISS - Vector Store):
  • Chunked competitor research text
  • Embeddings for semantic search
  • Used for RAG context retrieval in LLM prompts

PostgreSQL (Railway):
  • Agent name
  • Description
  • Features (core capabilities, workflow steps, integrations)
  • Tech stack (LLM, orchestration, database, etc.)
  • Build complexity & estimated days
  • Timestamps (created_at, updated_at)

SETUP STEPS
──────────────────────────────────────────────────────────────────────

1. INSTALL NEW DEPENDENCY
   ─────────────────────────

   The PostgreSQL driver has already been added to requirements.txt.
   Install it:

   $ pip install -r requirements.txt

   Or just the new package:

   $ pip install psycopg2-binary>=2.9.0


2. CONFIGURE DATABASE CONNECTION (Optional)
   ──────────────────────────────────────────

   The connection string is hardcoded in pg_store.py, but you can
   override it using an environment variable:

   # In your .env file or shell:
   export DATABASE_URL="postgresql://postgres:YRMdDKECisuzTCHtDzgUlimEziCAGRIp@nozomi.proxy.rlwy.net:59367/railway"

   Or set it in your terminal:

   Linux/Mac:
   $ export DATABASE_URL="postgresql://postgres:..."

   Windows PowerShell:
   $ $env:DATABASE_URL="postgresql://postgres:..."


3. CREATE THE DATABASE TABLE (One-time setup)
   ───────────────────────────────────────────

   Before storing data, create the table schema:

   $ python pg_store.py create

   You should see:
   [pg_store] ✓ Connected to PostgreSQL
   [pg_store] ✓ Table 'agent' created/verified

   This creates a table with these columns:
   - id (auto-incrementing primary key)
   - agent_name (unique, indexed)
   - description
   - features (JSONB)
   - tech_stack (JSONB)
   - agent_url
   - created_at, updated_at (auto-timestamps)


4. MIGRATE EXISTING DATA
   ──────────────────────

   If you have existing build_spec.json files that were only stored
   locally, seed them into PostgreSQL:

   $ python seed_postgres.py

   This will:
   - Walk Data/research_output/ folders
   - Extract agent metadata from build_spec.json files
   - Insert them into PostgreSQL
   - Show you a summary

   You should see output like:
   [seed_postgres] Found 2 agent folder(s)
   [seed_postgres] Creating table schema...
   [load] accounts_payable_agent/
          ✓ Upserted agent (ID: 1, Name: Accounts Payable Agent)
   [load] accounts_receivable_agent/
          ✓ Upserted agent (ID: 2, Name: Accounts Receivable Agent)
   ...
   [seed_postgres] Database stats:
                    • Total agents in DB: 2


5. FROM HERE ON, AUTOMATIC STORAGE
   ────────────────────────────────

   Once set up, everything works automatically:

   • When you run `python research_bot.py "requirement"`:
     - It saves JSON files locally (as before)
     - Indexes competitor text into FAISS (as before)
     - ALSO stores the agent spec in PostgreSQL (NEW!)

   • When you run `python seed_faiss.py`:
     - It seeds FAISS from raw_competitor_data.json (as before)
     - ALSO seeds PostgreSQL from build_spec.json (NEW!)

   No code changes needed from you.


VERIFICATION & TESTING
──────────────────────────────────────────────────────────────────────

1. Check database stats:
   $ python pg_store.py stats

   Output:
   {
     "total_agents": 2,
     "database": "PostgreSQL (Railway)",
     "table": "agent"
   }


2. List all agents in database:
   $ python pg_store.py list

   Output:
   [
     {
       "id": 1,
       "agent_name": "Accounts Payable Agent",
       "description": "To automate and streamline the accounts payable process...",
       "features": {...},
       "tech_stack": {...},
       "created_at": "2026-04-22T10:30:45.123456",
       "updated_at": "2026-04-22T10:30:45.123456"
     },
     ...
   ]


3. Retrieve a specific agent:
   $ python pg_store.py get "Accounts Receivable Agent"

   Output:
   {
     "id": 2,
     "agent_name": "Accounts Receivable Agent",
     ...
   }


4. Run research_bot and verify PostgreSQL storage:
   $ python research_bot.py "new requirement"

   In the output, you should see:
   [research_bot] Saved to: Data/research_output/new_requirement/
     raw_competitor_data.json  ← all scraped pages
     build_spec.json           ← raw JSON spec
     [PostgreSQL] ✓ Agent stored in database


AVAILABLE FUNCTIONS (For scripting)
──────────────────────────────────────────────────────────────────────

In pg_store.py:

  pg_store.create_table()
    → Create/verify table schema

  pg_store.upsert_agent(agent_data)
    → Insert or update agent
    → agent_data = {
        "agent_name": "...",
        "description": "...",
        "features": {...},
        "tech_stack": {...},
        "agent_url": "..." (optional)
      }

  pg_store.get_agent_by_name(name)
    → Retrieve agent by name

  pg_store.get_agent_by_id(id)
    → Retrieve agent by ID

  pg_store.get_all_agents()
    → List all agents

  pg_store.delete_agent(name)
    → Delete agent by name

  pg_store.stats()
    → Get database statistics


TROUBLESHOOTING
────────────────────────────────────────────────────────────────────

❌ "psycopg2-binary not installed"
   → Run: pip install psycopg2-binary

❌ "Failed to connect to database"
   → Check your connection string
   → Verify Railway PostgreSQL is running
   → Test connection: python -c "import pg_store; pg_store.create_table()"

❌ "Table already exists" warning
   → This is normal; the table creation is idempotent

❌ "Agent stored in database" but agent is missing later
   → Verify the agent_name is unique (it's a UNIQUE constraint)
   → Check that you're querying the correct name/ID

❌ DATABASE_URL environment variable not being read
   → Reload your shell or terminal after setting .env
   → Verify with: echo $DATABASE_URL (Mac/Linux) or $env:DATABASE_URL (Windows)


DATABASE SCHEMA
──────────────────────────────────────────────────────────────────────

CREATE TABLE agent (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    features JSONB,
    tech_stack JSONB,
    agent_url VARCHAR(2048),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agent_name ON agent(agent_name);


EXAMPLE WORKFLOW
───────────────────────────────────────────────────────────────────────

# Step 1: Set up PostgreSQL (one-time)
$ python pg_store.py create

# Step 2: Migrate existing local data
$ python seed_postgres.py

# Step 3: Run research bot normally
$ python research_bot.py "Invoice Processing Agent"

# Step 4: Verify it's in the database
$ python pg_store.py list
$ python pg_store.py get "Invoice Processing Agent"

# Step 5: From now on, just keep running research_bot
# PostgreSQL storage happens automatically!
$ python research_bot.py "Payment Reconciliation Agent"


NEXT STEPS
──────────────────────────────────────────────────────────────────────

1. Run: pip install psycopg2-binary
2. Run: python pg_store.py create
3. Run: python seed_postgres.py
4. Test: python pg_store.py list

Then start using research_bot normally — PostgreSQL storage is automatic!


QUESTIONS OR ISSUES?
─────────────────────────────────────────────────────────────────────

Check pg_store.py docstring for detailed API documentation.
All functions have detailed docstrings with examples.

════════════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(__doc__)
