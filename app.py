"""Gradio UI for the AI Debate Agent — production SaaS UI.

Architecture
────────────
* Sidebar history: single ``gr.HTML`` block with inline onclick that sets a
  hidden ``gr.Number``.  ``gr.Number.change`` fires the Python ``load_debate``
  callback.
* Transcript / Verdict: ``gr.HTML`` fed by Python HTML-string generators.
* Copy / Download: JS clipboard / Blob APIs via gr.Button(js=…).
* No Browse Debates, Settings, or Search in the sidebar.
"""

from __future__ import annotations

import threading
from datetime import datetime
from queue import Queue

import gradio as gr

from debate import AGAINST, DEBATER_A, DEBATER_B, FOR, VLLM_MODEL, run_debate
import storage

MAX_HISTORY = 20

# ─────────────────────────────────────────────────────────────────────────────
#  Design tokens
# ─────────────────────────────────────────────────────────────────────────────
_AVATAR_COLORS = [
    "#4F7FFF", "#E11D68", "#059669", "#D97706",
    "#6C4DFF", "#0891B2", "#EA580C",
]

CSS = r"""
/* ═══════════════════════════════════════════════════════════════════════════
   AI DEBATE AGENT — Design System CSS
   ═══════════════════════════════════════════════════════════════════════════ */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
    height: 100%; width: 100vw;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #F5F7FC;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden !important; /* Force no horizontal scroll */
    margin: 0; padding: 0;
}

/* ── Gradio Overrides ── */
.gradio-container {
    font-family: 'Inter', sans-serif !important;
    background: #F5F7FC !important;
    max-width: 100vw !important;
    width: 100vw !important;
    min-width: 100vw !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow-x: hidden !important;
}
.gradio-container > .main,
.gradio-container > .main > .wrap {
    padding: 0 !important; margin: 0 !important;
    width: 100% !important; max-width: 100% !important; gap: 0 !important;
    overflow-x: hidden !important;
}
footer { display: none !important; }

/* ── App Shell ── */
.app-shell {
    display: flex !important;
    flex-direction: row !important;
    width: 100vw !important;
    min-height: 100vh !important;
    align-items: stretch !important;
    flex-wrap: nowrap !important;
    background: #F5F7FC !important;
    margin: 0 !important; padding: 0 !important;
    overflow-x: hidden !important;
}
.app-shell > .wrap, .app-shell > div {
    display: flex !important;
    flex-direction: row !important;
    width: 100% !important;
    align-items: stretch !important;
    flex-wrap: nowrap !important;
    gap: 0 !important;
    margin: 0 !important; padding: 0 !important;
}

/* ── Sidebar ── */
.sidebar {
    width: 280px !important; min-width: 280px !important; max-width: 280px !important;
    background: #111A36 !important;
    padding: 24px !important;
    display: flex !important; flex-direction: column !important;
    border: none !important; border-radius: 0 !important;
    height: 100vh !important;
    position: sticky !important; top: 0 !important;
    overflow-y: auto !important; overflow-x: hidden !important;
}
.sidebar > .wrap, .sidebar > .form { gap: 0 !important; padding: 0 !important; display: flex !important; flex-direction: column !important; height: 100% !important; }

.sb-logo { display: flex; align-items: center; gap: 12px; margin-bottom: 28px; }
.sb-logo-icon {
    width: 44px; height: 44px; border-radius: 12px;
    background: linear-gradient(135deg, #6C4DFF, #4F7FFF);
    display: flex; justify-content: center; align-items: center;
    font-size: 22px; flex-shrink: 0; box-shadow: 0 6px 20px rgba(108,77,255,.35);
}
.sb-logo-text h3 { color: #fff; font-size: 17px; font-weight: 700; line-height: 1.25; }
.sb-logo-text p { color: #7B8DB5; font-size: 12px; margin-top: 3px; line-height: 1.4; }

.new-debate-btn, .new-debate-btn button {
    width: 100% !important; height: 50px !important;
    background: linear-gradient(135deg, #6C4DFF, #4F7FFF) !important;
    color: #fff !important; border: none !important; border-radius: 12px !important;
    font-size: 15px !important; font-weight: 700 !important;
    cursor: pointer !important; box-shadow: 0 6px 20px rgba(79,127,255,.3) !important;
    margin-bottom: 32px !important;
    display: flex !important; justify-content: center !important; align-items: center !important;
    transition: transform .15s !important; margin-left: 0 !important; margin-right: 0 !important;
}
.new-debate-btn button:hover { transform: translateY(-1px) !important; }

.sb-section-label {
    color: #5A6E94; font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px;
}

.hist-html .hist-card {
    display: flex; align-items: center; gap: 12px;
    background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.06);
    border-radius: 12px; padding: 12px 14px; cursor: pointer;
    margin-bottom: 8px; transition: background .15s, border-color .15s;
}
.hist-html .hist-card:hover { background: rgba(255,255,255,.09); }
.hist-html .hist-card.active {
    background: rgba(108,77,255,.16) !important;
    border-color: rgba(108,77,255,.45) !important;
}
.hist-html .hist-avatar {
    width: 38px; height: 38px; border-radius: 50%;
    display: flex; justify-content: center; align-items: center;
    font-size: 15px; font-weight: 700; color: #fff; flex-shrink: 0;
}
.hist-html .hist-body { flex: 1; min-width: 0; }
.hist-html .hist-title { color: #E2E8F0; font-size: 14px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 3px; }
.hist-html .hist-date { color: #5A6E94; font-size: 11px; font-weight: 500; }

.sb-quote {
    margin-top: auto; background: rgba(108,77,255,.10);
    border-left: 3px solid #6C4DFF; border-radius: 0 10px 10px 0;
    padding: 16px; color: #7B8DB5; font-size: 13px; font-style: italic; line-height: 1.5;
}
.hist-trigger { display: none !important; }

/* ── Main Content ── */
.main-content {
    flex: 1 !important; min-width: 0 !important; width: calc(100vw - 280px) !important; max-width: calc(100vw - 280px) !important;
    padding: 32px 40px !important; background: #F5F7FC !important;
    display: flex !important; flex-direction: column !important;
    overflow-y: auto !important; overflow-x: hidden !important; height: 100vh !important;
}
.main-content > .wrap { display: flex !important; flex-direction: column !important; gap: 0 !important; overflow-x: hidden !important; width: 100% !important; }

.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
.ph-title { font-size: 38px; font-weight: 800; color: #17213D; letter-spacing: -.6px; line-height: 1.05; }
.ph-title .ai-accent { background: linear-gradient(90deg, #6C4DFF, #4F7FFF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.ph-sub { font-size: 15px; color: #64708A; margin-top: 6px; }
.ph-right { display: flex; align-items: center; gap: 12px; }
.ph-badge { display: flex; align-items: center; gap: 7px; background: #EDE9FE; color: #5B21B6; font-size: 13px; font-weight: 600; padding: 7px 16px; border-radius: 20px; }
.ph-theme { width: 38px; height: 38px; background: #fff; border: 1px solid #E2E8F0; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 16px; }
.ph-user { display: flex; align-items: center; gap: 9px; background: #fff; border: 1px solid #E2E8F0; border-radius: 30px; padding: 4px 16px 4px 4px; font-size: 14px; font-weight: 600; color: #17213D; }
.ph-user-av { width: 32px; height: 32px; background: linear-gradient(135deg, #8B5CF6, #6C4DFF); color: #fff; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 13px; font-weight: 700; }

/* ── Control Card (Fixed Proportions) ── */
.ctrl-card {
    display: flex !important;
    flex-wrap: nowrap !important;
    gap: 32px !important;
    align-items: end !important;
    background: #fff !important; border: 1px solid #E2E8F0 !important;
    border-radius: 16px !important; box-shadow: 0 2px 12px rgba(0,0,0,.03) !important;
    padding: 24px 32px !important; margin-bottom: 24px !important;
    width: 100% !important; overflow: visible !important;
}
/* If Gradio inserts a wrapper, make the wrapper flex too */
.ctrl-card > .wrap, .ctrl-card > div {
    display: flex !important;
    flex-wrap: nowrap !important;
    gap: 32px !important;
    align-items: end !important;
    width: 100% !important;
    overflow: visible !important;
}

/* Hardcoded percentages so Gradio min-widths cannot expand them */
.ctrl-col-topic  { width: 45% !important; min-width: 0 !important; flex: none !important; margin: 0 !important; padding: 0 !important; border: none !important; background: transparent !important; }
.ctrl-col-rounds { width: 25% !important; min-width: 0 !important; flex: none !important; margin: 0 !important; padding: 0 !important; border: none !important; background: transparent !important; }
.ctrl-col-start  { width: 30% !important; min-width: 0 !important; flex: none !important; margin: 0 !important; padding: 0 !important; border: none !important; background: transparent !important; }

.ctrl-label { font-size: 14px; font-weight: 650; color: #17213D; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }

/* Topic Input - fix the black border issue by stripping internal Gradio backgrounds */
.ctrl-col-topic label { margin: 0 !important; padding: 0 !important; width: 100% !important; display: block !important; background: transparent !important;}
.ctrl-col-topic .container { background: transparent !important; border: none !important; box-shadow: none !important; border-radius: 0 !important; }
.ctrl-col-topic textarea,
.ctrl-col-topic input {
    background: #fff !important; border: 1.5px solid #E2E8F0 !important;
    border-radius: 12px !important; padding: 0 16px !important;
    font-size: 15px !important; color: #17213D !important;
    height: 52px !important; line-height: 52px !important;
    font-family: 'Inter', sans-serif !important; width: 100% !important;
    box-sizing: border-box !important; resize: none !important; box-shadow: none !important; margin: 0 !important;
}
.ctrl-col-topic textarea:focus, .ctrl-col-topic input:focus { border-color: #6C4DFF !important; outline: none !important; box-shadow: 0 0 0 3px rgba(108,77,255,.1) !important; }
.ctrl-col-topic textarea::placeholder, .ctrl-col-topic input::placeholder { color: #94A3B8 !important; }
.ctrl-char-count { text-align: right; font-size: 11px; color: #94A3B8; margin-top: 8px; }

/* Round Radio */
.ctrl-col-rounds * { overflow: visible !important; } /* Stop internal radio scrollbars */
.round-radio { margin: 0 !important; padding: 0 !important; width: 100% !important; border: none !important; background: transparent !important; }
.round-radio .wrap { display: flex !important; gap: 8px !important; flex-wrap: nowrap !important; align-items: center !important; }
.round-radio label {
    display: flex !important; justify-content: center !important; align-items: center !important;
    width: 46px !important; height: 46px !important;
    background: #fff !important; border: 1.5px solid #E2E8F0 !important;
    border-radius: 10px !important; color: #475569 !important;
    font-size: 15px !important; font-weight: 600 !important;
    cursor: pointer !important; padding: 0 !important; flex-shrink: 0 !important;
}
.round-radio label:has(input:checked) {
    background: linear-gradient(135deg, #6C4DFF, #4F7FFF) !important;
    border-color: transparent !important; color: #fff !important;
    box-shadow: 0 4px 12px rgba(108,77,255,.3) !important;
}
.round-radio input[type=radio] { display: none !important; }

/* Start Button */
.start-btn, .start-btn button {
    width: 100% !important; height: 52px !important;
    background: linear-gradient(135deg, #6C4DFF, #4F7FFF) !important;
    color: #fff !important; font-size: 16px !important; font-weight: 700 !important;
    border: none !important; border-radius: 12px !important;
    cursor: pointer !important; box-shadow: 0 4px 16px rgba(79,127,255,.25) !important;
    display: flex !important; justify-content: center !important; align-items: center !important;
    margin: 0 !important; transition: transform .15s !important;
}
.start-btn button:hover { transform: translateY(-1px) !important; }
.start-hint { text-align: center; font-size: 12px; color: #94A3B8; margin-top: 10px; font-weight: 500; }

/* ── Content Grid (Fixed Proportions) ── */
.content-row {
    display: flex !important; flex-wrap: nowrap !important; gap: 24px !important;
    align-items: start !important; width: 100% !important;
    margin: 0 !important; padding: 0 !important; border: none !important; background: transparent !important;
}
.content-row > .wrap, .content-row > div {
    display: flex !important; flex-wrap: nowrap !important; gap: 24px !important;
    align-items: start !important; width: 100% !important;
}
.tx-panel, .rs-panel {
    background: #fff !important; border: 1px solid #E2E8F0 !important;
    border-radius: 16px !important; box-shadow: 0 2px 12px rgba(0,0,0,.03) !important;
    padding: 24px !important; display: flex !important; flex-direction: column !important;
    min-height: 400px !important; margin: 0 !important; min-width: 0 !important;
    overflow-x: hidden !important;
}
.tx-panel { width: 68% !important; min-width: 0 !important; flex: none !important; }
.rs-panel { width: 32% !important; min-width: 0 !important; flex: none !important; }

/* Panel Headers */
.panel-hdr-container {
    display: flex !important; justify-content: space-between !important; align-items: center !important;
    padding-bottom: 16px !important; border-bottom: 1px solid #E2E8F0 !important;
    margin-bottom: 20px !important; width: 100% !important; height: 52px !important;
}
.panel-title { display: flex; align-items: center; gap: 10px; font-size: 17px; font-weight: 700; color: #17213D; margin: 0 !important; min-width: max-content; }
.badge-live { background: #DCFCE7; color: #15803D; font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 20px; }
.badge-done { background: #DCFCE7; color: #15803D; font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 20px; }

/* Transcript Actions */
.tx-actions {
    display: flex !important; gap: 8px !important; flex-wrap: nowrap !important; align-items: center !important;
    margin: 0 !important; padding: 0 !important; border: none !important; background: transparent !important; width: auto !important;
}
.act-btn, .act-btn button {
    height: 36px !important; background: #fff !important;
    border: 1px solid #E2E8F0 !important; color: #64748B !important;
    font-size: 13px !important; font-weight: 500 !important;
    padding: 0 14px !important; border-radius: 8px !important;
    cursor: pointer !important; min-width: unset !important;
    display: flex !important; justify-content: center !important; align-items: center !important;
    margin: 0 !important; box-shadow: none !important;
}
.act-btn button:hover { background: #F8FAFC !important; color: #17213D !important; }

/* ── Message Bubbles ── */
.msg-row { display: flex; gap: 16px; margin-bottom: 20px; }
.msg-av { width: 44px; height: 44px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 17px; font-weight: 700; color: #fff; flex-shrink: 0; }
.av-a { background: #4F7FFF; }
.av-b { background: #E11D68; }
.msg-bub { flex: 1; min-width: 0; padding: 16px 20px; border-radius: 12px; overflow-wrap: break-word; }
.bub-a { background: #EFF6FF; border: 1px solid #DBEAFE; }
.bub-b { background: #FFF1F3; border: 1px solid #FFE4E9; }
.msg-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.msg-name { font-size: 15px; font-weight: 700; color: #17213D; }
.msg-rnd { display: inline-block; font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 20px; margin-left: 12px; }
.rnd-a { background: #DBEAFE; color: #1D4ED8; }
.rnd-b { background: #FFE4E9; color: #BE123C; }
.msg-ts { font-size: 12px; color: #94A3B8; font-weight: 500; }
.msg-body { font-size: 15px; color: #334155; line-height: 1.65; }

.thinking-bar { display: flex; align-items: center; gap: 12px; background: #EFF6FF; border: 1px solid #DBEAFE; border-radius: 10px; padding: 14px 20px; font-size: 14px; font-weight: 500; color: #4F7FFF; margin-bottom: 16px; }
.empty-state { text-align: center; color: #94A3B8; font-size: 15px; padding: 60px 20px; font-weight: 400; }

/* ── Result Panel ── */
.win-card { border-radius: 12px; padding: 20px; margin-bottom: 24px; display: flex; align-items: center; gap: 16px; }
.win-a { background: #EFF6FF; border: 1px solid #BFDBFE; }
.win-b { background: #FFF1F3; border: 1px solid #FECDD3; }
.win-tie { background: #F8FAFC; border: 1px solid #E2E8F0; }
.win-trophy { font-size: 40px; filter: drop-shadow(0 4px 10px rgba(0,0,0,.08)); }
.win-lbl { font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; color: #64748B; margin-bottom: 6px; }
.win-name { font-size: 20px; font-weight: 800; line-height: 1.2; margin-bottom: 4px; }
.win-sub { font-size: 13px; color: #64748B; font-weight: 400; }
.col-a { color: #1D4ED8; } .col-b { color: #BE123C; } .col-tie { color: #475569; }

.res-sec { font-size: 15px; font-weight: 700; color: #17213D; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.score-tbl { width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 24px; }
.score-tbl thead th { color: #64748B; font-weight: 600; font-size: 12px; padding: 0 10px 12px; text-align: center; border-bottom: 1.5px solid #E2E8F0; }
.score-tbl thead th:first-child { text-align: left; }
.score-tbl tbody td { padding: 12px 10px; text-align: center; border-bottom: 1px solid #F1F4FA; color: #475569; font-weight: 500; }
.score-tbl tbody td:first-child { text-align: left; }
.score-tbl td.ca { color: #2563EB; font-weight: 700; }
.score-tbl td.cb { color: #E11D68; font-weight: 700; }
.score-tbl tr.tot td { background: #F8FAFC; font-weight: 800; font-size: 15px; border-top: 2px solid #E2E8F0; border-bottom: none; padding: 14px 10px; }
.score-tbl tr.tot td.ca { color: #2563EB; }
.score-tbl tr.tot td.cb { color: #E11D68; }

.judge-text { font-size: 14px; color: #475569; line-height: 1.65; margin-bottom: 20px; }
.judge-quote { background: #F8FAFC; border-left: 3px solid #6C4DFF; border-radius: 0 10px 10px 0; padding: 16px 20px; font-size: 13px; font-style: italic; color: #64748B; line-height: 1.55; }
"""


