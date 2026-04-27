# Connecting Your Frontend to the Agent Search API

## Quick Start

### 1. Start the Backend API Server

```bash
cd c:\Users\Abcom\Desktop\web_scraper

# Install Flask (one-time)
pip install flask flask-cors

# Run the API
python api/app.py
```

**The API will be available at:** `http://localhost:5000`

### 2. Connect Your Frontend

Update your frontend to call the API endpoints. Use these URLs:

```javascript
const API_URL = "http://localhost:5000";

// Search for agents
async function searchAgents(query, searchType = "all") {
  const params = new URLSearchParams({
    query: query,
    search_type: searchType
  });

  const response = await fetch(
    `${API_URL}/api/agents/search?${params}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json"
      }
    }
  );

  return await response.json();
}

// Example usage:
// const result = await searchAgents("Accounts Payable Agent");
// console.log(result);
// Output:
// {
//   success: true,
//   agents: [...],
//   source: "database" | "scraper",
//   message: "..."
// }
```

## API Endpoints

### Search Agents (Primary)
```
GET /api/agents/search?query=<search_term>&search_type=<type>

Query Parameters:
  - query: Search term (required)
  - search_type: "name" | "requirement" | "all" (default: "all")

Response:
{
  "success": true,
  "agents": [
    {
      "id": 1,
      "agent_name": "AP Agent",
      "description": "...",
      "features": [...],
      "tech_stack": {...},
      "agent_url": "..."
    }
  ],
  "source": "database" | "scraper",
  "total": 1,
  "message": "Found 1 agent(s) in database"
}
```

### List All Agents
```
GET /api/agents/all

Response:
{
  "success": true,
  "agents": [...],
  "total": 5
}
```

### Get Agent by ID
```
GET /api/agents/<id>

Response:
{
  "success": true,
  "agent": {...}
}
```

### Get Agent by Name
```
GET /api/agents/name/<name>

Response:
{
  "success": true,
  "agent": {...}
}
```

### Trigger Web Scraper (Manual)
```
POST /api/agents/scrape
Content-Type: application/json

{
  "requirement": "Invoice Processing Agent"
}

Response:
{
  "success": true,
  "requirement": "Invoice Processing Agent",
  "agents_found": 1,
  "agents": [...],
  "message": "Successfully scraped and saved 1 agent(s)"
}
```

### Get Database Stats
```
GET /api/agents/stats

Response:
{
  "success": true,
  "stats": {
    "total_agents": 5,
    "total_integrations": 12,
    "created_at": "...",
    "last_updated": "..."
  }
}
```

### Health Check
```
GET /api/health

Response:
{
  "status": "ok",
  "message": "API server is running"
}
```

## How It Works

```
User enters query in your frontend
    ↓
Frontend sends GET /api/agents/search?query=...
    ↓
Backend API checks PostgreSQL database
    ├─ Found? → Return results immediately
    └─ Not found? → Trigger web scraper
    ↓
Web scraper:
├─ Searches ZBrain agents
├─ Searches competitor platforms (DuckDuckGo)
├─ Analyzes with Groq LLM
└─ Saves to PostgreSQL
    ↓
Backend returns results with source ("database" or "scraper")
    ↓
Frontend displays results to user
```

## Response Example

**When agent found in database (fast):**
```json
{
  "success": true,
  "agents": [
    {
      "id": 1,
      "agent_name": "Accounts Payable Agent",
      "description": "Automates accounts payable workflow",
      "features": ["invoice validation", "payment routing", "reconciliation"],
      "tech_stack": {
        "llm": "llama-3.3-70b",
        "orchestration": "LangChain",
        "database": "PostgreSQL"
      },
      "agent_url": "/api/agents/ap-agent/",
      "match_score": 10
    }
  ],
  "source": "database",
  "total": 1,
  "message": "Found 1 agent(s) in database"
}
```

**When agent not found → scraper triggered (slower, more comprehensive):**
```json
{
  "success": true,
  "agents": [
    {
      "id": 2,
      "agent_name": "Custom Invoice Agent",
      "description": "...",
      "features": [...],
      "tech_stack": {...},
      "agent_url": "..."
    }
  ],
  "source": "scraper",
  "total": 1,
  "message": "Scraped 1 agent(s) from web and saved to database"
}
```

## Frontend Integration Example (React)

```jsx
import { useState } from 'react';

function AgentSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [source, setSource] = useState('');

  const handleSearch = async (e) => {
    e.preventDefault();
    setLoading(true);
    setSource('');
    
    try {
      const response = await fetch(
        `http://localhost:5000/api/agents/search?query=${encodeURIComponent(query)}`
      );
      const data = await response.json();
      
      if (data.success) {
        setResults(data.agents);
        setSource(data.source); // "database" or "scraper"
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSearch}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for an agent..."
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {source && (
        <p style={{ color: source === 'database' ? 'green' : 'blue' }}>
          Results from: {source === 'database' ? '✓ Database' : '🌐 Web Scraper'}
        </p>
      )}

      {results.map((agent) => (
        <div key={agent.id}>
          <h3>{agent.agent_name}</h3>
          <p>{agent.description}</p>
          {/* Display other agent details */}
        </div>
      ))}
    </div>
  );
}

export default AgentSearch;
```

## Performance

- **Database hit** (agent found): <100ms
- **Scraper fallback** (not found): 4-6 minutes
  - 2-3 min: ZBrain scraping
  - 3-5 min: DuckDuckGo + competitor search
  - 1-2 min: Groq LLM analysis
- **Cached ZBrain data**: 10-30 seconds

## Error Handling

The API returns standard HTTP status codes:

```
200 OK - Successful request
400 Bad Request - Missing or invalid query parameter
404 Not Found - No agents found
500 Internal Server Error - Server error
```

Example error response:
```json
{
  "success": false,
  "error": "No agents found in database or web scraper",
  "message": "Try a different search term"
}
```

## Environment Setup

The API requires a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_key
DATABASE_URL=postgresql://postgres:chDIUHYWFmWDTLkOWnIQMxPjWvBMUHdW@nozomi.proxy.rlwy.net:34233/railway
```

## CORS Configuration

CORS is enabled in the API server, so your frontend can call it from any domain:

```python
from flask_cors import CORS
CORS(app)  # Allow all origins
```

If you need to restrict to specific domains:
```python
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000"]}})
```

## Troubleshooting

**"Failed to fetch from localhost:5000"**
- Ensure API server is running: `python api/app.py`
- Check if port 5000 is available: `netstat -ano | findstr :5000`
- Try accessing `http://localhost:5000/api/health` in browser

**"CORS error"**
- Already enabled in app.py
- Check your frontend is sending correct headers
- Verify API URL matches exactly

**"No database connection"**
- Check `.env` file has valid DATABASE_URL
- Verify Railway PostgreSQL is running
- Test: `python -c "from database import pg_store; pg_store.get_all_agents()"`

**"Scraper timeout"**
- Increase timeout in `core/zbrain_scraper.py`
- Or use `/api/agents/scrape` endpoint with manual retry

---

**Ready?** Start the API server and integrate the endpoints with your frontend! 🚀
