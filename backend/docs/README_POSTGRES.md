# PostgreSQL Migration - Quick Start

> ⏱️ **Setup Time: ~5 minutes**

You now have a hybrid storage system:
- **FAISS** (local): Vector store for competitor research + RAG retrieval
- **PostgreSQL** (Railway): Agent metadata storage

## ⚡ Quick Setup (3 commands)

```bash
# 1. Install PostgreSQL driver
pip install psycopg2-binary

# 2. Create database table
python pg_store.py create

# 3. Migrate existing agent data
python seed_postgres.py
```

**On Windows PowerShell:**
```powershell
.\setup_postgres.bat
```

**On Linux/Mac:**
```bash
chmod +x setup_postgres.sh
./setup_postgres.sh
```

## ✅ Verify Setup

```bash
# Check database statistics
python pg_store.py stats

# List all agents
python pg_store.py list

# Get specific agent
python pg_store.py get "Accounts Receivable Agent"
```

## 🚀 Use It

Now just run research_bot as normal—PostgreSQL storage is automatic:

```bash
python research_bot.py "Invoice Processing Agent"
```

You'll see new output:
```
[research_bot] Saved to: Data/research_output/invoice_processing_agent/
  raw_competitor_data.json  ← all scraped pages
  build_spec.json           ← raw JSON spec
  [PostgreSQL] ✓ Agent stored in database
```

## 📦 What Gets Stored

### FAISS (Local)
- Chunked competitor text
- Embeddings
- Used for RAG context

### PostgreSQL (Railway)
```
Agent:
  - ID
  - Name
  - Description
  - Core capabilities (JSONB)
  - Workflow steps (JSONB)
  - Integrations (JSONB)
  - Tech stack details (JSONB)
  - Build complexity & estimated days
  - Created/updated timestamps
```

## 🔌 Python API

Use `pg_store` in your code:

```python
import pg_store

# Create table (one-time)
pg_store.create_table()

# Store an agent
pg_store.upsert_agent({
    "agent_name": "My Agent",
    "description": "Does stuff",
    "features": {...},
    "tech_stack": {...}
})

# Retrieve agents
agent = pg_store.get_agent_by_name("My Agent")
all_agents = pg_store.get_all_agents()
stats = pg_store.stats()
```

See `pg_store.py` for full API documentation.

## 📋 Files Added/Modified

### New Files
- `pg_store.py` - PostgreSQL module (main)
- `seed_postgres.py` - Migration script
- `POSTGRESQL_SETUP.py` - Detailed setup guide
- `setup_postgres.bat` - Windows quick setup
- `setup_postgres.sh` - Linux/Mac quick setup

### Modified Files
- `requirements.txt` - Added psycopg2-binary
- `research_bot.py` - Auto-saves to PostgreSQL
- `seed_faiss.py` - Auto-seeds PostgreSQL

## ❓ Need Help?

1. **Connection issues?**
   ```bash
   python pg_store.py create
   ```
   This will test the connection.

2. **Want full documentation?**
   ```bash
   python POSTGRESQL_SETUP.py
   ```

3. **Want to see the database?**
   ```bash
   python pg_store.py list
   python pg_store.py stats
   ```

## 🔐 Connection Details

Database URL (already set in `pg_store.py`):
```
postgresql://postgres:YRMdDKECisuzTCHtDzgUlimEziCAGRIp@nozomi.proxy.rlwy.net:59367/railway
```

Can also set via environment variable `DATABASE_URL`.

## 📊 Example Workflow

```bash
# First time setup
$ python pg_store.py create
$ python seed_postgres.py

# Research a new requirement
$ python research_bot.py "Payment Reconciliation Agent"

# Verify it's stored
$ python pg_store.py list
$ python pg_store.py get "Payment Reconciliation Agent"

# Get stats
$ python pg_store.py stats
```

---

**That's it!** Your agent metadata is now backed up in PostgreSQL while FAISS handles the research RAG retrieval. 🎉