# ─────────────────────────────────────────────────────────────────────────────
#  HTML rendering helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now_ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _transcript_html(transcript: list[dict], thinking: str | None = None) -> str:
    if not transcript and not thinking:
        return "<div class='empty-state'>The debate will appear here once you start…</div>"
    parts: list[str] = []
    for arg in transcript:
        is_a    = arg["speaker"] == DEBATER_A
        av_cls  = "av-a" if is_a else "av-b"
        av_ltr  = "A" if is_a else "B"
        bub_cls = "bub-a" if is_a else "bub-b"
        rnd_cls = "rnd-a" if is_a else "rnd-b"
        role    = FOR if is_a else AGAINST
        ts      = arg.get("timestamp", "")
        content = arg["content"].replace("\n", "<br>")
        parts.append(f"""
<div class="msg-row">
  <div class="msg-av {av_cls}">{av_ltr}</div>
  <div class="msg-bub {bub_cls}">
    <div class="msg-meta">
      <div>
        <span class="msg-name">{arg['speaker']} ({role})</span>
        <span class="msg-rnd {rnd_cls}">Round {arg['round']}</span>
      </div>
      <span class="msg-ts">{ts}</span>
    </div>
    <div class="msg-body">{content}</div>
  </div>
</div>""")
    if thinking:
        parts.append(f"""
<div class="thinking-bar">🤖 <span>{thinking}</span></div>""")
    return "".join(parts)


