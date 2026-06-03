from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from models import Card
from scoring import score_cards
from components.quiz import render_quiz
from components.card_grid import render_card_grid
from components.card_detail import render_detail_panel
from components.ingest import render_ingest_section

# ── page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CardWise",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── global CSS ─────────────────────────────────────────────────────────────────
# st.html() is the correct API for injecting raw HTML/CSS in Streamlit 1.36+

st.html("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2.5rem 3rem !important; }

/* metric value sizing */
[data-testid="stMetricValue"] { font-size: 1rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.7rem !important; }

/* tighten st.html blocks so they don't add extra whitespace */
[data-testid="stHtml"] { margin: 0 !important; line-height: 1; }
</style>
""")

# ── data ──────────────────────────────────────────────────────────────────────

def load_cards() -> list[Card]:
    raw = json.loads((Path(__file__).parent / "data" / "cards.json").read_text())
    return [Card(**c) for c in raw]

# ── header ────────────────────────────────────────────────────────────────────

st.html("""
<div style="padding:1.5rem 0 1rem;margin-bottom:0.25rem">
    <div style="font-size:1.75rem;font-weight:800;letter-spacing:-0.02em">
        Card<span style="color:#3b82f6">Wise</span>
    </div>
    <div style="font-size:0.95rem;opacity:0.45;margin-top:0.2rem">
        Find the card that fits your life
    </div>
</div>
""")

# ── layout ────────────────────────────────────────────────────────────────────

cards = load_cards()

left_col, right_col = st.columns([3, 2], gap="large")

with left_col:
    q1, q2, q3 = render_quiz()
    scored = score_cards(cards, q1, q2, q3)
    render_card_grid(scored, any([q1, q2, q3]))

selected_id: str | None = st.session_state.get("selected_card_id")
selected_card = next((c for c in cards if c.id == selected_id), None) if selected_id else None

with right_col:
    if selected_card:
        render_detail_panel(selected_card)
    else:
        st.html("""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;padding:5rem 2rem;text-align:center;opacity:0.35">
            <div style="font-size:2.5rem;margin-bottom:0.75rem">💳</div>
            <div style="font-size:0.9rem">
                Click <strong>Details →</strong> on any card<br>to see full rewards and perks
            </div>
        </div>
        """)

# ── ingestion ─────────────────────────────────────────────────────────────────

st.divider()
render_ingest_section()
