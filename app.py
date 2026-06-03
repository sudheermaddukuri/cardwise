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

# ── global CSS ────────────────────────────────────────────────────────────────

st.html("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2.5rem 3rem !important; }
[data-testid="stMetricValue"] { font-size: 1rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.7rem !important; }
[data-testid="stHtml"] { margin: 0 !important; line-height: 1; }
</style>
""")

# ── data ──────────────────────────────────────────────────────────────────────

def load_cards() -> list[Card]:
    raw = json.loads((Path(__file__).parent / "data" / "cards.json").read_text())
    return [Card(**c) for c in raw]

# ── card detail dialog ────────────────────────────────────────────────────────
# Defined here so it shares scope with the loaded cards.
# Calling _card_detail_modal(card) opens an overlay — no layout shift.

@st.dialog("Card Details", width="large")
def _card_detail_modal(card: Card) -> None:
    render_detail_panel(card)

# ── header ────────────────────────────────────────────────────────────────────

st.html("""
<div style="padding:1.25rem 0 1rem;border-bottom:1px solid #e2e8f0;margin-bottom:1.5rem">
    <div style="font-size:1.75rem;font-weight:800;letter-spacing:-0.02em;color:#1e293b">
        Card<span style="color:#2563eb">Wise</span>
    </div>
    <div style="font-size:0.95rem;color:#94a3b8;margin-top:0.15rem">
        Find the card that fits your life
    </div>
</div>
""")

# ── quiz + full-width card grid ───────────────────────────────────────────────

cards = load_cards()

q1, q2, q3 = render_quiz()
scored = score_cards(cards, q1, q2, q3)
render_card_grid(scored, any([q1, q2, q3]), on_details=_card_detail_modal)

# ── ingestion ─────────────────────────────────────────────────────────────────

st.divider()
render_ingest_section()