def _verdict_html(verdict: dict | str) -> str:
    if not verdict:
        return "<div class='empty-state'>Awaiting the judge's verdict…</div>"
    if isinstance(verdict, str):
        escaped = verdict.replace("&", "&amp;").replace("<", "&lt;")
        return (
            f"<div class='thinking-bar'>🤖 Judge ({VLLM_MODEL}) is deliberating…</div>"
            f"<pre style='background:#1E293B;color:#CBD5E1;padding:16px;border-radius:10px;"
            f"font-size:13px;overflow-x:auto;line-height:1.5'>{escaped}</pre>"
        )

    totals  = verdict.get("totals", {})
    a_tot   = totals.get(DEBATER_A, 0)
    b_tot   = totals.get(DEBATER_B, 0)
    winner  = verdict.get("winner", "Tie")

    if winner == DEBATER_A:
        card_cls, name_cls = "win-card win-a", "col-a"
        win_txt = f"{DEBATER_A} (For)"
        subtxt  = "Stronger logical foundation and reasoning"
    elif winner == DEBATER_B:
        card_cls, name_cls = "win-card win-b", "col-b"
        win_txt = f"{DEBATER_B} (Against)"
        subtxt  = "Stronger arguments and better evidence"
    else:
        card_cls, name_cls = "win-card win-tie", "col-tie"
        win_txt = "Tie"
        subtxt  = "An equally matched and compelling debate"

    args = verdict.get("arguments", [])

    def _s(key: str, spk: str) -> int:
        return sum(int(a.get(key, 0)) for a in args if a.get("speaker") == spk)

    a_log, a_ev, a_per = _s("logic", DEBATER_A), _s("evidence", DEBATER_A), _s("persuasiveness", DEBATER_A)
    b_log, b_ev, b_per = _s("logic", DEBATER_B), _s("evidence", DEBATER_B), _s("persuasiveness", DEBATER_B)

    html = f"""
<div class="{card_cls}">
  <div class="win-trophy">🏆</div>
  <div>
    <div class="win-lbl">Winner</div>
    <div class="win-name {name_cls}">{win_txt}</div>
    <div class="win-sub">{subtxt}</div>
  </div>
</div>
<div class="res-sec">📊 Score Breakdown</div>
<table class="score-tbl">
  <thead><tr><th>Criteria</th><th>Debater A</th><th>Debater B</th></tr></thead>
  <tbody>
    <tr><td>Logic</td><td class="ca">{a_log}</td><td class="cb">{b_log}</td></tr>
    <tr><td>Evidence</td><td class="ca">{a_ev}</td><td class="cb">{b_ev}</td></tr>
    <tr><td>Persuasiveness</td><td class="ca">{a_per}</td><td class="cb">{b_per}</td></tr>
    <tr class="tot"><td>Total Score</td><td class="ca">{a_tot}</td><td class="cb">{b_tot}</td></tr>
  </tbody>
</table>"""

    if verdict.get("verdict"):
        html += f"""
<div class="res-sec" style="margin-top:4px">📝 Judge's Summary</div>
<div class="judge-text">{verdict['verdict']}</div>
<div class="judge-quote">"A great debate doesn't just reveal who is right, but what we all can learn."</div>"""
    return html


