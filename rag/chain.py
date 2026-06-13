"""
Chain — Step 3b of the RAG pipeline.

Wires retrieval → prompt assembly → GPT-4 → answer.
Supports multi-turn conversation via a history list.
"""

import chromadb
from openai import OpenAI

from rag.retriever import retrieve

SYSTEM_PROMPT = """You are a personal credit card advisor with access to the user's actual spend history and their card reward terms.

Rules:
- Answer using only the provided context. Never invent card terms.
- Be specific: quote dollar amounts, reward rates, and point values from the context.
- If the user is missing a better reward rate on another card they hold, call it out clearly.
- Keep answers concise — 3 to 5 sentences unless a breakdown is genuinely useful."""


def build_context(spend_chunks: list[str], rule_chunks: list[str]) -> str:
    parts = []
    if spend_chunks:
        parts.append("USER SPEND HISTORY:\n" + "\n".join(f"- {c}" for c in spend_chunks))
    if rule_chunks:
        parts.append("CARD REWARD TERMS:\n" + "\n".join(f"- {c}" for c in rule_chunks))
    return "\n\n".join(parts)


def ask(
    query: str,
    user_id: str,
    collection: chromadb.Collection,
    openai_client: OpenAI,
    history: list[dict] | None = None,
) -> str:
    spend_chunks, rule_chunks = retrieve(query, user_id, collection, openai_client)
    context = build_context(spend_chunks, rule_chunks)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({
        "role": "user",
        "content": f"Context:\n{context}\n\nQuestion: {query}",
    })

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.3,
    )
    return response.choices[0].message.content
