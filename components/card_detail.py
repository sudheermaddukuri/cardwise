from __future__ import annotations

import streamlit as st
from models import Card


def render_detail_panel(card: Card) -> None:
    st.html(
        f'<div style="border-top:3px solid {card.accent_color};'
        f'padding-top:0.85rem;margin-bottom:0.25rem">'
        f'<span style="font-weight:700;font-size:1.2rem">{card.name}</span><br>'
        f'<span style="font-size:0.8rem;opacity:0.5">{card.issuer} · {card.network}</span>'
        f'</div>'
    )

    fee_str = f"${card.annual_fee}/yr" if card.annual_fee > 0 else "No annual fee"
    m1, m2 = st.columns(2)
    m1.metric("Annual Fee", fee_str)
    m2.metric("Sign-up Bonus", "See below")

    if card.sign_up_bonus:
        st.info(f"**Bonus:** {card.sign_up_bonus}")
    if card.sign_up_spend:
        st.caption(f"Spend requirement: {card.sign_up_spend}")

    st.divider()

    st.markdown("**Rewards**")
    r = card.rewards
    reward_rows: list[tuple[str, str]] = []
    if r.travel:
        reward_rows.append(("✈ Travel", r.travel))
    if r.dining:
        reward_rows.append(("🍽 Dining", r.dining))
    if r.groceries:
        reward_rows.append(("🛒 Groceries", r.groceries))
    if r.gas:
        reward_rows.append(("⛽ Gas", r.gas))
    if r.streaming:
        reward_rows.append(("📺 Streaming", r.streaming))
    if r.special:
        reward_rows.append(("⭐ Special", r.special))
    reward_rows.append(("Everything else", r.other))

    for label, rate in reward_rows:
        c1, c2 = st.columns([3, 1])
        c1.write(label)
        c2.markdown(f"**{rate}**")

    st.divider()

    st.markdown("**Perks & Benefits**")
    for perk in card.perks:
        st.markdown(f"✓ &nbsp;{perk}")

    st.html("<div style='height:0.75rem'></div>")
    st.link_button("Apply Now →", card.apply_url, use_container_width=True, type="primary")
