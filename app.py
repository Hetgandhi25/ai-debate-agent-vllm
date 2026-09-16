"""Gradio UI for the AI Debate Agent.

Two LLM agents argue opposing sides of a user-defined topic for a configurable
number of rounds, and a judge agent scores each argument and declares a winner.
The transcript streams in live as each agent takes its turn.
"""

from __future__ import annotations

import threading
from queue import Queue
import gradio as gr

from debate import (
    AGAINST,
    DEBATER_A,
    DEBATER_B,
    FOR,
    VLLM_MODEL,
    run_debate,
)
import storage

MAX_HISTORY_BTNS = 20


def _render_transcript(transcript: list[dict]) -> str:
    """Format the running transcript as markdown."""
    if not transcript:
        return "_The debate will appear here…_"
    blocks = []
    for arg in transcript:
        if arg["speaker"] == DEBATER_A:
            badge = f"🟦 **{DEBATER_A} · {FOR}**"
        else:
            badge = f"🟥 **{DEBATER_B} · {AGAINST}**"
        blocks.append(
            f"### Round {arg['round']} - {badge}\n\n{arg['content']}"
        )
    return "\n\n---\n\n".join(blocks)


def _render_verdict(verdict: dict | str) -> str:
    """Format the judge's verdict as markdown."""
    if not verdict:
        return "_Awaiting the judge's verdict…_"

    # If it's a string, it means the judge is currently streaming its raw JSON
    if isinstance(verdict, str):
        return f"## ⚖️ Judge is deliberating ({VLLM_MODEL})...\n\n```json\n{verdict}\n```"

    totals = verdict.get("totals", {})
    a_total = totals.get(DEBATER_A, 0)
    b_total = totals.get(DEBATER_B, 0)
    winner = verdict.get("winner", "Tie")

    if winner == DEBATER_A:
        headline = f"🏆 Winner: **{DEBATER_A} ({FOR})**"
    elif winner == DEBATER_B:
        headline = f"🏆 Winner: **{DEBATER_B} ({AGAINST})**"
    else:
        headline = "🤝 Result: **Tie**"

    lines = [
        f"## ⚖️ Judge's Verdict ({VLLM_MODEL})",
        "",
        headline,
        "",
        f"**Total scores** - {DEBATER_A} (For): `{a_total}` · {DEBATER_B} (Against): `{b_total}`",
        "",
    ]

    args = verdict.get("arguments", [])
    if args:
        lines.append("### Score breakdown")
        lines.append("")
        lines.append("| Round | Debater | Logic | Evidence | Persuasion | Notes |")
        lines.append("|:-----:|:--------|:-----:|:--------:|:----------:|:------|")
        for a in args:
            lines.append(
                f"| {a.get('round', '-')} | {a.get('speaker', '-')} "
                f"| {a.get('logic', '-')} | {a.get('evidence', '-')} "
                f"| {a.get('persuasiveness', '-')} | {a.get('comment', '')} |"
            )
        lines.append("")

    if verdict.get("verdict"):
        lines.append("### Reasoning")
        lines.append("")
        lines.append(verdict["verdict"])

    return "\n".join(lines)


def get_history_button_updates():
    """Fetch history and return updates for the fixed pool of sidebar buttons."""
    sessions = storage.load_sessions()
    updates = []
    for i in range(MAX_HISTORY_BTNS):
        if i < len(sessions):
            s = sessions[i]
            title = s["topic"]
            if len(title) > 35:
                title = title[:35] + "..."
            updates.append(gr.update(visible=True, value=title))
        else:
            updates.append(gr.update(visible=False, value=""))
    return updates


def load_debate_by_index(idx: int):
    """Callback when a user clicks a specific history button."""
    sessions = storage.load_sessions()
    if idx < len(sessions):
        session = sessions[idx]
        status = f"✅ Loaded past debate from {session['timestamp']}."
        return (
            session["topic"],
            session["rounds"],
            status,
            _render_transcript(session["transcript"]),
            _render_verdict(session["verdict"])
        )
    return gr.update(), gr.update(), gr.update(), gr.update(), gr.update()


def clear_debate_callback():
    """Callback when the user clicks + New Debate."""
    return (
        "",
        3,
        "_Ready when you are._",
        "_The debate will appear here…_",
        "_Awaiting the judge's verdict…_"
    )


