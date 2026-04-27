# AgentFinder: AI Agent Discovery & Research Platform

AgentFinder is a high-performance research tool designed to discover, scrape, and synthesize building specifications for AI agents based on client requirements. It leverages advanced scraping techniques, FAISS-backed RAG (Retrieval-Augmented Generation), and the Groq LLM for real-time intelligence.

---

## 🚀 Recent Core Updates (Integration Phase)

We have successfully bridged the gap between the standalone Python research engine and the React frontend.

### 🔹 Full-Stack Integration

- **FastAPI Layer**: Introduced `backend/api.py`, a modern API server that handles all communication between the frontend and the database/LLM.
- **Database Persistence**: Integrated **PostgreSQL (Railway)** for chat history. A new `chat_session` table automatically stores and retrieves your past conversations.
- **Real-time Streaming**: Implemented server-sent events (SSE) for the chatbot, allowing the Groq LLM responses to stream token-by-token for a seamless user experience.

### 🔹 Advanced RAG Features

- **Dynamic Source Attribution**: The chatbot no longer answers from memory alone. It queries the FAISS vector store to find relevant past research.
- **Live Search Indicators**: The UI now displays a dynamic "Searching..." pill (e.g., *Searched in 3 sources...*) while the backend performs vector lookups.
- **Citations**: Assistant responses now include interactive source bubbles that show exactly which competitor platform the data was retrieved from (e.g., ZBrain, CrewAI, RelevanceAI).

### 🔹 Frontend Optimization

- **UI/UX Polish**: Refined the loading state with improved "bouncing dots" and status pills.
- **Code Cleanup**: Removed legacy document upload logic and unused states to ensure a lean, focused production codebase.
- **Re-wiring**: Updated the frontend to communicate directly with the local FastAPI backend.

---

## 🛠 Project Architecture

### Backend (`/backend`)

- **`api.py`**: The central FastAPI hub.
- **`core/research_bot.py`**: The heavy-lifting engine that scrapes DuckDuckGo and competitor sites.
- **`core/rag_store.py`**: Manages FAISS vector embeddings for semantic knowledge retrieval.
- **`database/pg_store.py`**: Handles all PostgreSQL operations on Railway.
- **`Data/faiss_store/`**: Local storage for the vector index.

### Frontend (`/frontend`)

- **React + Vite**: A modern, high-speed frontend framework.
- **Tailwind CSS**: Custom-designed, premium aesthetics with dark/light mode support.
- **Lucide React**: Sleek iconography for a professional look.

---

## ⚙️ Setup & Installation

### 1. Backend Setup

```bash
cd backend
# Install dependencies
pip install -r requirements.txt
# Start the API server
python api.py
```

### 2. Frontend Setup

```bash
cd frontend
# Install dependencies
npm install
# Start the development server
npm run dev
```

### 3. Environment Variables (`.env`)

Ensure your `backend/.env` contains:

- `GROQ_API_KEY`: Your Groq API key.
- `DATABASE_URL`: Your Railway PostgreSQL connection string.

---

## 📊 Data Flow

1. **User Request**: User asks about an agent (e.g., "Accounts Payable Agent").
2. **Knowledge Retrieval**: `api.py` sends a "Searching..." status and queries `rag_store.py`.
3. **LLM Synthesis**: Groq LLM receives the requirement + retrieved context.
4. **Streaming Response**: Tokens are streamed to the UI while source citations are calculated.
5. **Persistence**: The conversation is saved to the `chat_session` table in Postgres.

---

## 📞 Support

For maintenance or troubleshooting, refer to the `backend/docs/` folder or the `STRUCTURE.md` file for deep technical details.
