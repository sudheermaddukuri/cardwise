from __future__ import annotations

import streamlit as st
from models import Card


def _reward_highlights(card: Card) -> list[str]:
    r = card.rewards
    items: list[str] = []
    if r.travel:
        items.append(f"✈ {r.travel} Travel")
    if r.dining:
        items.append(f"🍽 {r.dining} Dining")
    if r.groceries:
        items.append(f"🛒 {r.groceries} Groceries")
    if r.streaming:
        items.append(f"📺 {r.streaming} Streaming")
    if r.special:
        items.append(f"⭐ {r.special}")
    if not items:
        items.append(f"💰 {r.other} on all purchases")
    return items[:3]


def _render_card_tile(card: Card, score: int, rank: int, show_score: bool) -> None:
    with st.container(border=True):
        # Accent border + name — minimal inline HTML, reliable in all Streamlit versions
        st.html(
            f'<div style="border-left:4px solid {card.accent_color};'
            f'padding-left:10px;margin:0 0 4px">'
            f'<span style="font-weight:700;font-size:1.05rem">{card.name}</span><br>'
            f'<span style="font-size:0.78rem;opacity:0.6">{card.issuer} · {card.network}</span>'
            f'</div>'
        )

        if show_score:
            st.progress(score / 100, text=f"#{rank} &nbsp;·&nbsp; **{score}%** match")

        c1, c2 = st.columns(2)
        fee = f"${card.annual_fee}/yr" if card.annual_fee > 0 else "No fee"
        c1.metric("Annual Fee", fee)

        bonus = card.sign_up_bonus or "—"
        if len(bonus) > 28:
            bonus = bonus[:28] + "…"
        c2.metric("Sign-up Bonus", bonus)

        highlights = _reward_highlights(card)
        st.markdown("&nbsp; · &nbsp;".join(f"`{h}`" for h in highlights))

        if st.button("Details →", key=f"details_{card.id}", use_container_width=True):
            st.session_state.selected_card_id = card.id
            st.rerun()


def render_card_grid(scored: list[tuple[Card, int]], has_scores: bool) -> None:
    count = len(scored)
    if has_scores:
        st.caption(f"Sorted by match · {count} cards")
    else:
        st.caption(f"{count} cards · answer the questions above to rank them")

    col_a, col_b = st.columns(2, gap="medium")

    for i, (card, score) in enumerate(scored):
        with (col_a if i % 2 == 0 else col_b):
            _render_card_tile(card, score, i + 1, has_scores)
