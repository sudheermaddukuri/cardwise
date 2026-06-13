#!/usr/bin/env python3
"""
Generate realistic synthetic credit card statements for CardWise user personas.

Produces 6 months of transactions per persona under:
  data/statements/{user_id}/{YYYY-MM}.json

Each statement includes:
  - transactions          individual line items with merchant, amount, card used
  - rewards_earned        per-transaction reward posted, matched to card terms
  - reward_postings       statement-style summary of rewards (like a real statement)
  - rewards_summary       total points/cashback per card with category breakdown

Run:
  uv run python scripts/generate_statements.py
"""

import json
import random
from datetime import date
from pathlib import Path

SEED = 42  # reproducible output across runs

CARDS_JSON = Path(__file__).parent.parent / "data" / "cards.json"

# ---------------------------------------------------------------------------
# Merchant pools — real names, per-merchant amount ranges (lo, hi)
# When lo == hi the transaction is a fixed-price subscription
# ---------------------------------------------------------------------------
MERCHANTS: dict[str, list[tuple[str, tuple[float, float]]]] = {
    "dining": [
        ("Shake Shack", (14.25, 28.50)),
        ("Chipotle Mexican Grill", (10.75, 19.25)),
        ("The Capital Grille", (68.00, 178.00)),
        ("Sweetgreen", (12.75, 22.50)),
        ("Starbucks", (5.75, 17.50)),
        ("Panera Bread", (11.50, 24.75)),
        ("Olive Garden", (21.00, 56.50)),
        ("Cheesecake Factory", (27.50, 78.00)),
        ("Chick-fil-A", (8.25, 21.75)),
        ("Nobu New York", (88.00, 192.00)),
        ("Blue Bottle Coffee", (5.25, 13.75)),
        ("Five Guys", (11.75, 22.25)),
        ("Panda Express", (8.75, 17.50)),
        ("Domino's Pizza", (17.50, 44.75)),
        ("Momofuku Noodle Bar", (22.00, 58.00)),
        ("Joe's Pizza", (7.75, 21.50)),
        ("Dunkin'", (4.25, 11.75)),
        ("The Smith", (28.00, 72.00)),
        ("Dos Caminos", (18.50, 49.00)),
        ("Dig Inn", (12.25, 21.75)),
    ],
    "groceries": [
        ("Whole Foods Market", (54.75, 188.00)),
        ("Trader Joe's", (44.25, 142.50)),
        ("Kroger", (39.50, 162.75)),
        ("Safeway", (37.25, 148.00)),
        ("Costco Wholesale", (82.00, 245.00)),
        ("Wegmans", (48.50, 178.25)),
        ("Publix", (41.75, 158.00)),
        ("Stop & Shop", (37.50, 147.25)),
        ("Fairway Market", (54.00, 168.50)),
        ("Aldi", (29.75, 112.50)),
        ("Sprouts Farmers Market", (44.25, 138.75)),
    ],
    "travel": [
        ("Delta Air Lines", (182.00, 748.00)),
        ("United Airlines", (168.00, 724.00)),
        ("American Airlines", (155.00, 682.00)),
        ("Southwest Airlines", (122.00, 485.00)),
        ("JetBlue Airways", (112.00, 428.00)),
        ("Marriott Hotels", (148.00, 385.00)),
        ("Hilton Hotels", (138.00, 352.00)),
        ("Hyatt Regency", (162.00, 425.00)),
        ("Airbnb", (88.00, 458.00)),
        ("Uber", (11.75, 67.50)),
        ("Lyft", (10.50, 54.25)),
        ("Hertz", (54.00, 224.00)),
        ("National Car Rental", (49.50, 212.00)),
    ],
    "gas": [
        ("Shell", (37.50, 82.75)),
        ("Chevron", (39.25, 85.50)),
        ("ExxonMobil", (35.75, 80.25)),
        ("BP", (37.75, 82.50)),
        ("Sunoco", (34.50, 78.25)),
        ("Mobil", (38.00, 82.00)),
        ("Circle K", (33.75, 75.50)),
        ("Speedway", (35.50, 78.75)),
    ],
    "entertainment": [
        ("Netflix", (15.49, 15.49)),
        ("Spotify", (10.99, 10.99)),
        ("Hulu", (17.99, 17.99)),
        ("Disney+", (13.99, 13.99)),
        ("Apple TV+", (9.99, 9.99)),
        ("HBO Max", (15.99, 15.99)),
        ("AMC Theatres", (13.75, 34.50)),
        ("Regal Cinemas", (12.50, 31.75)),
        ("Ticketmaster", (44.00, 285.00)),
        ("StubHub", (52.00, 348.00)),
    ],
    "shopping": [
        ("Amazon", (17.50, 285.00)),
        ("Target", (21.75, 148.00)),
        ("Walmart", (17.25, 138.50)),
        ("Nordstrom", (54.00, 325.00)),
        ("Macy's", (34.50, 188.00)),
        ("Best Buy", (44.75, 458.00)),
        ("Apple Store", (28.75, 1198.00)),
        ("IKEA", (54.00, 385.00)),
        ("HomeGoods", (27.50, 148.50)),
        ("Zara", (34.75, 188.00)),
        ("Nike", (34.50, 188.50)),
        ("REI", (44.25, 282.00)),
        ("H&M", (21.75, 97.50)),
    ],
    "utilities": [
        ("AT&T Wireless", (58.00, 58.00)),
        ("Verizon", (72.00, 72.00)),
        ("Comcast", (89.99, 89.99)),
        ("Google One", (2.99, 2.99)),
        ("iCloud+", (2.99, 2.99)),
        ("New York Times", (17.00, 17.00)),
        ("Amazon Prime", (14.99, 14.99)),
        ("Adobe Creative Cloud", (54.99, 54.99)),
        ("Dropbox", (11.99, 11.99)),
    ],
}

