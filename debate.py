"""LangGraph multi-agent debate graph.

Three agents collaborate on a single graph:

* **Debater A** - argues the "for" position (via vLLM API).
* **Debater B** - argues the "against" position (via vLLM API).
* **Judge**     - scores every argument and declares a winner (via vLLM API).

All three agents are routed through a user-configured vLLM OpenAI-compatible API.

The graph alternates A -> B for a configurable number of rounds, then routes to the
judge. ``run_debate`` is a generator so the UI can stream the debate as it unfolds.
"""

from __future__ import annotations

import json
import os
import re
from typing import Iterator, List, Optional, TypedDict, Any

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

load_dotenv()

# Position labels used throughout the transcript and prompts.
FOR = "For"
AGAINST = "Against"
DEBATER_A = "Debater A"
DEBATER_B = "Debater B"


class Argument(TypedDict):
    """A single turn in the debate."""

    speaker: str  # "Debater A" or "Debater B"
    position: str  # "For" or "Against"
    round: int
    content: str


class DebateState(TypedDict, total=False):
    """Shared state passed between every node in the graph."""

    topic: str
    max_rounds: int
    round_num: int
    transcript: List[Argument]
    verdict: dict
    q: Any


# --------------------------------------------------------------------------- #
# Model factory
# --------------------------------------------------------------------------- #
# All three agents use the same vLLM model. Roles are enforced via system prompts.
VLLM_MODEL = os.getenv("VLLM_MODEL", "<MY_MODEL_NAME>")

def _vllm_client():
    """Shared vLLM router client used by every agent."""
    from openai import OpenAI

    base_url = os.getenv("VLLM_BASE_URL")
    api_key = os.getenv("VLLM_API_KEY", "EMPTY")
    if not base_url or "<MY-VLLM-IP>" in base_url:
        raise RuntimeError(
            "VLLM_BASE_URL is not set properly. Copy .env.example to .env and configure it."
        )
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
    )


# --------------------------------------------------------------------------- #
# Prompt helpers
# --------------------------------------------------------------------------- #
def _history_block(transcript: List[Argument]) -> str:
    """Render the debate so far as plain text for the next debater."""
    if not transcript:
        return "(No arguments yet - you are opening the debate.)"
    lines = []
    for arg in transcript:
        lines.append(f"[Round {arg['round']}] {arg['speaker']} ({arg['position']}):\n{arg['content']}")
    return "\n\n".join(lines)


def _debater_system_prompt(position: str, topic: str) -> str:
    """Return the system prompt assigning a debater to its position on the given topic."""
    return (
        f"You are a sharp, persuasive debater arguing the **{position.upper()}** position "
        f'on the topic: "{topic}".\n'
        "Make a focused, well-structured case. Use clear logic, concrete evidence or "
        "examples, and rhetorical persuasion. Directly rebut your opponent's most recent "
        "point when one exists. Stay on your assigned side at all times. Keep each turn to "
        "roughly 120-180 words and do not break character or mention that you are an AI."
    )


def _debater_user_prompt(position: str, round_num: int, transcript: List[Argument]) -> str:
    """Return the user-turn prompt instructing the debater to deliver their argument for this round."""
    return (
        f"Debate so far:\n\n{_history_block(transcript)}\n\n"
        f"It is now round {round_num}. Deliver your {position} argument."
    )


