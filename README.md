# CardWise

An AI-powered credit card advisor that evaluates your spending history and tells you whether you are getting the best value from your cards — using RAG (Retrieval-Augmented Generation).

---

## What it does

**Discover tab** — Answer 3 questions about your spending habits and cards re-rank by match score in real time.

**Card Advisor tab** — Ask natural language questions about your card usage:

- *"Am I getting good value from my dining spend?"*
- *"Which card should I use for gas this month?"*
- *"Should I book a concert ticket to maximise rewards?"*
- *"What am I leaving on the table with my current card usage?"*

The assistant answers using your actual simulated spend history and exact card terms — no generic advice, no hallucinated rates.

---

## How it works — RAG in 4 steps

```
Step 1 — Data
  Simulate 6 months of credit card statements for 3 user personas.
  Each transaction includes the exact reward earned per card terms.

Step 2 — Index
  Convert statements + card rules into text chunks.
  Embed each chunk with OpenAI text-embedding-ada-002.
  Store vectors + metadata in ChromaDB (local, persistent).

Step 3 — Retrieve + Generate
  User asks a question → embed query → find closest chunks in ChromaDB
  → assemble prompt (context + question) → GPT-4o → grounded answer.

Step 4 — Chat UI
  Streamlit chat interface with persona selector and conversation history.
```

### Why RAG and not just GPT-4?

A plain LLM call has no knowledge of your spending data and may hallucinate card terms. RAG injects the right facts at query time — every figure in the answer traces back to a retrieved chunk, not the model's imagination.

---

## Key concepts

**Chunking** — the unit of retrieval. We create two chunk types:
- *Spend summaries* — one per (user × card × category × month): `"Alice spent $293 on dining using Citi Double Cash in Dec 2025 and earned $5.87 cashback at 2%."`
- *Card rules* — one per card encoding reward rates as prose: `"Amex Gold earns 4x Membership Rewards on dining, valued at 1¢ per point."`

**Embeddings** — text converted to a 1,536-dimensional vector by `text-embedding-ada-002`. Semantically similar texts land near each other in that space, enabling search by meaning rather than keywords.

**Metadata filtering** — each vector carries tags (`user_id`, `card_id`, `category`, `month`). At query time `where={"user_id": "alice"}` ensures one user's data never appears in another's results.

**Prompt assembly** — before calling GPT-4o, retrieved chunks are injected into the prompt alongside the question. The system prompt explicitly prohibits inventing card terms, so every claim is grounded.

**Conversation history** — each API call is stateless. Prior turns are passed as a message list so follow-up questions work naturally within a session.

---

## Project structure

```
app.py                        Entry point — tabs, layout, CSS
models.py                     Pydantic models: Card, Rewards
scoring.py                    Quiz answer → match score per card

data/
  cards.json                  Card catalog with reward_config (single source of truth)
  statements/{user}/{month}.json  Simulated statements (18 files)
  chroma/                     ChromaDB vector store (generated)

scripts/
  generate_statements.py      Generate 18 statement JSON files
  index_statements.py         Embed chunks and store in ChromaDB

rag/
  retriever.py                Embed query → top-k chunks from ChromaDB
  chain.py                    Retrieval + prompt assembly + GPT-4o call

components/
  quiz.py                     3-question radio panel
  card_grid.py                2-column card grid with match scores
  card_detail.py              Detail panel (rewards, perks, apply link)
  chat.py                     RAG chat UI with session history
  ingest.py                   Add cards via form or file upload

notebooks/
  rag_01_indexing.ipynb       Step-by-step: chunking, embedding, ChromaDB
  rag_02_chain.ipynb          Step-by-step: retrieval, prompt, generation, multi-turn
```

---

## Setup and run

**Prerequisites:** Python 3.12+, [uv](https://github.com/astral-sh/uv), OpenAI API key.

```bash
# 1. Install dependencies
uv sync

# 2. Add your OpenAI API key
echo "OPENAI_API_KEY=sk-..." > .env

# 3. Generate simulated statements (creates data/statements/)
uv run python scripts/generate_statements.py

# 4. Build the vector index (creates data/chroma/)
uv run python scripts/index_statements.py

# 5. Run the app
uv run streamlit run app.py
# Opens at http://localhost:8501
```

Re-run steps 3 and 4 any time the card catalog or personas change.

---

## Personas

| Persona | Cards | Spending focus |
|---|---|---|
| Alice Chen | Citi Double Cash + Chase Sapphire Preferred | Mixed — dining, travel, groceries, shopping |
| Bob Martinez | Amex Gold | Dining and groceries heavy |
| Carol Kim | Discover it Cash Back | Gas, groceries, rotating categories |

Six months of statements per persona (Dec 2025 – May 2026), with seasonal variance, weekend dining bias, and correct quarterly cap tracking for Discover's rotating rewards.

---

## Learning notebooks

The `notebooks/` directory walks through the RAG pipeline one concept at a time:

| Notebook | Covers |
|---|---|
| `rag_01_indexing.ipynb` | Chunking, embeddings (with cosine similarity demo), ChromaDB upsert, test retrieval |
| `rag_02_chain.ipynb` | Retrieval mechanics, prompt assembly, GPT-4o generation, multi-turn conversation |

```bash
uv run jupyter lab
```

---

## Stack

| Layer | Tool |
|---|---|
| App framework | Streamlit |
| LLM | GPT-4o |
| Embedding model | text-embedding-ada-002 |
| Vector database | ChromaDB (local, persistent) |
| Data validation | Pydantic v2 |
| Package management | uv |

---

## Add cards

Use the **Add Cards** tab in the app, or upload a JSON file matching the schema in [`data/cards.json`](data/cards.json). Any card with a `reward_config` block is automatically scoreable in the quiz and queryable in the advisor — no code changes needed.
