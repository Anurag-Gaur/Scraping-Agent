# Backend API Setup

## Installation

### 1. Install Python Dependencies

```bash
# Install Flask for API server
pip install flask flask-cors

# Verify installation
pip list | grep -i flask
```

### 2. Create `.env` file with Railway Database URL

In project root (`c:\Users\Abcom\Desktop\web_scraper\`), create/update `.env`:

```env
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=postgresql://postgres:chDIUHYWFmWDTLkOWnIQMxPjWvBMUHdW@nozomi.proxy.rlwy.net:34233/railway
```

### 3. Start the API Server

```bash
cd c:\Users\Abcom\Desktop\web_scraper

# Run the API
python api/app.py
```

**Output:**
```
======================================================================
  AGENT SEARCH API SERVER
======================================================================

[api] Starting server...
[api] Database: Railway PostgreSQL
[api] Scraper: ZBrain + DuckDuckGo + LLM

[api] API Endpoints:
  GET  /api/health                    - Health check
  GET  /api/agents/search?query=...   - Search by name/requirement
  GET  /api/agents/all                - List all agents
  GET  /api/agents/<id>               - Get agent by ID
  GET  /api/agents/name/<name>        - Get agent by name
  POST /api/agents/scrape             - Trigger scraper
  GET  /api/agents/stats              - Database statistics

[api] Frontend can connect to: http://localhost:5000
======================================================================
```

## API Endpoints

### 1. Health Check
```bash
curl http://localhost:5000/api/health
```

### 2. Search Agents
```bash
# Search by name/requirement (all)
curl "http://localhost:5000/api/agents/search?query=Accounts%20Payable"

# Search by name only
curl "http://localhost:5000/api/agents/search?query=AP%20Agent&search_type=name"

# Search by requirement
curl "http://localhost:5000/api/agents/search?query=invoice&search_type=requirement"
```

**Response:**
```json
{
  "success": true,
  "agents": [
    {
      "id": 1,
      "agent_name": "AP Agent",
      "description": "...",
      "features": [...],
      "tech_stack": {...},
      "agent_url": "...",
      "match_score": 10
    }
  ],
  "source": "database",
  "total": 1,
  "message": "Found 1 agent(s) in database"
}
```

### 3. List All Agents
```bash
curl http://localhost:5000/api/agents/all
```

### 4. Get Agent by ID
```bash
curl http://localhost:5000/api/agents/1
```

### 5. Get Agent by Name
```bash
curl http://localhost:5000/api/agents/name/AP%20Agent
```

### 6. Trigger Web Scraper (Manual)
```bash
curl -X POST http://localhost:5000/api/agents/scrape \
  -H "Content-Type: application/json" \
  -d '{"requirement": "Invoice Automation Agent"}'
```

### 7. Get Database Statistics
```bash
curl http://localhost:5000/api/agents/stats
```

## How It Works

```
User Query (from React frontend)
    ↓
REST API (/api/agents/search)
    ↓
Step 1: Check PostgreSQL database
    ├─ Found? → Return immediately
    └─ Not found? → Go to Step 2
    ↓
Step 2: Trigger web scraper
    ├─ Scrape ZBrain agents
    ├─ Search competitors via DuckDuckGo
    ├─ Analyze with Groq LLM
    └─ Save to PostgreSQL
    ↓
Return results to frontend
```

## Error Handling

- **No database connection** → Scraper still works (returns web results)
- **Scraper fails** → Returns "No agents found" message
- **Invalid query** → Returns 400 Bad Request

## Performance

- **Database hit** (agent found): <100ms
- **Scraper fallback** (not found): 4-6 minutes
- **Cached ZBrain data**: 10-30 seconds

## Troubleshooting

**"ModuleNotFoundError: No module named 'flask'"**
```bash
pip install flask flask-cors
```

**"No connection to PostgreSQL"**
- Check DATABASE_URL in .env
- Verify Railway database is running
- Test with: `python -c "from database import pg_store; print(pg_store._get_connection())"`

**"CORS error from React"**
- Already configured in app.py: `CORS(app)`
- Frontend should connect to `http://localhost:5000`

**API not responding**
```bash
curl http://localhost:5000/api/health
```

---

**Next step:** Set up the React frontend to connect to this API!
