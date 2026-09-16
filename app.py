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


def get_history_choices() -> list[tuple[str, str]]:
    """Fetch formatted options for the history dropdown."""
    sessions = storage.load_sessions()
    choices = []
    for s in sessions:
        topic_preview = s['topic'][:40] + ("..." if len(s['topic']) > 40 else "")
        label = f"{s['timestamp']} - {topic_preview}"
        choices.append((label, s['id']))
    return choices


def load_debate_callback(session_id: str):
    """Callback when a user selects a past debate to load."""
    if not session_id:
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    
    sessions = storage.load_sessions()
    session = next((s for s in sessions if s["id"] == session_id), None)
    
    if not session:
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
        
    status = f"✅ Loaded past debate from {session['timestamp']}."
    return (
        session["topic"],
        session["rounds"],
        status,
        _render_transcript(session["transcript"]),
        _render_verdict(session["verdict"])
    )


def clear_debate_callback():
    """Callback when the user clicks + New Debate."""
    return (
        "",
        3,
        "_Ready when you are._",
        "_The debate will appear here…_",
        "_Awaiting the judge's verdict…_",
        None
    )


def debate_handler(topic: str, rounds: int):
    """Gradio streaming callback using a queue to stream token-by-token."""
    if not (topic or "").strip():
        yield "⚠️ Please enter a debate topic.", "", "", gr.update()
        return

    yield "🚀 Starting debate…", "_The debate will appear here…_", "", gr.update()

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
            yield status, _render_transcript(temp_transcript), _render_verdict(verdict), gr.update()

        elif msg_type == "judge_chunk":
            status = "⚖️ Judge is evaluating the arguments…"
            yield status, _render_transcript(transcript), _render_verdict(data), gr.update()

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
                choices = get_history_choices()
                yield status, _render_transcript(transcript), _render_verdict(verdict), gr.update(choices=choices)
            elif transcript:
                latest = transcript[-1]
                status = f"🗣️ Round {latest['round']}: {latest['speaker']} ({latest['position']}) just argued…"
                yield status, _render_transcript(transcript), _render_verdict(verdict), gr.update()
            else:
                status = "🚀 Starting debate…"
                yield status, _render_transcript(transcript), _render_verdict(verdict), gr.update()

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
            yield f"❌ Error: {detail}", _render_transcript(transcript), _render_verdict(verdict), gr.update()
            break

        elif msg_type == "done":
            break


def build_ui() -> gr.Blocks:
    """Build and return the Gradio Blocks interface for the debate app."""
    with gr.Blocks(title="AI Debate Agent") as demo:
        with gr.Row():
            # LEFT SIDEBAR - HISTORY
            with gr.Column(scale=1, variant="panel"):
                gr.Markdown("### 🗄️ Debate History")
                new_btn = gr.Button("+ New Debate", variant="primary")
                history_dd = gr.Dropdown(
                    choices=get_history_choices(),
                    label="Load Past Debate",
                    interactive=True
                )

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
            outputs=[status, transcript_out, verdict_out, history_dd],
        )
        topic.submit(
            fn=debate_handler,
            inputs=[topic, rounds],
            outputs=[status, transcript_out, verdict_out, history_dd],
        )
        
        history_dd.change(
            fn=load_debate_callback,
            inputs=[history_dd],
            outputs=[topic, rounds, status, transcript_out, verdict_out]
        )
        
        new_btn.click(
            fn=clear_debate_callback,
            inputs=[],
            outputs=[topic, rounds, status, transcript_out, verdict_out, history_dd]
        )

    return demo


if __name__ == "__main__":
    build_ui().launch(server_name="0.0.0.0", theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="rose"))
