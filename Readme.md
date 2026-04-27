# AI Agent Scraper & Advisor 🤖

A sophisticated full-stack platform designed to discover, scrape, and analyze specialized AI agents. This project leverages an automated research engine combined with a RAG-powered conversational advisor to provide users with precise, data-backed automation solutions.

---

## 🏗 System Architecture

### 1. Frontend (React / Vite)
- **Framework**: Built with React 18 and Vite for ultra-fast development and optimized production builds.
- **Styling**: Modern, premium UI utilizing **Tailwind CSS** with full dark/light mode support.
- **Icons**: Professional iconography provided by **Lucide React**.
- **State Management**: React Hooks (`useState`, `useEffect`, `useCallback`) handle real-time message streaming and session persistence.

### 2. Backend (FastAPI)
- **Web Framework**: **FastAPI** provides a high-performance, asynchronous REST API layer.
- **LLM Integration**: Powered by **Groq (Llama-3.3-70b-versatile)** for near-instantaneous reasoning and response generation.
- **Streaming**: Implements Server-Sent Events (SSE) to stream tokens directly to the UI, providing a seamless "typing" experience.
- **RAG Engine**: Integrated with **FAISS** (Facebook AI Similarity Search) for high-dimensional vector retrieval from the local knowledge base.

### 3. Database (PostgreSQL)
- **Hosting**: Deployed on **Railway** for reliable, cloud-native PostgreSQL performance.
- **Storage Strategy**: Uses a `chat_session` table with a **JSONB** column to store complex message histories, including metadata like citations and source snippets.

---

## 💎 Advanced Features & Technical Implementation

### 🔍 RAG-Driven Chatbot with Citations
The chatbot doesn't just "guess"—it researches using a specialized Retrieval-Augmented Generation pipeline.
- **Vector Search Engine**: Powered by **FAISS (Facebook AI Similarity Search)** utilizing a `FlatL2` index for rapid semantic lookup across thousands of scraped text chunks.
- **Embeddings**: Text is vectorized into 384-dimensional embeddings using the **`sentence-transformers`** library (specifically the `all-MiniLM-L6-v2` model), ensuring high-quality semantic matching on standard CPUs.
- **Citation Logic**: 
    - **Retrieval**: The system fetches the top-k most relevant chunks based on cosine similarity.
    - **Extraction**: A custom **Regex-based parser** in the backend scans retrieved chunks to extract platform labels (e.g., `ZBRAIN`, `RELEVANCEAI`).
    - **Metadata Mapping**: These labels are converted into a structured `citations` array (including source, "page" index, and snippet) and sent as a final metadata block in the stream.

### 📡 Real-Time Streaming & UI Feedback
- **Protocol**: Uses **Server-Sent Events (SSE)** via FastAPI's `StreamingResponse`. 
- **Dynamic Status Updates**: We implemented a custom `type: status` event. This allows the backend to notify the frontend when it is *"Searching knowledge base"* or *"Synthesizing response"*, which the React UI renders as a dynamic status pill.
- **Streaming Parser**: The frontend uses a `ReadableStream` reader with a `TextDecoder` and a line-based buffer to safely parse fragmented JSON chunks emitted by the Groq API.
- **Markdown Processing**: Responses are rendered via a custom `renderMarkdown` utility that handles bolding, headers, code blocks, and lists while maintaining high security against XSS.

### 🛡️ Proper Database Connection & Persistence
We implemented a professional-grade persistence layer hosted on **Railway PostgreSQL**.
- **Driver**: Uses the **`psycopg2-binary`** adapter for robust, thread-safe database operations.
- **Storage Pattern**: Instead of flat relational mapping for every message, we store the entire message thread as a **JSONB** object. This allows for flexible schema evolution (e.g., adding citations or new metadata later) while maintaining fast read speeds.
- **Session Management**: Session IDs are generated using a custom alphanumeric `generateId` utility. On every message turn, the backend executes an `INSERT ... ON CONFLICT (id) DO UPDATE` (Upsert) to keep the history in sync with minimal latency.

### ⚡ Performance & Cleanup
- **Optimized Stream**: Removed legacy Flask dependencies in favor of FastAPI's native async capabilities.
- **Frontend Hygiene**: Purged unused document upload logic and refactored the `Chat.jsx` component for better performance and readability.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Groq API Key
- PostgreSQL Database (e.g., Railway)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python api.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables (.env)
```env
GROQ_API_KEY=your_key_here
DATABASE_URL=your_postgresql_url_here
```

---

## 📊 Technical Flow Summary
1. **User Input** → Frontend emits a POST request to `/api/chat/stream`.
2. **Backend Search** → Queries FAISS vector index for matching research snippets.
3. **Status Update** → API streams `type: status` to the UI for immediate user feedback.
4. **LLM Generation** → Groq synthesizes a response using the retrieved context.
5. **Final Payload** → Backend streams tokens followed by a `type: citations` metadata block.
6. **Persistence** → The complete turn is updated in the PostgreSQL `chat_session` table.
