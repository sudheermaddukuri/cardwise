"""
RAG Chat component — Step 4 of the RAG pipeline.

Concepts in play:
  - st.session_state    : persists chat history across Streamlit rerenders
  - st.chat_message()   : renders user / assistant bubbles
  - st.chat_input()     : fixed input bar at the bottom of the page
  - history list        : grows each turn; passed to chain.ask() so GPT-4
                          remembers previous exchanges in the same session
"""

from __future__ import annotations

from pathlib import Path

import chromadb
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from rag.chain import ask

load_dotenv()

CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma"

PERSONAS = {
    "alice": "Alice Chen  —  Citi Double Cash + Chase Sapphire Preferred",
    "bob":   "Bob Martinez  —  Amex Gold",
    "carol": "Carol Kim  —  Discover it Cash Back",
}

STARTER_QUESTIONS = [
    "Am I getting good value from my dining spend?",
    "Which category should I spend more on to earn better rewards?",
    "Should I book a concert ticket this month?",
    "Am I using the right card for gas?",
]


# ── Client initialisation (once per session) ──────────────────────────────────
#
# Streamlit reruns the entire script on every interaction.
# Storing clients in st.session_state means they are created only once —
# the first time the user visits — and reused on every subsequent rerender.

def _init_clients() -> tuple[OpenAI, chromadb.Collection] | tuple[None, None]:
    if "openai_client" not in st.session_state:
        try:
            st.session_state.openai_client = OpenAI()
        except Exception:
            return None, None

    if "chroma_collection" not in st.session_state:
        try:
            client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            st.session_state.chroma_collection = client.get_collection("cardwise")
        except Exception:
            return None, None

    return st.session_state.openai_client, st.session_state.chroma_collection


# ── Main render function ──────────────────────────────────────────────────────

def render_chat() -> None:
    openai_client, collection = _init_clients()

    # Guard: show setup message if clients aren't ready
    if openai_client is None:
        st.warning("OpenAI API key not found. Add it to your `.env` file.")
        return
    if collection is None:
        st.warning(
            "ChromaDB index not found. Run `uv run python scripts/index_statements.py` first."
        )
        return

    # ── User selector ─────────────────────────────────────────────────────────
    #
    # Each persona has their own chat history stored under a separate key.
    # Switching users gives a fresh conversation without losing prior sessions.

    user_id = st.selectbox(
        "Select persona",
        options=list(PERSONAS.keys()),
        format_func=lambda k: PERSONAS[k],
        label_visibility="collapsed",
    )

    history_key = f"chat_history_{user_id}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []

    history: list[dict] = st.session_state[history_key]

    # ── Starter prompts (only when chat is empty) ─────────────────────────────
    if not history:
        st.markdown("**Try asking:**")
        cols = st.columns(2)
        for i, q in enumerate(STARTER_QUESTIONS):
            if cols[i % 2].button(q, key=f"starter_{i}", use_container_width=True):
                # Treat a starter click exactly like a typed question
                st.session_state[f"pending_query_{user_id}"] = q
                st.rerun()

    # ── Render existing messages ──────────────────────────────────────────────
    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Handle pending query from starter button clicks ───────────────────────
    pending_key = f"pending_query_{user_id}"
    pending = st.session_state.pop(pending_key, None)

    # ── Chat input ────────────────────────────────────────────────────────────
    typed = st.chat_input(f"Ask about {PERSONAS[user_id].split('—')[0].strip()}'s cards...")
    prompt = pending or typed

    if prompt:
        # Snapshot history BEFORE this turn — this is what the LLM sees as
        # "what we've talked about so far". The current question is NOT in it yet.
        prior_history = list(history) if history else None

        # Display the user's message immediately
        with st.chat_message("user"):
            st.markdown(prompt)

        # Call the RAG chain: retrieve → assemble prompt → GPT-4o → answer
        with st.chat_message("assistant"):
            with st.spinner("Looking at your statements..."):
                answer = ask(
                    query=prompt,
                    user_id=user_id,
                    collection=collection,
                    openai_client=openai_client,
                    history=prior_history,
                )
            st.markdown(answer)

        # Persist both turns — next rerender will display them from session state
        history.append({"role": "user",      "content": prompt})
        history.append({"role": "assistant", "content": answer})

    # ── Clear conversation button ─────────────────────────────────────────────
    if history:
        if st.button("Clear conversation", key=f"clear_{user_id}"):
            st.session_state[history_key] = []
            st.rerun()
