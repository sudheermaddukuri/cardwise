"""
Retriever — Step 3a of the RAG pipeline.

Given a query and a user_id, returns the most relevant chunks from ChromaDB.
Two searches run per query:
  - Spend summaries  (filtered to this user)
  - Card rule chunks (global — same for everyone)
"""

import chromadb
from openai import OpenAI


def retrieve(
    query: str,
    user_id: str,
    collection: chromadb.Collection,
    openai_client: OpenAI,
    n_spend: int = 6,
    n_rules: int = 2,
) -> tuple[list[str], list[str]]:
    # Embed the query using the same model used at index time
    query_vec = openai_client.embeddings.create(
        model="text-embedding-ada-002",
        input=[query],
    ).data[0].embedding

    # Search 1: user's spend history
    spend_results = collection.query(
        query_embeddings=[query_vec],
        n_results=n_spend,
        where={"$and": [{"user_id": user_id}, {"chunk_type": "spend_summary"}]},
        include=["documents"],
    )

    # Search 2: card reward rules (no user filter — these are global facts)
    rule_results = collection.query(
        query_embeddings=[query_vec],
        n_results=n_rules,
        where={"chunk_type": "card_rules"},
        include=["documents"],
    )

    spend_chunks = spend_results["documents"][0]
    rule_chunks  = rule_results["documents"][0]

    return spend_chunks, rule_chunks
