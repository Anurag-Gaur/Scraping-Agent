```
web_scraper/
├── README.md                          ← Start here!
├── run.py                             ← Main entry point
├── requirements.txt                   ← Python dependencies
├── .env                               ← Environment variables (GROQ_API_KEY, etc.)
│
├── core/                              ← Core application modules
│   ├── research_bot.py                ← Main bot (scrapes + LLM analysis)
│   ├── rag_store.py                   ← FAISS vector database for RAG
│   └── generate_docx.js               ← Word document generation
│
├── database/                          ← PostgreSQL operations
│   ├── pg_store.py                    ← PostgreSQL agent storage & API
│   └── __init__.py
│
├── scripts/                           ← Utility scripts
│   ├── seed_postgres.py               ← Migrate agents to PostgreSQL
│   ├── seed_faiss.py                  ← Index competitor data into FAISS
│   ├── launcher.py                    ← Continuous research loop
│   ├── setup_postgres.bat             ← Windows setup script
│   ├── setup_postgres.sh              ← Linux/Mac setup script
│   └── __init__.py
│
├── docs/                              ← Documentation
│   ├── README_POSTGRES.md             ← Quick start guide
│   ├── POSTGRESQL_SETUP.py            ← Detailed setup guide
│   └── TROUBLESHOOTING_POSTGRES.py    ← Common issues & fixes
│
├── Data/                              ← Research output and RAG store
│   ├── faiss_store/                   ← Vector embeddings (FAISS index)
│   │   ├── index.faiss                ← FAISS flat-L2 index
│   │   └── metadata.json              ← Chunk metadata
│   ├── research_output/               ← Agent build specs
│   │   ├── accounts_payable_agent/
│   │   │   ├── scrape_source.json     ← Scraped competitor data WITH URLs
│   │   │   ├── build_spec.json        ← LLM-generated blueprint
│   │   │   └── raw_competitor_data.json ← (legacy format)
│   │   ├── accounts_receivable_agent/
│   │   └── sourcing_agent/
│   └── scrape_sources.json            ← Predefined source URLs (future use)
│
├── Maintenance/                       ← System status and logs
│   └── status_file.lock               ← Current bot status
│
└── venv/                              ← Virtual environment (created by pip)
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure PostgreSQL
```bash
# Windows
.\scripts\setup_postgres.bat

# Linux/Mac
chmod +x scripts/setup_postgres.sh
./scripts/setup_postgres.sh
```

### 3. Set Environment Variables
Create/edit `.env`:
```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://...
```

### 4. Run the Bot
```bash
# Interactive (will prompt for requirement)
python run.py

# Direct mode (pass requirement)
python run.py "Accounts Payable Agent"

# Or use full path if not in project root
C:\Users\Abcom\Desktop\web_scraper\venv\Scripts\python run.py
```

## 📂 Folder Organization

### `core/` - Main Application Logic
- **research_bot.py**: Main entry point
  - Scrapes competitor websites via DuckDuckGo
  - Sends findings to Groq LLM
  - Generates structured build specs
  - Saves to PostgreSQL

- **rag_store.py**: Vector search (FAISS)
  - Indexes scraped text chunks
  - Enables semantic search
  - Retrieves past context for LLM

### `database/` - PostgreSQL Management
- **pg_store.py**: Complete PostgreSQL API
  - Connection management
  - Table creation/schema
  - CRUD operations
  - Auto-generates agent URLs from names

### `scripts/` - Utilities & Setup
- **seed_postgres.py**: Migrate existing agents to database
- **seed_faiss.py**: Index existing competitor data
- **launcher.py**: Run research_bot on a loop
- **setup_postgres.bat/sh**: One-command setup

### `docs/` - Documentation
- **README_POSTGRES.md**: PostgreSQL quick start
- **POSTGRESQL_SETUP.py**: Comprehensive guide
- **TROUBLESHOOTING_POSTGRES.py**: Common issues

### `Data/` - Outputs & Storage
- **faiss_store/**: FAISS vector index for RAG
- **research_output/**: Agent build specs
  - Each agent has: `scrape_source.json`, `build_spec.json`
  - All with source URLs included

## 🔄 Data Flow

```
1. Research Phase
   ├─ research_bot.py searches DuckDuckGo
   ├─ Scrapes competitor websites
   └─ Saves to: scrape_source.json (with URLs)