def debate_handler(topic: str, rounds: int):
    """Gradio streaming callback using a queue to stream token-by-token."""
    empty_history = [gr.update() for _ in range(MAX_HISTORY_BTNS)]
    
    if not (topic or "").strip():
        yield tuple(["⚠️ Please enter a debate topic.", "", ""] + empty_history)
        return

    yield tuple(["🚀 Starting debate…", "_The debate will appear here…_", ""] + empty_history)

    q = Queue()

    def run_graph():
        try:
            for _ in run_debate(topic, rounds, q=q):
                pass
            q.put(("done", None))
        except Exception as exc:
            q.put(("error", exc))

    threading.Thread(target=run_graph, daemon=True).start()

    transcript = []
    verdict = {}

    while True:
        msg_type, data = q.get()

        if msg_type == "chunk":
            temp_transcript = transcript + [data]
            status = f"🗣️ Round {data['round']}: {data['speaker']} ({data['position']}) is arguing…"
            yield tuple([status, _render_transcript(temp_transcript), _render_verdict(verdict)] + empty_history)

        elif msg_type == "judge_chunk":
            status = "⚖️ Judge is evaluating the arguments…"
            yield tuple([status, _render_transcript(transcript), _render_verdict(data)] + empty_history)

        elif msg_type == "state_full":
            state = data
            if "transcript" in state:
                transcript = state["transcript"]
            if "verdict" in state and state["verdict"]:
                verdict = state["verdict"]

            if verdict:
                status = "✅ Debate complete - verdict delivered."
                # Save session to history only when complete
                storage.save_session(topic, rounds, transcript, verdict)
                btn_updates = get_history_button_updates()
                yield tuple([status, _render_transcript(transcript), _render_verdict(verdict)] + btn_updates)
            elif transcript:
                latest = transcript[-1]
                status = f"🗣️ Round {latest['round']}: {latest['speaker']} ({latest['position']}) just argued…"
                yield tuple([status, _render_transcript(transcript), _render_verdict(verdict)] + empty_history)
            else:
                status = "🚀 Starting debate…"
                yield tuple([status, _render_transcript(transcript), _render_verdict(verdict)] + empty_history)

        elif msg_type == "error":
            exc = data
            from openai import APIConnectionError, APITimeoutError, NotFoundError
            
            if isinstance(exc, APIConnectionError):
                detail = f"Could not connect to vLLM server: {exc}"
            elif isinstance(exc, APITimeoutError):
                detail = f"vLLM server timed out: {exc}"
            elif isinstance(exc, NotFoundError):
                detail = f"Invalid model name or endpoint not found: {exc}"
            else:
                detail = str(exc).strip() or type(exc).__name__
                cause = exc.__cause__
                if cause and str(cause) not in detail:
                    detail = f"{detail} - {cause}"
            yield tuple([f"❌ Error: {detail}", _render_transcript(transcript), _render_verdict(verdict)] + empty_history)
            break

        elif msg_type == "done":
            break


def build_ui() -> gr.Blocks:
    """Build and return the Gradio Blocks interface for the debate app."""
    css = """
    .chat-history-btn { 
        text-align: left !important; 
        justify-content: flex-start !important; 
        overflow: hidden !important; 
        text-overflow: ellipsis !important; 
        white-space: nowrap !important;
        margin-bottom: 5px !important;
        background: transparent !important;
        border: 1px solid #333 !important;
    }
    .chat-history-btn:hover {
        background: #2a2a2a !important;
    }
    """
    
    with gr.Blocks(title="AI Debate Agent", css=css) as demo:
        with gr.Row():
            # LEFT SIDEBAR - HISTORY (ChatGPT Style)
            with gr.Column(scale=1, variant="panel"):
                new_btn = gr.Button("+ New Debate", variant="primary")
                gr.Markdown("### 🗄️ Recent Debates")
                
                # Pool of buttons to mimic a chat history list
                history_buttons = []
                for i in range(MAX_HISTORY_BTNS):
                    btn = gr.Button("", visible=False, elem_classes="chat-history-btn")
                    history_buttons.append(btn)

            # MAIN CONTENT AREA
            with gr.Column(scale=3):
                gr.Markdown(
                    f"""
                    # 🎙️ AI Debate Agent
                    Two LLM agents argue opposing sides of your topic; a judge scores every
                    argument and declares a winner.

                    - 🟦 **Debater A - For** · `{VLLM_MODEL}`
                    - 🟥 **Debater B - Against** · `{VLLM_MODEL}`
                    - ⚖️ **Judge** · `{VLLM_MODEL}`

                    All three agents are routed through a local **vLLM OpenAI-Compatible API**.
                    """
                )

                with gr.Row():
                    with gr.Column(scale=2):
                        topic = gr.Textbox(
                            label="Debate topic",
                            placeholder="e.g. Social media does more harm than good",
                            lines=2,
                        )
                    with gr.Column(scale=1):
                        rounds = gr.Slider(
                            label="Number of rounds",
                            minimum=1,
                            maximum=5,
                            step=1,
                            value=3,
                        )

                run_btn = gr.Button("Start Debate", variant="primary")
                status = gr.Markdown("_Ready when you are._")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("## 🗣️ Debate transcript")
                        transcript_out = gr.Markdown("_The debate will appear here…_")
                    with gr.Column():
                        gr.Markdown("## 🏆 Result")
                        verdict_out = gr.Markdown("_Awaiting the judge's verdict…_")

        # Events
        run_btn.click(
            fn=debate_handler,
            inputs=[topic, rounds],
            outputs=[status, transcript_out, verdict_out] + history_buttons,
        )
        topic.submit(
            fn=debate_handler,
            inputs=[topic, rounds],
            outputs=[status, transcript_out, verdict_out] + history_buttons,
        )
        
        # History button click events
        for i, btn in enumerate(history_buttons):
            def make_handler(idx):
                return lambda: load_debate_by_index(idx)
                
            btn.click(
                fn=make_handler(i),
                inputs=[],
                outputs=[topic, rounds, status, transcript_out, verdict_out]
            )
        
        new_btn.click(
            fn=clear_debate_callback,
            inputs=[],
            outputs=[topic, rounds, status, transcript_out, verdict_out]
        )

        # Update history on load/refresh
        demo.load(
            fn=get_history_button_updates,
            inputs=None,
            outputs=history_buttons
        )

    return demo


if __name__ == "__main__":
    build_ui().launch(server_name="0.0.0.0", theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="rose"))
