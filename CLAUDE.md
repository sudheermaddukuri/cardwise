# CardWise — Claude Code Context

This file captures project decisions, design rationale, and conversation history so any engineer or AI session can pick up from the current state without re-deriving context.

---

## What This Is

A single-page Streamlit app that helps users find the right credit card by answering 3 questions about their spending habits. Cards re-rank in real time as answers are selected. No login, no ads, no friction.

---

## How to Run

```bash
uv sync
uv run streamlit run app.py
# Opens at http://localhost:8501
```

---

## Project Structure

```
app.py                  # Entry point — layout, CSS, column orchestration
models.py               # Pydantic models: Card, Rewards
scoring.py              # Quiz answer → match score (0–100) per card
data/cards.json         # Card catalog (seed + any ingested cards)
components/
  quiz.py               # 3-question radio panel (auto-runs on change)
  card_grid.py          # 2-column card grid with match scores
  card_detail.py        # Right-panel detail view (rewards, perks, apply)
  ingest.py             # Add cards via form or JSON/CSV file upload
.streamlit/config.toml  # Dark navy theme
```

---

## Design Decisions (with rationale)

### Quiz drives sorting, not filtering
Cards are always visible. Answering questions re-orders them by match score. Zero answers = default order by annual fee ascending. This keeps the page useful even before the quiz is touched.

### Scoring is algorithmic, not hardcoded per card
`scoring.py` derives match scores from `card.categories` and `card.annual_fee`. This means any card added via ingestion is automatically scoreable — no per-card scoring config needed.

**Weights:** Q1 spending (50%) · Q2 annual fee (30%) · Q3 rewards type (20%)
Partial answers normalize against answered weight so a 1-question answer still produces a 0–100 score.

### Data stored as a flat JSON file
`data/cards.json` — no database, no migrations, editable by hand. The ingestion feature appends validated Pydantic objects to this file. Could swap for SQLite later with no UI changes.

### Right panel, not a modal or separate page
When a card's "Details →" is clicked, the layout shifts to a 60/40 column split. The right column renders the detail panel; closing it restores the full-width grid. This is the most Streamlit-native way to simulate a drawer.

---

## Features Deliberately Excluded (deferred, not forgotten)

| Feature | Status | Notes |
|---|---|---|
| Deals & offers section | Deferred | `Deal` model stubbed in `models.py`; data structure ready |
| Side-by-side compare | Out of scope | Replaced by quiz-driven ranking |
| External deals ingestion | Deferred | Manual ingestion only for now |
| User accounts / saved cards | Not planned | Intentionally stateless |

---

## Key Bug Fixed During Build

**HTML rendering as raw text (Streamlit 1.40+)**

`st.markdown(html, unsafe_allow_html=True)` was deprecated in Streamlit 1.40 and renders HTML as escaped text in 1.58.0. All HTML injection was migrated to `st.html()`, which is the correct API for Streamlit 1.36+.

Rule: use `st.html("<style>...")` for CSS, `st.html("<div>...")` for markup, and `st.markdown()` only for plain text/markdown content.

---

## Seed Cards

Four cards chosen to cover distinct user archetypes:

| Card | Best For | Annual Fee |
|---|---|---|
| Chase Sapphire Preferred | Travel + Dining | $95 |
| American Express Gold | Dining + Groceries | $250 |
| Citi Double Cash | Simple cashback | $0 |
| Discover it Cash Back | Beginners / rotating | $0 |

---

## Conversation History Summary

1. **User brief** — Build a credit card discovery SPA. Streamlit + Python + UV. Plan first, implement second.
2. **Design review** — Agreed on quiz-driven ranking (no compare), 4 seed cards, deals deferred, no specific target audience.
3. **Interaction spec** — Quiz auto-runs on any answer change. Card detail opens as a right panel.
4. **Implementation** — Full app built: quiz, card grid, detail panel, ingestion (form + file upload).
5. **Bug fix** — `st.markdown(unsafe_allow_html=True)` → `st.html()` across all components.
6. **Docs** — README.md (user-facing), OVERVIEW.md (one-pager with prompts + tech stack), CLAUDE.md (this file).

---

## What to Work on Next

- Wire up the `Deal` model and add a deals/offers section to the page
- Add card images (issuer logos or card art) to the grid tiles
- Consider SQLite if the card catalog grows beyond ~50 cards
