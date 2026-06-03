from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

from models import Card, Rewards

_CARDS_PATH = Path(__file__).parent.parent / "data" / "cards.json"


def _load_raw() -> list[dict]:
    return json.loads(_CARDS_PATH.read_text())


def _persist(cards: list[dict]) -> None:
    _CARDS_PATH.write_text(json.dumps(cards, indent=2))


def _add_card(card: Card) -> str | None:
    """Returns an error string or None on success."""
    cards = _load_raw()
    if any(c["id"] == card.id for c in cards):
        return f"A card with ID '{card.id}' already exists."
    cards.append(card.model_dump())
    _persist(cards)
    return None


def render_ingest_section() -> None:
    with st.expander("+ Add a Card", expanded=False):
        tab_form, tab_upload = st.tabs(["Fill in details", "Upload JSON / CSV"])
        with tab_form:
            _render_form()
        with tab_upload:
            _render_upload()


# ── form ──────────────────────────────────────────────────────────────────────

def _render_form() -> None:
    with st.form("ingest_form", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            name = st.text_input("Card Name *", placeholder="e.g. Venture Rewards")
            issuer = st.text_input("Issuer *", placeholder="e.g. Capital One")
            network = st.selectbox("Network", ["Visa", "Mastercard", "Amex", "Discover"])
            annual_fee = st.number_input("Annual Fee ($)", min_value=0, value=0, step=1)
            accent_color = st.color_picker("Accent Color", value="#3b82f6")

        with c2:
            sign_up_bonus = st.text_input("Sign-up Bonus", placeholder="e.g. 75,000 miles")
            sign_up_spend = st.text_input("Spend Requirement", placeholder="e.g. $3,000 in 3 months")
            categories = st.multiselect(
                "Categories *",
                ["travel", "dining", "groceries", "cashback", "gas", "streaming", "rotating"],
            )
            apply_url = st.text_input("Apply URL", placeholder="https://...")

        st.markdown("**Rewards** *(fill only what applies)*")
        r1, r2, r3 = st.columns(3)
        travel_r = r1.text_input("Travel", placeholder="3x")
        dining_r = r2.text_input("Dining", placeholder="2x")
        groceries_r = r3.text_input("Groceries", placeholder="2x")
        r4, r5, r6 = st.columns(3)
        gas_r = r4.text_input("Gas", placeholder="2x")
        streaming_r = r5.text_input("Streaming", placeholder="1x")
        other_r = r6.text_input("Everything Else *", value="1x")

        perks_raw = st.text_area(
            "Perks *(one per line)*",
            placeholder="No foreign transaction fees\nTrip cancellation insurance",
        )

        submitted = st.form_submit_button("Add Card", type="primary", use_container_width=True)

    if submitted:
        if not name.strip() or not issuer.strip() or not categories:
            st.error("Card name, issuer, and at least one category are required.")
            return

        card_id = name.strip().lower().replace(" ", "-")
        perks = [p.strip() for p in perks_raw.strip().splitlines() if p.strip()]

        try:
            card = Card(
                id=card_id,
                name=name.strip(),
                issuer=issuer.strip(),
                network=network,
                annual_fee=int(annual_fee),
                sign_up_bonus=sign_up_bonus.strip() or None,
                sign_up_spend=sign_up_spend.strip() or None,
                categories=categories,
                rewards=Rewards(
                    travel=travel_r.strip() or None,
                    dining=dining_r.strip() or None,
                    groceries=groceries_r.strip() or None,
                    gas=gas_r.strip() or None,
                    streaming=streaming_r.strip() or None,
                    other=other_r.strip() or "1x",
                ),
                perks=perks,
                apply_url=apply_url.strip() or "#",
                accent_color=accent_color,
            )
        except ValidationError as exc:
            st.error(f"Validation error: {exc}")
            return

        err = _add_card(card)
        if err:
            st.error(err)
        else:
            st.success(f"'{card.name}' added! Refresh the page to see it in the grid.")


# ── file upload ───────────────────────────────────────────────────────────────

def _render_upload() -> None:
    st.markdown("Upload a **JSON** array of card objects, or a **CSV** with one card per row.")
    uploaded = st.file_uploader("Choose file", type=["json", "csv"], label_visibility="collapsed")

    if not uploaded:
        return

    try:
        if uploaded.name.endswith(".json"):
            raw_list = json.loads(uploaded.read())
            if isinstance(raw_list, dict):
                raw_list = [raw_list]
        else:
            import pandas as pd
            df = pd.read_csv(uploaded)
            raw_list = df.where(df.notna(), None).to_dict(orient="records")
    except Exception as exc:
        st.error(f"Could not parse file: {exc}")
        return

    validated: list[Card] = []
    parse_errors: list[str] = []

    for i, raw in enumerate(raw_list):
        try:
            # Promote flat reward columns into a nested dict when needed
            if "rewards" not in raw:
                reward_keys = {"travel", "dining", "groceries", "gas", "streaming", "special", "other"}
                nested = {k: raw.pop(k) for k in reward_keys if k in raw}
                if nested:
                    raw["rewards"] = nested
            validated.append(Card(**raw))
        except (ValidationError, TypeError) as exc:
            parse_errors.append(f"Row {i + 1}: {exc}")

    if parse_errors:
        st.warning("Skipped invalid rows:\n" + "\n".join(parse_errors))

    if not validated:
        st.error("No valid cards found in the file.")
        return

    st.markdown(f"**Preview** — {len(validated)} card(s) ready to import:")
    for c in validated:
        st.markdown(f"- {c.name} ({c.issuer}, ${c.annual_fee}/yr)")

    if st.button("Import Cards", type="primary"):
        added, skipped = 0, 0
        for card in validated:
            if _add_card(card) is None:
                added += 1
            else:
                skipped += 1
        st.success(f"Imported {added} card(s). Skipped {skipped} duplicate(s).")
