import asyncio
import json
import threading
from queue import Queue
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import storage
from debate import run_debate

app = FastAPI(title="AI Debate Agent API")

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DebateRequest(BaseModel):
    topic: str
    rounds: int = 3


@app.get("/api/history")
async def get_history():
    sessions = storage.load_sessions()
    # Sort by timestamp descending or assume storage order is correct
    return {"sessions": sessions}


@app.get("/api/history/{idx}")
async def get_history_item(idx: int):
    sessions = storage.load_sessions()
    if 0 <= idx < len(sessions):
        return {"session": sessions[idx]}
    return {"error": "Not found"}, 404


@app.post("/api/debate/stream")
async def stream_debate(request: DebateRequest):
    topic = request.topic
    rounds = request.rounds

    if not topic.strip():
        return {"error": "Topic is required"}, 400

    async def event_generator():
        q: Queue = Queue()

        def _run():
            try:
                for _ in run_debate(topic, rounds, q=q):
                    pass
                q.put(("done", None))
            except Exception as exc:
                q.put(("error", str(exc) or type(exc).__name__))

        threading.Thread(target=_run, daemon=True).start()

        # Send an initial starting event
        yield f"event: status\ndata: {json.dumps({'message': 'Agents are preparing…'})}\n\n"

        while True:
            # We use a slight sleep in the async loop to allow other tasks to run,
            # but we read from the sync Queue. In a true async app we'd use asyncio.Queue,
            # but debate.py is synchronous, so we bridge it carefully.
            await asyncio.sleep(0.01)
            
            while not q.empty():
                msg_type, data = q.get()

                if msg_type == "chunk":
                    yield f"event: chunk\ndata: {json.dumps(data)}\n\n"

                elif msg_type == "judge_chunk":
                    # data is likely a string here
                    yield f"event: judge_chunk\ndata: {json.dumps({'content': data})}\n\n"

                elif msg_type == "state_full":
                    # full state update, also handle saving if verdict is final
                    new_vr = data.get("verdict", {})
                    if new_vr and not isinstance(new_vr, str):
                        # Final save
                        transcript = data.get("transcript", [])
                        storage.save_session(topic, rounds, transcript, new_vr)
                        
                    safe_data = {"transcript": data.get("transcript", []), "verdict": data.get("verdict", {})}
                    yield f"event: state_full\ndata: {json.dumps(safe_data)}\n\n"

                elif msg_type == "error":
                    yield f"event: error\ndata: {json.dumps({'detail': data})}\n\n"
                    return

                elif msg_type == "done":
                    yield f"event: done\ndata: {{}}\n\n"
                    return

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

@app.delete("/api/history")
async def delete_all_history():
    success = storage.clear_sessions()
    if success:
        return {"status": "cleared"}
    return {"error": "Failed to clear history"}, 500

@app.delete("/api/history/{idx}")
async def delete_history_item(idx: int):
    success = storage.delete_session(idx)
    if success:
        return {"status": "deleted"}
    return {"error": "Failed to delete history item"}, 404
