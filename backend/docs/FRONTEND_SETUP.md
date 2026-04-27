# Frontend React Setup

## Quick Start (Copy-Paste)

### 1. Create React App

```bash
# Option A: Using Create React App (simpler)
npx create-react-app agent-search-frontend
cd agent-search-frontend

# Option B: Using Vite (faster)
npm create vite@latest agent-search-frontend -- --template react
cd agent-search-frontend
npm install
```

### 2. Install Tailwind CSS (for styling)

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**Update `tailwind.config.js`:**
```js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

**Update `src/index.css`:**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 3. Copy React Component

Copy the `AgentSearch.jsx` component from `frontend/components/AgentSearch.jsx` to your React project:

```bash
mkdir -p src/components
cp AgentSearch.jsx src/components/
```

### 4. Update `src/App.jsx`

```jsx
import React from 'react';
import AgentSearch from './components/AgentSearch';
import './App.css';

function App() {
  return (
    <div className="App">
      <AgentSearch apiUrl="http://localhost:5000" />
    </div>
  );
}

export default App;
```

### 5. Start Frontend

```bash
npm start
# App opens at http://localhost:3000
```

## Full Example App

**If you want everything set up automatically:**

```bash
cd c:\Users\Abcom\Desktop\web_scraper
npx create-react-app frontend/app

# Copy component
cp frontend/components/AgentSearch.jsx frontend/app/src/components/

# Install Tailwind
cd frontend/app
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Add Tailwind config (see above)

# Start
npm start
```

## Environment Variables

Create `frontend/app/.env`:

```env
REACT_APP_API_URL=http://localhost:5000
```

Update component usage:

```jsx
<AgentSearch apiUrl={process.env.REACT_APP_API_URL} />
```

## Component Usage

### Basic Usage
```jsx
import AgentSearch from './components/AgentSearch';

function App() {
  return <AgentSearch apiUrl="http://localhost:5000" />;
}
```

### Advanced: Custom Styling
```jsx
import AgentSearch from './components/AgentSearch';

function App() {
  return (
    <div style={{ backgroundColor: '#f0f0f0', padding: '20px' }}>
      <AgentSearch apiUrl="http://localhost:5000" />
    </div>
  );
}
```

## Features

✅ **Search by Name** — Find agents by exact name  
✅ **Search by Requirement** — Find agents by keywords  
✅ **Combined Search** — Search both name and description  
✅ **Database First** — Fast results from cached database  
✅ **Auto-Scraper** — If not found, triggers web scraper  
✅ **Real-time Loading** — Shows loading state while searching  
✅ **Source Badge** — Shows if result from database or scraper  
✅ **Error Handling** — User-friendly error messages  
✅ **Beautiful UI** — Tailwind CSS styling  

## Architecture

```
React Frontend (localhost:3000)
    ↓
REST API Server (localhost:5000)
    ↓
PostgreSQL (Railway)
```

**Data Flow:**
```
User types query in search box
    ↓
Frontend sends GET /api/agents/search?query=...
    ↓
Backend checks database
    ├─ Found? → Return results
    └─ Not found? → Trigger scraper
    ↓
Frontend displays results with source badge
```

## Testing the Full Stack

### Terminal 1: Start Backend API
```bash
cd c:\Users\Abcom\Desktop\web_scraper
python api/app.py
# Listens on http://localhost:5000
```

### Terminal 2: Start Frontend
```bash
cd frontend/app  # Or wherever your React app is
npm start
# Opens http://localhost:3000
```

### Terminal 3: Test with cURL (optional)
```bash
# Search database
curl "http://localhost:5000/api/agents/search?query=Accounts"

# Trigger scraper
curl -X POST http://localhost:5000/api/agents/scrape \
  -H "Content-Type: application/json" \
  -d '{"requirement":"Procurement Agent"}'
```

## Troubleshooting

**"Failed to fetch from http://localhost:5000"**
- Make sure backend API is running: `python api/app.py`
- Check firewall allows port 5000
- Verify frontend .env has correct API_URL

**"CORS error"**
- CORS is enabled in backend (`flask-cors`)
- Try accessing `http://localhost:5000/api/health` directly in browser

**"Component not rendering"**
- Check React imports are correct
- Verify Tailwind CSS is installed
- Check browser console for errors (F12)

**"API returns 404"**
- Verify API server is running
- Check endpoint URL matches exactly
- Test with: `curl http://localhost:5000/api/health`

## Production Deployment

### Backend (API Server)

Deploy to Railway/Heroku/Cloud:

```bash
# Create Procfile
echo "web: python api/app.py" > Procfile

# Deploy
git add .
git commit -m "Add API server"
git push heroku main
```

**Set Environment Variable:**
```bash
heroku config:set DATABASE_URL=postgresql://...
heroku config:set GROQ_API_KEY=...
```

### Frontend (React App)

Deploy to Vercel/Netlify:

```bash
# Build production bundle
npm run build

# Deploy to Vercel
npm install -g vercel
vercel

# Or use Netlify
npm run build
# Drag-and-drop the `build/` folder to Netlify
```

**Update API URL in production:**

Update `.env.production`:
```env
REACT_APP_API_URL=https://your-api-server.herokuapp.com
```

## Project Structure

```
web_scraper/
├── api/
│   ├── app.py                    ← Backend API server
│   └── __init__.py
├── frontend/
│   ├── components/
│   │   └── AgentSearch.jsx       ← React component
│   └── app/                      ← Your React project (after setup)
│       ├── src/
│       │   ├── App.jsx
│       │   ├── App.css
│       │   ├── index.css
│       │   └── components/
│       │       └── AgentSearch.jsx
│       ├── package.json
│       └── .env
├── core/
├── database/
├── docs/
│   ├── API_SETUP.md             ← Backend setup
│   └── FRONTEND_SETUP.md        ← Frontend setup (this file)
```

## Next Steps

1. ✅ Start backend API: `python api/app.py`
2. ✅ Create React app: `npx create-react-app`
3. ✅ Copy AgentSearch component
4. ✅ Configure Tailwind CSS
5. ✅ Update App.jsx
6. ✅ Start frontend: `npm start`
7. ✅ Test search functionality

---

**Questions?** Check:
- `API_SETUP.md` — Backend setup and endpoints
- `STRUCTURE.md` — Project layout
- `TWO_TIER_RESEARCH.md` — How scraper works
