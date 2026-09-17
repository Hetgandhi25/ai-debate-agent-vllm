# 🤖 AI Debate Agent (v2.0)

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-B73BFE?style=for-the-badge&logo=vite&logoColor=FFD62E)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![FastAPI](https://img.shields.io/badge/fastapi-109989?style=for-the-badge&logo=FASTAPI&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

A multi-agent AI system where two large language models autonomously debate any topic you give them, while a third impartial AI judge evaluates their logic, evidence, and persuasiveness.

Recently completely re-architected from a basic Gradio script into a **production-ready SaaS application** featuring a modern React frontend and a FastAPI backend with Real-Time Server-Sent Events (SSE) streaming.

---

## ✨ Features

- **Multi-Agent Orchestration**: Powered by **LangGraph**, orchestrating three distinct agent personas (Debater A, Debater B, and the Judge).
- **Real-Time SSE Streaming**: Watch the debate unfold live. FastAPI streams chunks directly from the vLLM engine to the React frontend with zero latency.
- **Modern React + Tailwind UI**: A beautiful, responsive CSS Grid layout built with Vite, TypeScript, and Tailwind CSS.
- **Rich Markdown Formatting**: Debate transcripts are rendered using eact-markdown and @tailwindcss/typography for flawless readability.
- **Robust State Management**: View past debates in a locked-down 'View Only' mode, complete with hover-to-delete history management, just like modern AI products.
- **Bring Your Own LLM**: Connects to any local or remote OpenAI-compatible endpoint (like vLLM, Ollama, or OpenAI).

---

## 🏗️ Architecture

The system is separated into a strict Client-Server model:

1. **Frontend (Vite/React)**: Manages UI state, history sidebar, and parses the SSE stream using native etch and TextDecoder.
2. **Backend (FastAPI)**: Serves a REST API for history management and a POST endpoint that executes the LangGraph workflow, bridging synchronous generator queues to asynchronous HTTP streams.
3. **Orchestrator (LangGraph)**: Manages the cyclical graph state (DebateState), passing the context window back and forth between the debaters before handing it to the judge.
4. **LLM Engine (vLLM)**: Executes the actual inference for the agents.

### Agentic Workflow Diagram

`mermaid
sequenceDiagram
    participant UI as React Frontend
    participant API as FastAPI Backend
    participant Orchestrator as LangGraph
    participant Model as vLLM Endpoint

    UI->>API: POST /api/debate/stream {topic, rounds}
    API->>Orchestrator: Initialize DebateState
    loop For Each Round
        Orchestrator->>Model: Prompt (Position + Transcript)
        Model-->>API: Stream Chunk (SSE)
        API-->>UI: Render live text
    end
    Orchestrator->>Model: Prompt Judge (Full Transcript)
    Model-->>API: Stream JSON Verdict
    API-->>UI: Display Winner & Scores
`

---

## 🚀 Getting Started

### 1. Prerequisites
- Node.js (v18+)
- Python (3.10+)
- A running OpenAI-compatible API server (e.g., vLLM or Ollama).

### 2. Backend Setup (FastAPI + LangGraph)
\\\ash
# Clone the repository
git clone https://github.com/Hetgandhi25/ai-debate-agent-vllm.git
cd ai-debate-agent-vllm

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Configure your LLM endpoint
cp .env.example .env
# Edit .env with your VLLM_BASE_URL, VLLM_API_KEY, and VLLM_MODEL

# Start the FastAPI server
uvicorn main:app --reload
\\\

### 3. Frontend Setup (React + Vite)
Open a **new terminal window**:
\\\ash
cd ai-debate-agent-vllm/frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
\\\

Navigate to \http://localhost:5173\ in your browser to start using the AI Debate Agent!

---

## 📂 Project Structure

\\\	ext
ai_debate_agent_vllm/
├── main.py                 # FastAPI application and SSE streaming routes
├── debate.py               # LangGraph multi-agent logic
├── storage.py              # Local JSON history storage logic
├── .env                    # LLM Configuration
├── frontend/               # React + Vite application
│   ├── src/
│   │   ├── components/     # React UI Components (Sidebar, Transcript, Config, etc.)
│   │   ├── services/       # Axios API client
│   │   ├── types/          # TypeScript interfaces
│   │   ├── App.tsx         # Main React shell and state logic
│   │   └── index.css       # Tailwind directives & Custom Scrollbars
│   ├── package.json
│   └── tailwind.config.js
\\\

---
*Built for the future of multi-agent interactions.*