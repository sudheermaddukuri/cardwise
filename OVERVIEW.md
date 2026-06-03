# CardWise — Project Overview

---

## Problem Statement

Choosing a credit card is unnecessarily complex. Reward structures, annual fees, sign-up bonuses, and category multipliers vary widely across dozens of cards — and most comparison tools are cluttered, ad-heavy, or require an account. CardWise solves this by letting anyone answer three quick questions about their spending habits and instantly seeing which cards are the best fit for them, ranked by a match score. A built-in ingestion feature also allows new cards to be added over time without any code changes.

---

## Prompts Used to Build This Application

**1 — Initial brief**
> "I'm looking to build a credit card offers and deals tracking application. I want my users to be able to decide which card to choose based on their lifestyle and spending habits. This application is supposed to be a single-page application targeted at a specific set of users, with a simple UI and elegant design. Keeping it simple and easy for anybody to navigate and find out which card they want to apply for. I want to add another core feature to this app to support ingestion of other cards/deals. Pick on Streamlit, Python, and UV for tech stack. Do not implement anything unless I say so. Come up with a plan and let's review it together before implementation."

**2 — Design scope decisions**
> "Seed data: come up with 3–4 cards. Deals ingestion: not required for now. Compare feature: not required — just looking for an easy way to answer 2–3 questions and have cards sort by recommendation. Target audience: no specific demographic."

**3 — Interaction model**
> "Quiz should run automatically on any answer change. Learn More should open a drawer on the right."

**4 — Bug fix**
> "Cards are broken and are rendering HTML text on the application. Fix it."
*(Root cause: Streamlit 1.40+ deprecated `unsafe_allow_html` in `st.markdown`; resolved by migrating all HTML injection to `st.html()`.)*

---

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| UI Framework | Streamlit 1.58 | Single-page app, layout, and widgets |
| Language | Python 3.12 | Application logic and scoring |
| Package Manager | UV | Dependency management and virtual env |
| Data Storage | JSON (flat file) | Card catalog — zero infrastructure needed |
| Validation | Pydantic v2 | Schema enforcement on card ingestion |

---

## Feature Summary

- **Quiz** — 3 radio questions (spending category, fee tolerance, rewards preference); cards re-rank automatically on every selection
- **Card grid** — 2-column layout with match score, annual fee, sign-up bonus, and reward highlights per card
- **Detail panel** — full rewards breakdown and perks list slides in on the right when a card is selected
- **Ingestion** — add cards via a form or by uploading a JSON/CSV file; Pydantic validates before writing to disk

---

*Built with Claude Code · June 2026*
