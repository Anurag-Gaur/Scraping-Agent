# Backend API - Quick Start

## 🚀 Start the Server (30 seconds)

```bash
cd c:\Users\Abcom\Desktop\web_scraper
python api/app.py
```

**Expected output:**
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

* Running on http://0.0.0.0:5000
```

✅ API is now running!

---

## 📱 Connect Your Frontend

### Option 1: JavaScript/React

```javascript
const API_URL = "http://localhost:5000";

// Search for agents
async function searchAgents(query) {
  const response = await fetch(
    `${API_URL}/api/agents/search?query=${encodeURIComponent(query)}`
  );
  return await response.json();
}

// Example
const result = await searchAgents("Accounts Payable");
console.log(result);
// Output:
// {
//   success: true,
//   agents: [...],
//   source: "database" | "scraper",
//   message: "..."
// }
```

### Option 2: cURL (for testing)

```bash
# Search agents
curl "http://localhost:5000/api/agents/search?query=Accounts%20Payable"

# Get all agents
curl "http://localhost:5000/api/agents/all"

# Get database stats
curl "http://localhost:5000/api/agents/stats"

# Trigger scraper
curl -X POST http://localhost:5000/api/agents/scrape \
  -H "Content-Type: application/json" \
  -d '{"requirement":"Invoice Processing Agent"}'
```

### Option 3: Python

```python
import requests

API_URL = "http://localhost:5000"

# Search
response = requests.get(
    f"{API_URL}/api/agents/search",
    params={"query": "Accounts Payable"}
)
print(response.json())
```

---

## 🔄 How It Works

```
1. User searches for an agent in your frontend
         ↓
2. Frontend calls: GET /api/agents/search?query=...
         ↓
3. Backend checks PostgreSQL database
    ├─ Found? → Return results (fast, <100ms)
    └─ Not found? → Trigger web scraper
         ↓
4. Web scraper runs:
    ├─ Scrapes ZBrain agents
    ├─ Searches competitors (DuckDuckGo)
    ├─ Analyzes with Groq LLM
    └─ Saves to PostgreSQL
         ↓
5. Frontend displays results with source badge:
    ✓ Database (fast, cached)
    🌐 Web Scraper (comprehensive)
```

---

## 📊 Example Search Flow

### Fast: Agent found in database

```bash
$ curl "http://localhost:5000/api/agents/search?query=Accounts%20Payable"

# Response (instant):
{
  "success": true,
  "agents": [
    {
      "id": 1,
      "agent_name": "AP Agent",
      "description": "Automates accounts payable workflow",
      "features": ["invoice validation", "payment routing"],
      "tech_stack": {...},
      "agent_url": "/api/agents/ap-agent/"
    }
  ],
  "source": "database",
  "total": 1,
  "message": "Found 1 agent(s) in database"
}
```

### Slow: Agent not found → Trigger scraper

```bash
$ curl "http://localhost:5000/api/agents/search?query=Custom%20DPO%20Agent"

# Response (4-6 minutes):
{
  "success": true,
  "agents": [
    {
      "id": 2,
      "agent_name": "DPO Agent",
      "description": "...",
      "features": [...],
      "tech_stack": {...}
    }
  ],
  "source": "scraper",
  "total": 1,
  "message": "Scraped 1 agent(s) from web and saved to database"
}
```

---

## 🔑 Main Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/health` | Check if server is running |
| GET | `/api/agents/search?query=...` | **Search agents (DB + scraper fallback)** |
| GET | `/api/agents/all` | List all agents in database |
| GET | `/api/agents/<id>` | Get agent by ID |
| GET | `/api/agents/name/<name>` | Get agent by exact name |
| POST | `/api/agents/scrape` | Manually trigger scraper |
| GET | `/api/agents/stats` | Database statistics |

---

## ⚙️ Configuration

The API uses your `.env` file:

```env
GROQ_API_KEY=your_groq_key
DATABASE_URL=postgresql://postgres:chDIUHYWFmWDTLkOWnIQMxPjWvBMUHdW@nozomi.proxy.rlwy.net:34233/railway
```

---

## 🐛 Troubleshooting

**"Connection refused"**
- Make sure `python api/app.py` is running
- Check port 5000 is available

**"No database connection"**
- Verify `.env` has correct DATABASE_URL
- Check Railway PostgreSQL is running

**"CORS error from frontend"**
- Already enabled in API
- Verify frontend is calling `http://localhost:5000` (not `localhost:5000` without http)

**"Timeout on search"**
- First search might take 4-6 minutes if scraper is triggered
- Subsequent searches are fast (database cached)

---

## 📚 Full Documentation

- `docs/API_SETUP.md` — Detailed API documentation
- `docs/INTEGRATE_FRONTEND.md` — Integration guide with examples
- `docs/TWO_TIER_RESEARCH.md` — How the scraper works

---

## ✅ Ready?

```bash
# Terminal 1: Start API
python api/app.py

# Terminal 2: Test API (in another terminal)
curl "http://localhost:5000/api/health"

# Terminal 3: Connect your frontend
# Update your frontend code to call http://localhost:5000/api/agents/search
```

🎉 Done! Your frontend can now search agents from the database with automatic web scraper fallback!