# Seasonal multiplier applied on top of per-month random variance
SEASONAL_WEIGHT: dict[int, float] = {
    12: 1.28,  # December: holiday shopping + travel
    1: 0.80,   # January: post-holiday pullback
    2: 0.88,   # February: still quiet
    3: 1.00,   # March: baseline
    4: 1.06,   # April: spring uptick
    5: 1.12,   # May: pre-summer
}

# ---------------------------------------------------------------------------
# Card reward config — loaded from data/cards.json at startup.
# The reward_config block on each card is the single source of truth.
# ---------------------------------------------------------------------------

def load_card_configs() -> dict[str, dict]:
    """Return {card_id: reward_config} for every card that has a reward_config."""
    cards = json.loads(CARDS_JSON.read_text())
    return {c["id"]: c["reward_config"] for c in cards if "reward_config" in c}


CARD_CONFIGS: dict[str, dict] = load_card_configs()

# ---------------------------------------------------------------------------
# Persona definitions
#
# spend entries: category → (primary_card_id, probability_of_using_it, (min_tx, max_tx))
# Probability < 1.0 models habit — a card held but not always used optimally.
# ---------------------------------------------------------------------------
PERSONAS: dict[str, dict] = {
    "alice": {
        "name": "Alice Chen",
        "cards": ["citi-double-cash", "chase-sapphire-preferred"],
        # Alice defaults to Citi for almost everything out of habit.
        # Chase Sapphire Preferred used for travel but occasionally forgotten.
        "spend": {
            "dining":        ("citi-double-cash",          0.93, (8, 18)),
            "groceries":     ("citi-double-cash",          0.96, (4, 8)),
            "travel":        ("chase-sapphire-preferred",  0.88, (0, 4)),
            "gas":           ("citi-double-cash",          0.85, (2, 5)),
            "entertainment": ("citi-double-cash",          0.90, (2, 5)),
            "shopping":      ("citi-double-cash",          0.88, (3, 10)),
            "utilities":     ("citi-double-cash",          1.00, (1, 3)),
        },
    },
    "bob": {
        "name": "Bob Martinez",
        "cards": ["amex-gold"],
        # Heavy diner and grocery shopper. One card, used everywhere.
        # No gas (urban dweller). Occasional travel with no dedicated travel card.
        "spend": {
            "dining":        ("amex-gold", 1.00, (10, 22)),
            "groceries":     ("amex-gold", 1.00, (5, 10)),
            "travel":        ("amex-gold", 1.00, (0, 2)),
            "entertainment": ("amex-gold", 1.00, (2, 6)),
            "shopping":      ("amex-gold", 1.00, (2, 8)),
            "utilities":     ("amex-gold", 1.00, (1, 3)),
        },
    },
    "carol": {
        "name": "Carol Kim",
        "cards": ["discover-it-cash-back"],
        # Everyday spender — groceries, gas, streaming, some dining.
        # One beginner card for everything; not optimizing spend by category.
        "spend": {
            "dining":        ("discover-it-cash-back", 1.00, (3, 8)),
            "groceries":     ("discover-it-cash-back", 1.00, (3, 7)),
            "gas":           ("discover-it-cash-back", 1.00, (3, 6)),
            "entertainment": ("discover-it-cash-back", 1.00, (1, 4)),
            "shopping":      ("discover-it-cash-back", 1.00, (2, 7)),
            "utilities":     ("discover-it-cash-back", 1.00, (1, 2)),
        },
    },
}

