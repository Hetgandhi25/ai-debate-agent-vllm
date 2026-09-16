import json
import os
import uuid
from datetime import datetime

STORAGE_FILE = "sessions.json"

def load_sessions() -> list[dict]:
    """Load all saved debate sessions from the local JSON file."""
    if not os.path.exists(STORAGE_FILE):
        return []
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_session(topic: str, rounds: int, transcript: list, verdict: dict) -> dict:
    """Save a completed debate session to the local JSON file."""
    sessions = load_sessions()
    
    session = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic": topic,
        "rounds": rounds,
        "transcript": transcript,
        "verdict": verdict
    }
    
    # Insert at the beginning so the newest is always first
    sessions.insert(0, session)
    
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)
        
    return session