# --------------------------------------------------------------------------- #
# Graph nodes
# --------------------------------------------------------------------------- #
def _debater_a_node(state: DebateState) -> DebateState:
    """Call Debater A's model and append its For-side argument to the transcript."""
    client = _vllm_client()
    round_num = state["round_num"]
    messages = [
        {"role": "system", "content": _debater_system_prompt(FOR, state["topic"])},
        {"role": "user", "content": _debater_user_prompt(FOR, round_num, state["transcript"])},
    ]
    response = client.chat.completions.create(
        model=VLLM_MODEL,
        messages=messages,
        temperature=0.7,
        top_p=0.8,
        presence_penalty=1.5,
        max_tokens=512,
        stream=True,
        extra_body={
            "top_k": 20,
            "min_p": 0.0,
            "repetition_penalty": 1.0,
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )
    
    q = state.get("q")
    content = ""
    for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content or ""
        if delta:
            content += delta
            if q:
                q.put(("chunk", {
                    "speaker": DEBATER_A,
                    "position": FOR,
                    "round": round_num,
                    "content": content
                }))

    argument: Argument = {
        "speaker": DEBATER_A,
        "position": FOR,
        "round": round_num,
        "content": content.strip(),
    }
    return {"transcript": state["transcript"] + [argument]}


def _debater_b_node(state: DebateState) -> DebateState:
    """Call Debater B's model, append its Against-side argument, and increment the round counter."""
    client = _vllm_client()
    round_num = state["round_num"]
    messages = [
        {"role": "system", "content": _debater_system_prompt(AGAINST, state["topic"])},
        {"role": "user", "content": _debater_user_prompt(AGAINST, round_num, state["transcript"])},
    ]
    response = client.chat.completions.create(
        model=VLLM_MODEL,
        messages=messages,
        temperature=0.7,
        top_p=0.8,
        presence_penalty=1.5,
        max_tokens=512,
        stream=True,
        extra_body={
            "top_k": 20,
            "min_p": 0.0,
            "repetition_penalty": 1.0,
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )
    
    q = state.get("q")
    content = ""
    for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content or ""
        if delta:
            content += delta
            if q:
                q.put(("chunk", {
                    "speaker": DEBATER_B,
                    "position": AGAINST,
                    "round": round_num,
                    "content": content
                }))

    argument: Argument = {
        "speaker": DEBATER_B,
        "position": AGAINST,
        "round": round_num,
        "content": content.strip(),
    }
    return {
        "transcript": state["transcript"] + [argument],
        "round_num": round_num + 1,
    }


def _route_after_b(state: DebateState) -> str:
    """Loop back for another round, or hand off to the judge."""
    if state["round_num"] <= state["max_rounds"]:
        return "continue"
    return "judge"


_JUDGE_SYSTEM = (
    "You are an impartial debate judge. Score every argument on three criteria, each from "
    "1 to 10: logic, evidence, and persuasiveness. Be fair and consistent. After scoring, "
    "tally totals for each debater, declare a single winner, and write a concise verdict.\n\n"
    "Respond with ONLY valid JSON in exactly this shape (no markdown, no extra text):\n"
    "{\n"
    '  "arguments": [\n'
    '    {"speaker": "Debater A", "round": 1, "logic": 8, "evidence": 7, '
    '"persuasiveness": 9, "comment": "..."}\n'
    "  ],\n"
    '  "totals": {"Debater A": 0, "Debater B": 0},\n'
    '  "winner": "Debater A" | "Debater B" | "Tie",\n'
    '  "verdict": "A few sentences explaining the decision."\n'
    "}"
)


def _judge_node(state: DebateState) -> DebateState:
    client = _vllm_client()
    transcript_text = _history_block(state["transcript"])
    messages = [
        {"role": "system", "content": _JUDGE_SYSTEM},
        {
            "role": "user",
            "content": (
                f'Topic: "{state["topic"]}"\n'
                f"Debater A argued FOR; Debater B argued AGAINST.\n\n"
                f"Full transcript:\n\n{transcript_text}\n\n"
                "Score each argument and declare the winner now."
            ),
        },
    ]
    response = client.chat.completions.create(
        model=VLLM_MODEL,
        messages=messages,
        temperature=0.7,
        top_p=0.8,
        max_tokens=1024,
        stream=True,
        extra_body={
            "top_k": 20,
            "min_p": 0.0,
            "repetition_penalty": 1.0,
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )
    
    q = state.get("q")
    content = ""
    for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content or ""
        if delta:
            content += delta
            if q:
                q.put(("judge_chunk", content))
                
    return {"verdict": _parse_verdict(content, state["transcript"])}


# --------------------------------------------------------------------------- #
# Verdict parsing
# --------------------------------------------------------------------------- #
def _parse_verdict(raw: str, transcript: List[Argument]) -> dict:
    """Best-effort extraction of the judge's JSON, with graceful fallbacks."""
    parsed: Optional[dict] = None
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        json_str = match.group(0)
        # Attempt to clean up common JSON typos made by LLMs (e.g. trailing commas, extra quotes after digits)
        json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
        json_str = re.sub(r'(:\s*\d+)"\s*(,|})', r'\1\2', json_str)
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            parsed = None

    # If JSON parsing still fails, do a best-effort Regex extraction
    if not isinstance(parsed, dict):
        parsed = {
            "arguments": [],
            "totals": {DEBATER_A: 0, DEBATER_B: 0},
            "winner": "Tie",
            "verdict": "",
            "raw": raw.strip()
        }
        
        # Extract winner
        w_match = re.search(r'"winner"\s*:\s*"(Debater A|Debater B|Tie)"', raw, re.IGNORECASE)
        if w_match:
            parsed["winner"] = w_match.group(1)
            
        # Extract verdict
        v_match = re.search(r'"verdict"\s*:\s*"(.*?)"\s*\}?\s*$', raw, re.DOTALL | re.IGNORECASE)
        if v_match:
            parsed["verdict"] = v_match.group(1).strip()
        else:
            parsed["verdict"] = raw.strip()
            
        # Extract arguments
        arg_pattern = r'"speaker"\s*:\s*"(Debater [AB])".*?"round"\s*:\s*(\d+).*?"logic"\s*:\s*(\d+).*?"evidence"\s*:\s*(\d+).*?"persuasiveness"\s*:\s*(\d+).*?"comment"\s*:\s*"(.*?)"'
        for m in re.finditer(arg_pattern, raw, re.DOTALL | re.IGNORECASE):
            parsed["arguments"].append({
                "speaker": m.group(1),
                "round": int(m.group(2)),
                "logic": int(m.group(3)),
                "evidence": int(m.group(4)),
                "persuasiveness": int(m.group(5)),
                "comment": m.group(6)
            })

    # Recompute totals from per-argument scores when possible (more reliable than the LLM's math).
    totals = {DEBATER_A: 0, DEBATER_B: 0}
    for arg in parsed.get("arguments", []):
        speaker = arg.get("speaker")
        if speaker in totals:
            totals[speaker] += (
                int(arg.get("logic", 0))
                + int(arg.get("evidence", 0))
                + int(arg.get("persuasiveness", 0))
            )
    if any(totals.values()):
        parsed["totals"] = totals
        if totals[DEBATER_A] > totals[DEBATER_B]:
            parsed.setdefault("winner", DEBATER_A)
        elif totals[DEBATER_B] > totals[DEBATER_A]:
            parsed.setdefault("winner", DEBATER_B)

    parsed.setdefault("totals", totals)
    parsed.setdefault("winner", "Tie")
    parsed.setdefault("verdict", "")
    parsed.setdefault("arguments", [])
    return parsed


# --------------------------------------------------------------------------- #
# Graph assembly
# --------------------------------------------------------------------------- #
def build_graph():
    """Construct and compile the debate graph."""
    graph = StateGraph(DebateState)
    graph.add_node("debater_a", _debater_a_node)
    graph.add_node("debater_b", _debater_b_node)
    graph.add_node("judge", _judge_node)

    graph.add_edge(START, "debater_a")
    graph.add_edge("debater_a", "debater_b")
    graph.add_conditional_edges(
        "debater_b",
        _route_after_b,
        {"continue": "debater_a", "judge": "judge"},
    )
    graph.add_edge("judge", END)
    return graph.compile()


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def run_debate(topic: str, rounds: int, q: Any = None) -> Iterator[DebateState]:
    """Run the debate, yielding the full state after each agent turn.

    Args:
        topic: The debate topic supplied by the user.
        rounds: Number of rounds (1-5). Each round is one A turn + one B turn.
        q: Optional thread-safe queue to emit streaming chunks into.

    Yields:
        The accumulated :class:`DebateState` after every node, ending with a
        state that contains the judge's ``verdict``.
    """
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("Please enter a debate topic.")
    rounds = max(1, min(5, int(rounds)))

    app = build_graph()
    initial: DebateState = {
        "topic": topic,
        "max_rounds": rounds,
        "round_num": 1,
        "transcript": [],
        "verdict": {},
        "q": q,
    }
    # stream_mode="values" emits the full state snapshot after each node runs.
    for state in app.stream(initial, stream_mode="values"):
        if q:
            q.put(("state_full", state))
        yield state