MONTHS = [
    (2025, 12),
    (2026, 1),
    (2026, 2),
    (2026, 3),
    (2026, 4),
    (2026, 5),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def days_in_month(year: int, month: int) -> int:
    if month == 12:
        return (date(year + 1, 1, 1) - date(year, 12, 1)).days
    return (date(year, month + 1, 1) - date(year, month, 1)).days


def quarter_key(year: int, month: int) -> str:
    """Return a quarter string matching the rotating_schedule keys in cards.json, e.g. '2026-Q1'."""
    return f"{year}-Q{(month - 1) // 3 + 1}"


def random_date(year: int, month: int, category: str) -> str:
    n = days_in_month(year, month)
    if category == "dining":
        days = list(range(1, n + 1))
        weights = [3 if date(year, month, d).weekday() >= 4 else 1 for d in days]
        day = random.choices(days, weights=weights)[0]
    else:
        day = random.randint(1, n)
    return date(year, month, day).isoformat()


def pick_amount(lo: float, hi: float) -> float:
    if lo == hi:
        return round(lo, 2)
    mean = lo + (hi - lo) * 0.38
    std = (hi - lo) * 0.22
    val = random.gauss(mean, std)
    return round(max(lo, min(hi, val)), 2)


def pick_card(primary: str, prob: float, all_cards: list[str]) -> str:
    if random.random() < prob:
        return primary
    others = [c for c in all_cards if c != primary]
    return random.choice(others) if others else primary


# ---------------------------------------------------------------------------
# Reward computation — returns reward metadata for a single transaction.
# discover_state mutates across calls to track the quarterly $1,500 cap.
# ---------------------------------------------------------------------------

def compute_rewards(txn: dict, discover_state: dict) -> dict:
    card_id = txn["card_id"]
    amount = txn["amount"]
    category = txn["category"]
    merchant = txn["merchant"]
    year = int(txn["date"][:4])
    month = int(txn["date"][5:7])

    cfg = CARD_CONFIGS.get(card_id)
    if not cfg:
        return {}

    if cfg["type"] == "points":
        # Check for a streaming bonus defined in the card config
        streaming_bonus = cfg.get("streaming_bonus", {})
        if (
            streaming_bonus
            and category == streaming_bonus.get("applies_to_category")
            and merchant in streaming_bonus.get("merchants", [])
        ):
            rate = streaming_bonus["rate"]
            rate_label = f"{rate}x (streaming)"
        else:
            rate = cfg["category_rates"].get(category, cfg["category_rates"]["other"])
            rate_label = f"{rate}x"

        points = round(amount * rate)
        est_value = round(points * cfg["point_value_cents"] / 100, 2)
        currency = cfg["currency"]
        pv = cfg["point_value_cents"]

        return {
            "type": "points",
            "currency": currency,
            "rate": rate_label,
            "points_earned": points,
            "estimated_value_usd": est_value,
            "note": (
                f"{rate_label} {currency} on {category.title()} — "
                f"{points:,} pts ≈ ${est_value:.2f} at {pv}¢/pt"
            ),
        }

    elif cfg["type"] == "cashback":
        if "flat_rate" in cfg:
            # Simple flat-rate cashback (e.g. Citi Double Cash)
            cashback = round(amount * cfg["flat_rate"], 2)
            pct = int(cfg["flat_rate"] * 100)
            return {
                "type": "cashback",
                "rate": f"{pct}%",
                "cashback_usd": cashback,
                "note": f"{pct}% cashback on all purchases — ${cashback:.2f} earned",
            }

        elif "rotating_schedule" in cfg:
            # Rotating-category cashback (e.g. Discover it)
            qkey = quarter_key(year, month)
            rotating = cfg["rotating_schedule"].get(qkey, {})
            cap = cfg.get("quarterly_cap", 1500.0)

            qualifies_rotating = False
            if category in rotating:
                allowed = rotating[category]  # None means all merchants qualify
                qualifies_rotating = (allowed is None) or (merchant in allowed)

            if qualifies_rotating:
                if qkey not in discover_state:
                    discover_state[qkey] = 0.0

                remaining = cap - discover_state[qkey]
                q_label = qkey.replace("-", " ")  # "2026 Q1"

                if remaining <= 0:
                    cashback = round(amount * cfg["base_rate"], 2)
                    return {
                        "type": "cashback",
                        "rate": "1%",
                        "cashback_usd": cashback,
                        "note": (
                            f"1% cashback — 5% quarterly cap of ${cap:,.0f} "
                            f"reached ({q_label}). ${cashback:.2f} earned."
                        ),
                    }

                at_5pct = min(amount, remaining)
                at_1pct = max(0.0, amount - at_5pct)
                discover_state[qkey] = round(discover_state[qkey] + at_5pct, 2)
                cashback = round(at_5pct * cfg["rotating_rate"] + at_1pct * cfg["base_rate"], 2)
                cap_used = round(discover_state[qkey], 2)

                return {
                    "type": "cashback",
                    "rate": "5% rotating",
                    "cashback_usd": cashback,
                    "note": (
                        f"5% rotating cashback ({q_label}, {category}) — "
                        f"${cashback:.2f} earned. "
                        f"${cap_used:,.2f}/${cap:,.0f} of quarterly cap used."
                    ),
                }
            else:
                cashback = round(amount * cfg["base_rate"], 2)
                return {
                    "type": "cashback",
                    "rate": "1%",
                    "cashback_usd": cashback,
                    "note": f"1% cashback — ${cashback:.2f} earned",
                }

    return {}


# ---------------------------------------------------------------------------
# Statement generation
# ---------------------------------------------------------------------------

def generate_month(
    user_id: str,
    persona: dict,
    year: int,
    month: int,
    discover_state: dict,
) -> dict:
    seasonal = SEASONAL_WEIGHT.get(month, 1.0)
    monthly_variance = random.uniform(0.78, 1.30)
    effective_multiplier = seasonal * monthly_variance

    transactions: list[dict] = []

    for category, (primary_card, prob, (tx_min, tx_max)) in persona["spend"].items():
        pool = MERCHANTS.get(category, [])
        if not pool:
            continue

        subscriptions = [(m, r) for m, r in pool if r[0] == r[1]]
        one_offs = [(m, r) for m, r in pool if r[0] != r[1]]

        # Fixed subscriptions — posted in the first week of the month
        if subscriptions:
            n_subs = random.randint(0, min(2, len(subscriptions)))
            for merchant, (lo, _) in random.sample(subscriptions, n_subs):
                sub_day = min(random.randint(1, 7), days_in_month(year, month))
                card = pick_card(primary_card, prob, persona["cards"])
                transactions.append({
                    "date": date(year, month, sub_day).isoformat(),
                    "merchant": merchant,
                    "category": category,
                    "amount": round(lo, 2),
                    "card_id": card,
                })

        # Variable one-off transactions — count scaled by seasonal + random variance
        base_count = random.randint(tx_min, tx_max)
        count = max(0, round(base_count * effective_multiplier))

        for _ in range(count):
            if not one_offs:
                break
            merchant, (lo, hi) = random.choice(one_offs)
            amount = pick_amount(lo, hi)
            card = pick_card(primary_card, prob, persona["cards"])
            transactions.append({
                "date": random_date(year, month, category),
                "merchant": merchant,
                "category": category,
                "amount": amount,
                "card_id": card,
            })

    transactions.sort(key=lambda t: t["date"])

    # ----- Rewards -----
    # Compute rewards per transaction; build statement-style reward_postings
    statement_close = date(year, month, days_in_month(year, month)).isoformat()
    reward_postings: list[dict] = []

    # Per-card, per-category reward accumulators for rewards_summary
    rewards_summary: dict[str, dict] = {}

    for txn in transactions:
        rewards = compute_rewards(txn, discover_state)
        if not rewards:
            continue

        txn["rewards_earned"] = rewards
        card = txn["card_id"]
        cat = txn["category"]
        txn_date_short = txn["date"][5:]  # "03-26"

        # Build a posting entry that reads like a real statement line item
        if rewards["type"] == "points":
            currency = rewards["currency"]
            pts = rewards["points_earned"]
            est = rewards["estimated_value_usd"]
            posting = {
                "date": statement_close,
                "description": (
                    f"Rewards Posted: {rewards['rate']} {currency} — "
                    f"{txn['merchant']} (${txn['amount']:.2f} charged {txn_date_short})"
                ),
                "card_id": card,
                "type": "points",
                "points_earned": pts,
                "estimated_value_usd": est,
            }
            # Accumulate into rewards_summary
            if card not in rewards_summary:
                rewards_summary[card] = {
                    "type": "points",
                    "currency": currency,
                    "total_points_earned": 0,
                    "total_estimated_value_usd": 0.0,
                    "by_category": {},
                }
            rs = rewards_summary[card]
            rs["total_points_earned"] += pts
            rs["total_estimated_value_usd"] = round(rs["total_estimated_value_usd"] + est, 2)
            bcat = rs["by_category"].setdefault(cat, {"points": 0, "rate": rewards["rate"]})
            bcat["points"] += pts

        else:  # cashback
            cashback = rewards["cashback_usd"]
            posting = {
                "date": statement_close,
                "description": (
                    f"Cashback Posted: {rewards['rate']} — "
                    f"{txn['merchant']} (${txn['amount']:.2f} charged {txn_date_short})"
                ),
                "card_id": card,
                "type": "cashback",
                "cashback_usd": cashback,
            }
            if card not in rewards_summary:
                rewards_summary[card] = {
                    "type": "cashback",
                    "total_cashback_usd": 0.0,
                    "by_category": {},
                }
            rs = rewards_summary[card]
            rs["total_cashback_usd"] = round(rs["total_cashback_usd"] + cashback, 2)
            bcat = rs["by_category"].setdefault(cat, {"cashback_usd": 0.0, "rate": rewards["rate"]})
            bcat["cashback_usd"] = round(bcat["cashback_usd"] + cashback, 2)

        reward_postings.append(posting)

    # ----- Spend summary -----
    total = round(sum(t["amount"] for t in transactions), 2)
    by_category: dict[str, float] = {}
    by_card: dict[str, float] = {}
    for t in transactions:
        by_category[t["category"]] = round(by_category.get(t["category"], 0.0) + t["amount"], 2)
        by_card[t["card_id"]] = round(by_card.get(t["card_id"], 0.0) + t["amount"], 2)

    return {
        "user_id": user_id,
        "name": persona["name"],
        "month": f"{year}-{month:02d}",
        "cards": persona["cards"],
        "transactions": transactions,
        "reward_postings": reward_postings,
        "summary": {
            "total_spend": total,
            "transaction_count": len(transactions),
            "by_category": by_category,
            "by_card": by_card,
        },
        "rewards_summary": rewards_summary,
    }


def main() -> None:
    random.seed(SEED)
    base = Path("data/statements")

    print("Generating statements with reward postings...\n")
    for user_id, persona in PERSONAS.items():
        user_dir = base / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        print(f"{persona['name']} ({user_id})")

        discover_state: dict = {}  # tracks Discover quarterly cap across months

        for year, month in MONTHS:
            data = generate_month(user_id, persona, year, month, discover_state)
            out = user_dir / f"{year}-{month:02d}.json"
            out.write_text(json.dumps(data, indent=2))

            # Compact rewards line for terminal output
            rw = data["rewards_summary"]
            rw_parts = []
            for card_id, rs in rw.items():
                short = card_id.split("-")[0].title()
                if rs["type"] == "points":
                    rw_parts.append(f"{short}: {rs['total_points_earned']:,} pts (≈${rs['total_estimated_value_usd']:.2f})")
                else:
                    rw_parts.append(f"{short}: ${rs['total_cashback_usd']:.2f} cashback")

            print(
                f"  {year}-{month:02d}  "
                f"{data['summary']['transaction_count']:>3} txns  "
                f"${data['summary']['total_spend']:>8,.2f}    "
                f"rewards → {' | '.join(rw_parts) if rw_parts else 'none'}"
            )
        print()

    print("Done. Files written to data/statements/")


if __name__ == "__main__":
    main()