def _plain_transcript(transcript: list[dict]) -> str:
    lines: list[str] = []
    for arg in transcript:
        role = FOR if arg["speaker"] == DEBATER_A else AGAINST
        ts   = arg.get("timestamp", "")
        lines.append(f"[Round {arg['round']}] {arg['speaker']} ({role})  {ts}")
        lines.append(arg["content"])
        lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
#  History HTML
# ─────────────────────────────────────────────────────────────────────────────

def _history_html(sessions: list[dict], active_idx: int = -1) -> str:
    if not sessions:
        return "<div style='color:#5A6E94;font-size:13px;padding:12px 0'>No debates yet.</div>"

    parts: list[str] = []
    for idx, s in enumerate(sessions[:MAX_HISTORY]):
        topic = s.get("topic", "Untitled")
        ts    = s.get("timestamp", "")
        try:
            dt       = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            date_fmt = dt.strftime("%d %b %Y, %H:%M")
        except ValueError:
            date_fmt = ts[:16]

        initial = (topic[0].upper()) if topic else "D"
        color   = _AVATAR_COLORS[idx % len(_AVATAR_COLORS)]
        display = topic if len(topic) <= 22 else topic[:20] + "…"
        active_cls = " active" if idx == active_idx else ""

        parts.append(f"""
<div class="hist-card{active_cls}" onclick="triggerHistoryClick({idx})">
  <div class="hist-avatar" style="background:{color}">{initial}</div>
  <div class="hist-body">
    <div class="hist-title">{display}</div>
    <div class="hist-date">📅 {date_fmt}</div>
  </div>
</div>""")

    return "\n".join(parts)