2. RAG Phase
   ├─ rag_store.py chunks & embeds text
   ├─ Indexes into FAISS
   └─ Retrieves similar past context

3. LLM Analysis Phase
   ├─ research_bot.py sends to Groq
   ├─ LLM generates blueprint
   └─ Saves to: build_spec.json

4. Database Phase
   ├─ pg_store.py stores agent metadata
   ├─ PostgreSQL (Railway) backend
   └─ Includes: name, description, features, tech stack, source URLs
```

## 🗄️ Database Schema

```sql
TABLE agent (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(255) UNIQUE,
    description TEXT,
    features JSONB,              -- Core capabilities, workflow, integrations
    tech_stack JSONB,            -- LLM, orchestration, database, etc.
    agent_url VARCHAR(2048),     -- Auto-generated: /api/agents/name/
    source_urls JSONB,           -- List of URLs where data came from
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## 📊 Output Files

### Per Requirement (in `Data/research_output/<requirement>/`)

**scrape_source.json** - Scraped competitor data
```json
{
  "requirement": "accounts payable agent",
  "summary": {
    "total_pages_scraped": 12,
    "platforms_found": ["zbrain", "crewai"]
  },
  "pages_scraped_with_urls": [
    {
      "label": "zbrain_1",
      "platform": "zbrain",
      "url": "https://zbrain.ai/...",
      "quality": "good",
      "text": "..."
    }
  ]
}
```

**build_spec.json** - LLM-generated blueprint
```json
{
  "requirement": "accounts payable agent",
  "build_spec": {
    "agent_name": "AP Agent",
    "purpose": "...",
    "core_capabilities": [...],
    "workflow_steps": [...],
    "tech_stack": {...}
  }
}
```

## 🔑 Key Files to Know

| File | Purpose |
|---|---|
| `run.py` | **Start here** - main entry point |
| `core/research_bot.py` | Scraping + LLM engine |
| `database/pg_store.py` | PostgreSQL API |
| `scripts/seed_postgres.py` | Migrate agents to DB |
| `docs/README_POSTGRES.md` | PostgreSQL quick start |

## ✅ Command Reference

```bash
# Run the bot (interactive)
python run.py

# Run bot with requirement (direct)
python run.py "Invoice Automation Agent"

# Setup PostgreSQL
python scripts/seed_postgres.py

# Seed FAISS from existing data
python scripts/seed_faiss.py

# List agents in database
python database/pg_store.py list

# Get agent by name
python database/pg_store.py get "AP Agent"

# Show database stats
python database/pg_store.py stats

# Continuous loop (every 20 minutes)
python scripts/launcher.py
```

## 🛠️ Customization

### Add new platforms to search
Edit `core/research_bot.py`:
```python
COMPETITOR_SEARCHES = [
    ("zbrain",  "ZBrain AI agent {req}"),
    ("crewai",  "CrewAI {req} agent"),
    # Add more here...
]
```

### Adjust scraping settings
In `core/research_bot.py`:
```python
MIN_CONTENT_LINES = 6         # Minimum quality threshold
CHAR_LIMIT_PER_SOURCE = 6000  # Max chars per page
SCRAPE_DELAY = 1.2            # Seconds between requests
```

### Change LLM model
In `core/research_bot.py`:
```python
GROQ_MODEL = "llama-3.3-70b-versatile"  # Change this
```

## 📦 Dependencies

See `requirements.txt`:
- **Core**: anthropic, python-dotenv, requests, beautifulsoup4
- **RAG**: faiss-cpu, sentence-transformers, numpy
- **Database**: psycopg2-binary
- **Optional**: selenium, undetected-chromedriver (for JS-heavy sites)

## 🚨 Troubleshooting

**Import errors?** 
→ Make sure you're running `python run.py` from the project root

**PostgreSQL connection error?**
→ Check `.env` has valid DATABASE_URL

**GROQ API error?**
→ Verify GROQ_API_KEY is set in `.env`

See `docs/TROUBLESHOOTING_POSTGRES.py` for more help.

## 📞 Support

- Documentation: `docs/` folder
- Setup help: `docs/README_POSTGRES.md`
- Common issues: `docs/TROUBLESHOOTING_POSTGRES.py`
