import os
import sys
import asyncio
import time
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# Import your core agent logic from main.py
from main import multi_agent_task_force, query_rag_memory, embed_workspace

app = FastAPI(title="CodeFlow-AI Web Interface", version="1.0")

# Enable CORS cleanly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Models
class BuildRequest(BaseModel):
    task: str


class QueryRequest(BaseModel):
    question: str


# Serve static frontend files from a "static" folder
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")


@app.post("/api/build")
async def api_build(req: BuildRequest):
    task_lower = req.task.strip().lower()

    if task_lower in ["exit", "quit", "shutdown", "clear"]:
        return {
            "implementation": "// Session Reset\n// Ready for next engineering directive.",
            "review": "✅ SYSTEM READY\n\nDashboard cleared successfully. Awaiting next instructions."
        }

    if task_lower == "restart":
        return {
            "implementation": "# System Reboot Instruction\nprint('Rebooting backend session...')",
            "review": "✅ APPROVED\n\nReboot signal acknowledged."
        }

    try:
        result = await asyncio.to_thread(multi_agent_task_force, req.task)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
async def api_query(req: QueryRequest):
    try:
        answer = await asyncio.to_thread(query_rag_memory, req.question)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/embed")
async def api_embed():
    try:
        status = await asyncio.to_thread(embed_workspace)
        return {"status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    print("\n" + "=" * 65)
    print(" CodeFlow-AI Web Dashboard Online -> http://127.0.0.1:8000")
    print(" Press Ctrl+C in this terminal to shut down servers.")
    print("=" * 65 + "\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCodeFlow-AI: Shutdown sequence initialized. Goodbye!")
        sys.exit(0)