def _char_count_html(topic_text: str) -> str:
    n = len(topic_text or "")
    return f"<div class='ctrl-char-count'>{n} / 200</div>"


# JS injected globally via launch(js=...) — gr.HTML blocks <script> tags.
_GLOBAL_JS = """
function triggerHistoryClick(idx) {
    const wrap = document.querySelector('.hist-trigger');
    if (!wrap) return;
    const inp = wrap.querySelector('input[type=number]');
    if (!inp) return;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(inp, String(idx));
    inp.dispatchEvent(new Event('input',  {bubbles: true}));
    inp.dispatchEvent(new Event('change', {bubbles: true}));
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Event callbacks
# ─────────────────────────────────────────────────────────────────────────────

def on_load():
    sessions = storage.load_sessions()
    return _history_html(sessions, active_idx=-1)


def load_debate(idx_raw):
    try:
        idx = int(idx_raw)
    except (TypeError, ValueError):
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    sessions = storage.load_sessions()
    if 0 <= idx < len(sessions):
        s = sessions[idx]
        return (
            s["topic"],
            s["rounds"],
            _transcript_html(s["transcript"]),
            _verdict_html(s["verdict"]),
            _plain_transcript(s["transcript"]),
            _history_html(sessions, active_idx=idx),
            _char_count_html(s["topic"]),
        )
    return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()


def on_topic_change(topic_text):
    return _char_count_html(topic_text)


def _clear():
    sessions = storage.load_sessions()
    return (
        "", 3,
        _transcript_html([]),
        _verdict_html({}),
        "",
        _history_html(sessions, active_idx=-1),
        _char_count_html(""),
    )


def debate_handler(topic: str, rounds: int):
    """Streaming generator — yields (tx_html, vr_html, plain, hist_html)."""
    if not (topic or "").strip():
        yield (_transcript_html([], "⚠️ Please enter a debate topic."), _verdict_html({}), "", gr.update())
        return

    yield (_transcript_html([], "🚀 Agents are preparing…"), _verdict_html({}), "", gr.update())

    q: Queue = Queue()

    def _run():
        try:
            for _ in run_debate(topic, int(rounds), q=q):
                pass
            q.put(("done", None))
        except Exception as exc:
            q.put(("error", exc))

    threading.Thread(target=_run, daemon=True).start()

    transcript: list[dict] = []
    current_speaker_round  = (-1, "")
    verdict: dict | str    = {}

    while True:
        msg_type, data = q.get()

        if msg_type == "chunk":
            ts = _now_ts()
            data["timestamp"] = ts
            key = (data["round"], data["speaker"])
            if key == current_speaker_round:
                if transcript:
                    transcript[-1] = data
                else:
                    transcript.append(data)
            else:
                current_speaker_round = key
                transcript.append(data)

            thinking = f"Round {data['round']}: {data['speaker']} ({data['position']}) is arguing…"
            yield (
                _transcript_html(transcript, thinking),
                _verdict_html(verdict),
                _plain_transcript(transcript),
                gr.update(),
            )

        elif msg_type == "judge_chunk":
            yield (
                _transcript_html(transcript, "⚖️ Judge is evaluating arguments…"),
                _verdict_html(data),
                _plain_transcript(transcript),
                gr.update(),
            )

        elif msg_type == "state_full":
            state = data
            new_tx = state.get("transcript", [])
            new_vr = state.get("verdict", {})
            now    = _now_ts()
            for arg in new_tx:
                arg.setdefault("timestamp", now)
            transcript = new_tx

            if new_vr and not isinstance(new_vr, str):
                verdict = new_vr
                storage.save_session(topic, int(rounds), transcript, verdict)
                sessions  = storage.load_sessions()
                hist_upd  = _history_html(sessions, active_idx=0)
                yield (
                    _transcript_html(transcript),
                    _verdict_html(verdict),
                    _plain_transcript(transcript),
                    hist_upd,
                )
            else:
                if new_vr:
                    verdict = new_vr
                last = transcript[-1] if transcript else None
                thinking = (
                    f"Round {last['round']}: {last['speaker']} ({last['position']}) spoke…"
                    if last else "Starting debate…"
                )
                yield (
                    _transcript_html(transcript, thinking),
                    _verdict_html(verdict),
                    _plain_transcript(transcript),
                    gr.update(),
                )

        elif msg_type == "error":
            exc = data
            try:
                from openai import APIConnectionError, APITimeoutError, NotFoundError
                if isinstance(exc, APIConnectionError):
                    detail = "Cannot reach vLLM server. Check VLLM_BASE_URL in .env"
                elif isinstance(exc, APITimeoutError):
                    detail = "vLLM server timed out."
                elif isinstance(exc, NotFoundError):
                    detail = f"Model not found: {exc}"
                else:
                    detail = str(exc) or type(exc).__name__
            except ImportError:
                detail = str(exc) or type(exc).__name__
            yield (
                _transcript_html(transcript, f"❌ {detail}"),
                _verdict_html(verdict),
                _plain_transcript(transcript),
                gr.update(),
            )
            return

        elif msg_type == "done":
            return


# JS for Copy / Download
_COPY_JS = """
async (plain) => {
    try { await navigator.clipboard.writeText(plain); }
    catch(e) { alert('Copy failed: ' + e.message); }
}
"""

_DOWNLOAD_JS = """
(plain, topic) => {
    const blob = new Blob([plain], {type:'text/plain'});
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    const safe = (topic||'debate').replace(/[^a-z0-9]/gi,'_').toLowerCase();
    a.download = safe + '_transcript.txt';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  UI builder  (component tree + event wiring)
# ─────────────────────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="AI Debate Agent") as demo:

        plain_state = gr.State("")

        with gr.Row(elem_classes="app-shell"):

            # ── SIDEBAR ─────────────────────────────────────────────────
            with gr.Column(elem_classes="sidebar"):

                gr.HTML("""
                <div class="sb-logo">
                  <div class="sb-logo-icon">🤖</div>
                  <div class="sb-logo-text">
                    <h3>AI Debate Agent</h3>
                    <p>Different perspectives.<br>Better thinking.</p>
                  </div>
                </div>
                """)

                new_btn = gr.Button("+ New Debate", elem_classes="new-debate-btn")

                gr.HTML('<div class="sb-section-label">Recent Debates</div>')

                hist_display = gr.HTML(
                    _history_html(storage.load_sessions()),
                    elem_classes="hist-html",
                )

                hist_trigger = gr.Number(value=-1, visible=False, elem_classes="hist-trigger")

                gr.HTML("""
                <div class="sb-quote">
                  "Better questions lead to better thinking."
                </div>
                """)

            # ── MAIN CONTENT ─────────────────────────────────────────────
            with gr.Column(elem_classes="main-content"):

                gr.HTML("""
                <div class="page-header">
                  <div>
                    <div class="ph-title"><span class="ai-accent">AI</span> Debate Agent</div>
                    <div class="ph-sub">Two LLM agents argue. A judge scores. You learn.</div>
                  </div>
                  <div class="ph-right">
                    <div class="ph-badge">⚡ Powered by vLLM</div>
                    <div class="ph-theme">☀️</div>
                    <div class="ph-user">
                      <div class="ph-user-av">H</div>
                      Het Gandhi
                    </div>
                  </div>
                </div>
                """)

                # ── Controls ─────────────────────────────────────────────
                with gr.Row(elem_classes="ctrl-card"):

                    with gr.Column(elem_classes="ctrl-col-topic"):
                        gr.HTML('<div class="ctrl-label">📄 Debate Topic</div>')
                        topic = gr.Textbox(
                            show_label=False,
                            placeholder="e.g. Android Vs Apple",
                            container=False,
                            lines=1,
                        )
                        char_count = gr.HTML(_char_count_html(""))

                    with gr.Column(elem_classes="ctrl-col-rounds"):
                        gr.HTML('<div class="ctrl-label">📚 Number of Rounds</div>')
                        rounds = gr.Radio(
                            choices=[1, 2, 3, 4, 5],
                            value=3,
                            show_label=False,
                            container=False,
                            elem_classes="round-radio",
                        )

                    with gr.Column(elem_classes="ctrl-col-start"):
                        run_btn = gr.Button("▶ Start Debate", elem_classes="start-btn")
                        gr.HTML('<div class="start-hint">Let the AI agents begin!</div>')

                # ── Transcript + Result ───────────────────────────────────
                with gr.Row(elem_classes="content-row"):

                    with gr.Column(elem_classes="tx-panel"):
                        with gr.Row(elem_classes="panel-hdr-container"):
                            gr.HTML("""
                            <div class="panel-title">
                              👥 Debate Transcript
                              <span class="badge-live">● Live</span>
                            </div>
                            """)
                            with gr.Row(elem_classes="tx-actions"):
                                copy_btn  = gr.Button("📋 Copy",      elem_classes="act-btn")
                                dl_btn    = gr.Button("⬇️ Download",  elem_classes="act-btn")
                                clear_btn = gr.Button("🗑 Clear",     elem_classes="act-btn")

                        transcript_out = gr.HTML(_transcript_html([]))

                    with gr.Column(elem_classes="rs-panel"):
                        gr.HTML("""
                        <div class="panel-hdr-container">
                          <div class="panel-title">
                            🏆 Debate Result
                            <span class="badge-done">● Completed</span>
                          </div>
                        </div>
                        """)
                        verdict_out = gr.HTML(_verdict_html({}))

        # ══════════════════════════════════════════════════════════════════
        # EVENT WIRING
        # ══════════════════════════════════════════════════════════════════
        debate_outs = [transcript_out, verdict_out, plain_state, hist_display]

        run_btn.click(fn=debate_handler, inputs=[topic, rounds], outputs=debate_outs)
        topic.submit(fn=debate_handler, inputs=[topic, rounds], outputs=debate_outs)

        # live character counter
        topic.change(fn=on_topic_change, inputs=[topic], outputs=[char_count])

        new_btn.click(
            fn=_clear,
            outputs=[topic, rounds, transcript_out, verdict_out, plain_state, hist_display, char_count],
        )
        clear_btn.click(
            fn=_clear,
            outputs=[topic, rounds, transcript_out, verdict_out, plain_state, hist_display, char_count],
        )

        copy_btn.click(fn=None, inputs=[plain_state], outputs=[], js=_COPY_JS)
        dl_btn.click(fn=None, inputs=[plain_state, topic], outputs=[], js=_DOWNLOAD_JS)

        hist_trigger.change(
            fn=load_debate,
            inputs=[hist_trigger],
            outputs=[topic, rounds, transcript_out, verdict_out, plain_state, hist_display, char_count],
        )

        demo.load(fn=on_load, outputs=[hist_display])

    return demo


if __name__ == "__main__":
    build_ui().launch(server_name="0.0.0.0", css=CSS, js=_GLOBAL_JS, theme=gr.themes.Base())
