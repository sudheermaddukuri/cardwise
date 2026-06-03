from __future__ import annotations

from models import Card

_W = {"q1": 0.50, "q2": 0.30, "q3": 0.20}


def _q1_score(card: Card, answer: str) -> float:
    cats = card.categories
    if answer == "Travel":
        if "travel" in cats:
            return 1.0
        if "dining" in cats:
            return 0.45
        return 0.15
    if answer == "Dining & Groceries":
        if "dining" in cats or "groceries" in cats:
            return 1.0
        if "travel" in cats:
            return 0.40
        return 0.15
    if answer == "Everyday Purchases":
        if "cashback" in cats:
            return 1.0
        if "rotating" in cats:
            return 0.85
        return 0.25
    return 0.0


def _q2_score(card: Card, answer: str) -> float:
    fee = card.annual_fee
    if answer == "$0 only":
        if fee == 0:
            return 1.0
        if fee <= 100:
            return 0.25
        return 0.0
    if answer == "Up to $100":
        return 1.0 if fee <= 100 else 0.25
    if answer == "Fine with $200+":
        return 1.0
    return 0.0


def _q3_score(card: Card, answer: str) -> float:
    cats = card.categories
    if answer == "Cashback":
        return 1.0 if "cashback" in cats else 0.15
    if answer == "Points & Miles":
        return 1.0 if "travel" in cats else 0.20
    if answer == "No Preference":
        return 0.70
    return 0.0


def compute_score(card: Card, q1: str | None, q2: str | None, q3: str | None) -> int:
    answered_weight = (
        (_W["q1"] if q1 else 0.0)
        + (_W["q2"] if q2 else 0.0)
        + (_W["q3"] if q3 else 0.0)
    )
    if answered_weight == 0:
        return 0

    raw = 0.0
    if q1:
        raw += _W["q1"] * _q1_score(card, q1)
    if q2:
        raw += _W["q2"] * _q2_score(card, q2)
    if q3:
        raw += _W["q3"] * _q3_score(card, q3)

    # Normalize so partial answers still produce a 0–100 range
    return round((raw / answered_weight) * 100)


def score_cards(
    cards: list[Card],
    q1: str | None,
    q2: str | None,
    q3: str | None,
) -> list[tuple[Card, int]]:
    if not any([q1, q2, q3]):
        return [(c, 0) for c in sorted(cards, key=lambda c: c.annual_fee)]

    scored = [(card, compute_score(card, q1, q2, q3)) for card in cards]
    return sorted(scored, key=lambda x: x[1], reverse=True)
