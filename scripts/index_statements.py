"""
RAG Indexer — Step 2 of the RAG pipeline.

What this script does (run once, or re-run when data changes):
  1. Loads all statement files + cards.json
  2. Builds two types of text chunks (the retrieval units)
  3. Embeds each chunk with OpenAI text-embedding-ada-002
  4. Stores vectors + metadata in ChromaDB (local, persistent)

Run:
    uv run python scripts/index_statements.py
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
import chromadb
from openai import OpenAI

# ── Load API key from .env ──────────────────────────────────────────────────
# python-dotenv reads the .env file and injects its values into os.environ.
# This must happen before we construct the OpenAI client.
load_dotenv()

# ── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
STATEMENTS_DIR = ROOT / "data" / "statements"
CARDS_JSON = ROOT / "data" / "cards.json"
CHROMA_DIR = ROOT / "data" / "chroma"  # where ChromaDB persists on disk


# ── Clients ──────────────────────────────────────────────────────────────────
#
# OpenAI client — used only for embedding (not chat).
# text-embedding-ada-002 converts a text string → 1,536-dim float vector.
#
# ChromaDB client — local persistent store.
# PersistentClient saves to disk so the index survives between runs.
# Calling it again with the same path just opens the existing store.
#
openai_client = OpenAI()
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))


def embed(texts: list[str]) -> list[list[float]]:
    """
    Embed a batch of strings using OpenAI text-embedding-ada-002.

    RAG concept: embedding converts text into a dense vector — a fixed-size
    list of floats where meaning is encoded as direction and magnitude.
    Two sentences that mean the same thing (even with different words) will
    produce vectors that are close together in that 1,536-dimensional space.
    This is what powers semantic search: we find chunks whose meaning is
    similar to the query, not just chunks that share the same keywords.

    We batch all texts in one API call because the Embeddings endpoint accepts
    up to 2,048 inputs at once — batching is faster and cheaper than one
    call per chunk.
    """
    response = openai_client.embeddings.create(
        model="text-embedding-ada-002",
        input=texts,
    )
    return [item.embedding for item in response.data]


def get_or_create_collection() -> chromadb.Collection:
    """
    RAG concept: a Collection is the vector database's equivalent of a table.
    We use one collection for everything (spend summaries + card rules),
    and rely on metadata fields like `user_id` and `chunk_type` to filter
    at query time. This is more flexible than separate collections and teaches
    a pattern you'll see in production systems.

    cosine distance is standard for text embeddings — it measures the angle
    between two vectors, ignoring magnitude, which is what we want for
    semantic similarity.
    """
    return chroma_client.get_or_create_collection(
        name="cardwise",
        metadata={"hnsw:space": "cosine"},
    )


# ── Chunk builders ───────────────────────────────────────────────────────────
#
# RAG concept: chunking is the most important design decision in any RAG system.
# A chunk is the atomic retrieval unit — whatever gets embedded and returned.
# Too large: the chunk dilutes the signal (many topics in one vector).
# Too small: each chunk lacks enough context for the LLM to reason over.
#
# We use two chunk types that complement each other:
#   1. Spend summaries  → what the user actually did this month, per card per category
#   2. Card rules       → what the card promises to reward (from cards.json)
#
# At query time, retrieving both lets the LLM compare actual vs potential.


def build_spend_chunks(statement: dict, card_configs: dict[str, dict]) -> list[dict]:
    """
    One chunk per (card × category) combination in a statement.

    Each chunk is a natural-language summary that includes:
    - Who (user_id, name)
    - When (month)
    - Which card
    - What category
    - How much spent and how many transactions
    - Exactly what was earned (cashback or points)

    Natural language matters here: we're embedding text, and the embedding
    model was trained on natural language. A prose sentence like
    "Alice spent $418 on dining with Citi Double Cash" embeds much better
    than a raw JSON blob.

    Spend totals are derived from the transactions list (the source of truth)
    rather than rewards_summary, which only stores reward amounts per category.
    """
    chunks = []
    user_id = statement["user_id"]
    name = statement["name"]
    month = statement["month"]
    rewards_summary = statement.get("rewards_summary", {})

    # Build spend totals by (card_id, category) from the transactions list
    spend_by: dict[tuple, dict] = {}
    for txn in statement.get("transactions", []):
        key = (txn["card_id"], txn["category"])
        if key not in spend_by:
            spend_by[key] = {"amount": 0.0, "count": 0}
        spend_by[key]["amount"] += txn["amount"]
        spend_by[key]["count"] += 1

    for card_id, card_data in rewards_summary.items():
        reward_type = card_data.get("type")
        by_category = card_data.get("by_category", {})

        for category, cat_data in by_category.items():
            s = spend_by.get((card_id, category), {})
            spend = round(s.get("amount", 0), 2)
            txn_count = s.get("count", 0)

            if reward_type == "cashback":
                cashback = cat_data.get("cashback_usd", 0)
                rate = cat_data.get("rate", "?")
                earned_str = f"earned ${cashback:.2f} cashback at {rate}"
            else:
                points = cat_data.get("points", 0)
                rate = cat_data.get("rate", "?")
                pv = card_configs.get(card_id, {}).get("point_value_cents", 1.0)
                est_value = round(points * pv / 100, 2)
                earned_str = f"earned {points:,} points at {rate} (≈${est_value:.2f})"

            text = (
                f"{name} ({user_id}) spent ${spend:.2f} on {category} "
                f"using {card_id} in {month} across {txn_count} transaction(s) "
                f"and {earned_str}."
            )

            chunk_id = f"{user_id}__{card_id}__{category}__{month}"

            chunks.append({
                "id": chunk_id,
                "text": text,
                "metadata": {
                    "chunk_type": "spend_summary",
                    "user_id": user_id,
                    "card_id": card_id,
                    "category": category,
                    "month": month,
                    "spend_usd": spend,
                },
            })

    return chunks


def build_card_rule_chunks(cards: list[dict]) -> list[dict]:
    """
    One chunk per card describing its reward rules as prose.

    RAG concept: these chunks are the "knowledge base" side of RAG.
    The spend summaries tell us what happened; the card rules tell us
    what *could* have happened (or what to do next). Retrieving both
    at query time gives the LLM everything it needs to answer
    "am I getting the best rate?" without hallucinating card terms.

    Unlike spend summaries, card rule chunks have no user_id — they're
    global facts about the card, shared across all users.
    """
    chunks = []

    for card in cards:
        cfg = card.get("reward_config")
        if not cfg:
            continue

        card_id = card["id"]
        card_name = card["name"]
        annual_fee = card["annual_fee"]
        perks = card.get("perks", [])

        lines = [f"{card_name} (annual fee: ${annual_fee})."]

        if cfg["type"] == "points":
            currency = cfg["currency"]
            pv = cfg["point_value_cents"]
            lines.append(f"Earns {currency} points, valued at {pv}¢ per point.")
            for cat, rate in cfg["category_rates"].items():
                lines.append(f"  {rate}x {currency} on {cat}.")
            sb = cfg.get("streaming_bonus")
            if sb:
                merchants = ", ".join(sb["merchants"])
                lines.append(
                    f"  {sb['rate']}x {currency} on streaming services: {merchants}."
                )

        elif cfg["type"] == "cashback":
            if "flat_rate" in cfg:
                pct = int(cfg["flat_rate"] * 100)
                lines.append(f"Earns {pct}% cashback on all purchases.")
            elif "rotating_schedule" in cfg:
                cap = cfg.get("quarterly_cap", 1500)
                base = int(cfg["base_rate"] * 100)
                rotating = int(cfg["rotating_rate"] * 100)
                lines.append(
                    f"Earns {rotating}% cashback on rotating quarterly categories "
                    f"(up to ${cap:,.0f}/quarter), then {base}% on everything else."
                )
                for quarter, cats in cfg["rotating_schedule"].items():
                    for cat, merchants in cats.items():
                        if merchants:
                            m_str = ", ".join(merchants)
                            lines.append(f"  {quarter}: {rotating}% on {cat} at {m_str}.")
                        else:
                            lines.append(f"  {quarter}: {rotating}% on all {cat} purchases.")

        if perks:
            lines.append("Key perks: " + "; ".join(perks[:3]) + ".")

        text = " ".join(lines)
        chunk_id = f"card_rules__{card_id}"

        chunks.append({
            "id": chunk_id,
            "text": text,
            "metadata": {
                "chunk_type": "card_rules",
                "card_id": card_id,
            },
        })

    return chunks


# ── Index loader ─────────────────────────────────────────────────────────────

def load_all_statements() -> list[dict]:
    statements = []
    for path in sorted(STATEMENTS_DIR.rglob("*.json")):
        statements.append(json.loads(path.read_text()))
    return statements


def upsert_chunks(collection: chromadb.Collection, chunks: list[dict]) -> None:
    """
    RAG concept: upsert (update-or-insert) is idempotent — running the indexer
    twice won't create duplicate vectors. ChromaDB matches on the `id` field.
    This means you can safely re-run this script whenever statements are
    regenerated and only changed chunks get new embeddings.

    We embed all texts in one batch call, then upsert in one batch call.
    Both operations are O(n) in the number of chunks.
    """
    if not chunks:
        return

    texts = [c["text"] for c in chunks]
    ids = [c["id"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    print(f"  Embedding {len(texts)} chunk(s)...")
    vectors = embed(texts)

    collection.upsert(
        ids=ids,
        embeddings=vectors,
        documents=texts,
        metadatas=metadatas,
    )


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("CardWise RAG Indexer")
    print("=" * 50)

    collection = get_or_create_collection()

    # ── Index card rules (global, not per-user) ──────────────────────────────
    print("\n[1/2] Indexing card rules from cards.json...")
    cards = json.loads(CARDS_JSON.read_text())
    card_configs = {c["id"]: c["reward_config"] for c in cards if "reward_config" in c}
    card_rule_chunks = build_card_rule_chunks(cards)
    print(f"  Built {len(card_rule_chunks)} card rule chunk(s).")
    upsert_chunks(collection, card_rule_chunks)
    print("  Done.")

    # ── Index spend summaries (per user, per month) ──────────────────────────
    print("\n[2/2] Indexing spend summaries from statements...")
    statements = load_all_statements()
    print(f"  Found {len(statements)} statement file(s).")

    all_spend_chunks = []
    for stmt in statements:
        all_spend_chunks.extend(build_spend_chunks(stmt, card_configs))

    print(f"  Built {len(all_spend_chunks)} spend summary chunk(s).")
    upsert_chunks(collection, all_spend_chunks)
    print("  Done.")

    # ── Summary ──────────────────────────────────────────────────────────────
    total = collection.count()
    print(f"\nIndex complete. Total vectors in ChromaDB: {total}")
    print(f"Persisted at: {CHROMA_DIR}")


if __name__ == "__main__":
    main()
