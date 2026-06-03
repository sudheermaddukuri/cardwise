from __future__ import annotations

import streamlit as st

_Q1_OPTIONS = ["Travel", "Dining & Groceries", "Everyday Purchases"]
_Q2_OPTIONS = ["$0 only", "Up to $100", "Fine with $200+"]
_Q3_OPTIONS = ["Cashback", "Points & Miles", "No Preference"]


def render_quiz() -> tuple[str | None, str | None, str | None]:
    st.caption("Answer a few questions and cards sort instantly")

    col1, col2, col3 = st.columns(3, gap="large")

    with col1:
        q1 = st.radio(
            "Where do you spend the most?",
            _Q1_OPTIONS,
            index=None,
            key="quiz_q1",
        )

    with col2:
        q2 = st.radio(
            "Annual fee comfort?",
            _Q2_OPTIONS,
            index=None,
            key="quiz_q2",
        )

    with col3:
        q3 = st.radio(
            "Rewards preference?",
            _Q3_OPTIONS,
            index=None,
            key="quiz_q3",
        )

    return q1, q2, q3
