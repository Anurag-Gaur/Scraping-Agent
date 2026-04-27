from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import os
import uuid
import time
from dotenv import load_dotenv
import asyncio
from datetime import datetime

# Load backend modules
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import pg_store
from core import rag_store
import requests
import re

load_dotenv()

app = FastAPI(title="AgentFinder API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Simple in-memory session store (we can persist this to Postgres if we create a sessions table)
# For now, following the 'proper database connection' request, we'll try to add a sessions table
def init_db():
    conn = pg_store._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_session (
            id VARCHAR(255) PRIMARY KEY,
            title VARCHAR(255),
            messages JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cursor.close()

try:
    init_db()
except Exception as e:
    print(f"Failed to init chat_session table: {e}")

@app.get("/api/history/sessions")
def get_sessions():
    try:
        conn = pg_store._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, created_at FROM chat_session ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        sessions = [{"id": r[0], "title": r[1], "timestamp": r[2].isoformat()} for r in rows]
        return {"sessions": sessions}
    except Exception as e:
        print(f"Error fetching sessions: {e}")
        return {"sessions": []}

@app.post("/api/history/sessions")
async def save_session(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    title = data.get("title", "New Chat")
    messages = data.get("messages", [])
    if not session_id:
        return {"error": "Missing session_id"}
    try:
        conn = pg_store._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_session (id, title, messages)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                messages = EXCLUDED.messages,
                updated_at = CURRENT_TIMESTAMP
        """, (session_id, title, json.dumps(messages)))
        conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error saving session: {e}")
        return {"error": str(e)}

@app.get("/api/history/sessions/{session_id}")
def get_session(session_id: str):
    try:
        conn = pg_store._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, messages FROM chat_session WHERE id = %s", (session_id,))
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "messages": row[1]}
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    data = await request.json()
    message = data.get("message", "")
    
    async def generate():
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        yield "data: " + json.dumps({'type': 'status', 'content': 'Searching knowledge base...'}) + "\n\n"
        
        context = rag_store.query(message, top_k=5)
        
        system_prompt = "You are a helpful Agent Discovery Assistant. Answer questions about AI agents, capabilities, and solutions. "
        citations = []
        
        if context:
            system_prompt += f"Use the following past research context to answer the user's question:\\n\\n{context}"
            
            # Extract simple citations from the context text block
            platforms = re.findall(r"\[([A-Z_]+) — past req:", context)
            unique_platforms = list(set(platforms))
            
            for idx, plat in enumerate(unique_platforms):
                citations.append({
                    "source": plat,
                    "page": str(idx + 1),
                    "text_snippet": "Extracted from " + plat + " research."
                })
            
            if unique_platforms:
                msg = f'Searched in {len(unique_platforms)} sources...'
                yield "data: " + json.dumps({'type': 'status', 'content': msg}) + "\n\n"
        else:
            yield "data: " + json.dumps({'type': 'status', 'content': 'No relevant documents found in knowledge base.'}) + "\n\n"
        
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            "temperature": 0.5,
            "stream": True
        }
        
        try:
            with requests.post(GROQ_API_URL, headers=headers, json=payload, stream=True) as response:
                if not response.ok:
                    yield "data: " + json.dumps({'type': 'token', 'content': f'Error: {response.text}'}) + "\n\n"
                    return
                    
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith("data: ") and line != "data: [DONE]":
                            content_data = line[6:]
                            try:
                                chunk = json.loads(content_data)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        token = delta["content"]
                                        yield "data: " + json.dumps({'type': 'token', 'content': token}) + "\n\n"
                            except json.JSONDecodeError:
                                pass
            
            if citations:
                yield "data: " + json.dumps({'type': 'citations', 'citations': citations}) + "\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield "data: " + json.dumps({'type': 'token', 'content': f'Exception: {str(e)}'}) + "\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
