# CardWise

Find the right credit card based on how you actually spend.

## What it does

- Answer 3 questions → cards rank by match score instantly
- Click any card for full rewards, perks, and sign-up bonus details
- Add new cards via a form or JSON/CSV file upload

## Stack

Streamlit · Python 3.12 · UV · Pydantic v2

## Run

```bash
uv sync
uv run streamlit run app.py
```

Opens at `http://localhost:8501`

## Add cards

Use the **+ Add a Card** section at the bottom of the page, or upload a JSON file matching the schema in [`data/cards.json`](data/cards.json).
