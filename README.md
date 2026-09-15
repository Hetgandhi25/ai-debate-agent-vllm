# AI Debate Agent

> Two LLM debaters argue opposing sides of any topic you choose; a judge scores every turn and declares a winner.

## Overview

AI Debate Agent is a multi-agent application that runs structured debates between two language models and an impartial judge. You supply a topic and round count (1 to 5); Debater A argues for, Debater B argues against, and they alternate while responding to each other's latest points. When rounds finish, a judge reviews the full transcript, scores each argument on logic, evidence, and persuasiveness, and returns a winner with a written verdict. The Gradio interface streams the transcript live as each agent speaks.

## Demo

![Demo](assets/demo.png)

## Features

- **Dual debaters** with fixed roles: Debater A (For) and Debater B (Against)
- **Configurable rounds** from 1 to 5, with each round consisting of one turn per debater
- **Context-aware rebuttals** where each debater sees the full transcript before speaking
- **Impartial judge** that scores every argument and declares a winner with reasoning
- **Live streaming UI** that updates the transcript and status after each agent turn
- **Configurable API** for local inference via **vLLM** (OpenAI-compatible)
- **Optional connectivity test** (`test_vllm.py`) to verify the vLLM server before launching the app

## Tech Stack

**Frameworks & Libraries:**

- [LangGraph](https://langchain-ai.github.io/langgraph/) for multi-agent orchestration
- [LangChain Core](https://python.langchain.com/) for graph state typing
- [OpenAI Python SDK](https://github.com/openai/openai-python) (vLLM-compatible client)
- [Gradio](https://www.gradio.app/) for the web UI
- [python-dotenv](https://github.com/theskumar/python-dotenv) for environment configuration

**Additional Tools:**

- **Orchestration:** LangGraph
- **Web Framework:** Gradio
- **Model Backend:** A vLLM server providing an OpenAI-compatible API endpoint

| Agent | Role | Default model |
|-------|------|-------------------------|
| Debater A | For | Configurable `VLLM_MODEL` |
| Debater B | Against | Configurable `VLLM_MODEL` |
| Judge | Scoring and verdict | Configurable `VLLM_MODEL` |

## Prerequisites

- Python 3.10 or higher
- A running vLLM server exposing an OpenAI-compatible API (e.g. `http://<VLLM_IP>:<PORT>/v1`)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Sumanth077/Hands-On-AI-Engineering.git
cd Hands-On-AI-Engineering/ai_agents/ai_debate_agent
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv
```

**Windows:**

```bash
venv\Scripts\activate
```

**macOS/Linux:**

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and configure your vLLM API details:

```env
VLLM_BASE_URL=http://<MY-VLLM-IP>:<PORT>/v1
VLLM_API_KEY=<MY_API_KEY>
VLLM_MODEL=<MY_MODEL_NAME>
```

Verify connectivity (optional):

```bash
python test_vllm.py
```

## Usage

### Running the Application

```bash
python app.py
```

Open the local URL shown in the terminal (typically `http://127.0.0.1:7860`). Enter a debate topic, select the number of rounds (1 to 5), and click **Start Debate**.

### Example Usage

| Debate topic | Rounds | What you get |
|--------------|--------|--------------|
| Social media does more harm than good | 3 | Alternating For/Against arguments across 3 rounds, then a judge verdict with per-argument scores and a declared winner |
| Remote work is better than working in an office | 2 | Two rounds of rebuttals, streamed transcript, and a scored breakdown (logic, evidence, persuasiveness) |
| Artificial intelligence should be heavily regulated | 3 | Full debate transcript with live updates, total scores per debater, and written judge reasoning |
| Space exploration is worth the cost | 2 | Concise two-round debate ending in a winner (Debater A, Debater B, or Tie) and comments per argument |

**Typical output sections:**

1. **Debate transcript** (markdown): each round labeled with Debater A (For) or Debater B (Against)
2. **Judge's verdict**: score table, totals, winner, and short explanation

## Project Structure

```text
ai_debate_agent/
├── app.py              # Gradio UI and streaming debate handler
├── debate.py           # LangGraph graph (Debater A, Debater B, Judge)
├── test_vllm.py        # Smoke test for vLLM connectivity
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore
├── README.md
└── assets/
    └── demo.png        # Demo screenshot for the README
```

## How It Works

1. **Topic input**  
   The user enters a topic and round count in Gradio. `debate_handler` in `app.py` calls `run_debate()` in `debate.py`.

2. **Graph setup**  
   LangGraph builds a stateful graph with shared `DebateState`: topic, `max_rounds`, `round_num`, `transcript`, and `verdict`. All three agents use one shared vLLM client initialized with `VLLM_BASE_URL`.

3. **Debater A (For)**  
   The first node calls the vLLM model with the topic and an empty transcript. The model returns the opening argument for the For side.

4. **Debater B (Against)**  
   The second node calls the vLLM model with the transcript including Debater A's latest turn. It returns the Against argument and increments `round_num`.

5. **Round loop**  
   A conditional edge checks `round_num <= max_rounds`. If more rounds remain, control returns to Debater A with the updated transcript. Each debater is prompted to rebut the opponent's most recent point. If rounds are complete, the graph routes to the judge.

6. **Judge**  
   The judge node sends the full transcript to the vLLM model with a structured JSON scoring prompt. Each argument receives scores (1 to 10) for logic, evidence, and persuasiveness. The app parses the response, recomputes totals, and sets the winner and verdict text.

7. **Streaming to the UI**  
   The graph runs with `stream_mode="values"`. After every node, `run_debate` yields the current state. Gradio renders the transcript and verdict panels incrementally until the debate completes.

**Graph flow:**

```text
START -> debater_a -> debater_b -> (more rounds? -> debater_a : judge) -> END
```
