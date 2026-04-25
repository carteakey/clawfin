"""
Transaction categorizer — AI batch by merchant (cached) + rule fallback.

Strategy:
1. Collect unique normalized merchant names from the batch
2. Check CategoryRule table for existing matches (cache)
3. For remaining unknowns, batch-send to LLM for classification
4. Store results as new CategoryRules for future cache hits
5. Fall back to rule-based regex if no AI provider configured
"""
import asyncio
import json
import re
from sqlalchemy.orm import Session
from backend.db.models import CategoryRule, Category, DEFAULT_CATEGORIES


def ai_categorize_batch(merchants: list[str], categories: list[str]) -> dict[str, str]:
    """
    Call the configured AI provider to classify merchants.
    Returns {merchant: category} for merchants the LLM felt confident about.
    Gracefully returns {} on any error.
    """
    from backend.ai import provider

    if not merchants:
        return {}

    prompt = (
        "Classify each merchant name into exactly one of the allowed categories. "
        "Return JSON only, no prose, shaped as {\"merchant\": \"Category\", ...}.\n\n"
        f"Allowed categories: {', '.join(categories)}\n\n"
        f"Merchants: {json.dumps(merchants)}"
    )

    try:
        resp = asyncio.run(provider.chat_completion(
            messages=[
                {"role": "system", "content": "You classify merchant names into finance categories. Return JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        ))
    except Exception:
        return {}

    content = (resp.get("content") or "").strip()
    # Be tolerant of code fences
    if content.startswith("```"):
        content = content.split("```", 2)[-1].strip()
        if content.startswith("json"):
            content = content[4:].strip()
        content = content.rsplit("```", 1)[0].strip()

    try:
        data = json.loads(content)
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}
    return {str(k).strip().lower(): str(v) for k, v in data.items() if v in categories}


# ─── Rule-based fallback patterns ────────────────────────────────────

DEFAULT_RULES = [
    # Groceries
    (r"loblaws|no\s*frills|superstore|metro|sobeys|freshco|food\s*basics|walmart\s*super|costco|t&t|farm\s*boy|whole\s*foods|longos", "Groceries"),
    # Dining
    (r"uber\s*eats|doordash|skip\s*the\s*dishes|mcdonald|tim\s*horton|starbucks|restaurant|pizza|sushi|cafe|coffee|shawarma|burrito|subway|popeyes|wendy|a&w|dairy\s*queen|boston\s*pizza", "Dining"),
    # Transit
    (r"presto|uber\s+(?!eats)|lyft|ttc|transit|parking|gas\s*station|petro|shell|esso|canadian\s*tire\s*gas|go\s*transit", "Transit"),
    # Subscriptions
    (r"netflix|spotify|apple\.com|google\s*(play|storage)|amazon\s*prime|disney|youtube|hbo|crave|audible|dropbox|icloud|microsoft\s*365|github|notion|figma|adobe|chatgpt|openai", "Subscriptions"),
    # Rent
    (r"\brent\b|landlord|property\s*management|rentpayment", "Rent"),
    # Housing
    (r"mortgage|property\s*tax|home\s*depot|ikea|wayfair|structube|canadian\s*tire(?!\s*gas)|rona|lowes", "Housing"),
    # Utilities
    (r"hydro|enbridge|toronto\s*hydro|alectra|rogers|bell\s*(?!.*restaurant)|telus|fido|koodo|virgin\s*plus|teksavvy|internet|phone\s*bill", "Utilities"),
    # Insurance
    (r"insurance|manulife|sunlife|intact|td\s*insurance|life\s*policy|security\s*national", "Insurance"),
    # Loan / installments
    (r"installment|instalment|\bloan\b|\bemi\b|membership\s*fee\s*installment|financ", "Loan"),
    # Fees
    (r"\bfee\b|service\s*charge|overdraft|nsf|atm\s*fee|interest\s*charge", "Fees"),
    # Transfer
    (r"e-?transfer|transfer|payment\s*-\s*thank|autopay|interac\s*e-?transfer", "Transfer"),
    # Income
    (r"payroll|salary|direct\s*deposit|employer|tax\s*refund|cerb|ei\s*deposit|gst.*credit|canada\s*child", "Income"),
    # Entertainment
    (r"cineplex|nintendo|steam|playstation|xbox|concert|ticket|event|museum|zoo|aquarium|ripley", "Entertainment"),
    # Health
    (r"pharmacy|shoppers\s*drug|rexall|physiotherapy|dentist|doctor|clinic|hospital|drug\s*mart|lens|optom|chiropract", "Health"),
    # Shopping
    (r"amazon(?!\s*prime)|best\s*buy|winners|marshalls|h&m|zara|uniqlo|old\s*navy|gap|indigo|chapters|sport\s*chek|nike|adidas|apple\s*store", "Shopping"),
]


def categorize_transactions(
    transactions: list[dict],
    db: Session,
    ai_categorize_fn=None,
) -> list[dict]:
    """
    Categorize a list of transaction dicts in-place.

    1. Check cached CategoryRules by merchant
    2. Batch uncategorized merchants to AI (if available)
    3. Fall back to regex rules
    """
    # Get all existing rules from DB
    rules = db.query(CategoryRule).order_by(CategoryRule.priority.desc()).all()
    rule_cache = {r.pattern.lower(): r.category for r in rules}

    # Get valid category names
    categories = db.query(Category).all()
    valid_categories = {c.name for c in categories}
    if not valid_categories:
        valid_categories = {c["name"] for c in DEFAULT_CATEGORIES}

    # Collect unique merchants that need categorization
    uncategorized_merchants: set[str] = set()

    for tx in transactions:
        merchant = tx.get("merchant", "").strip().lower()
        if not merchant:
            tx["category"] = "Other"
            continue

        # Check rule cache first
        if merchant in rule_cache:
            tx["category"] = rule_cache[merchant]
            continue

        # Check regex rules
        matched = False
        for pattern, category in DEFAULT_RULES:
            if re.search(pattern, merchant, re.IGNORECASE):
                tx["category"] = category
                rule_cache[merchant] = category
                matched = True
                break

        if not matched:
            uncategorized_merchants.add(merchant)
            tx["category"] = "Other"  # default, may be overridden by AI

    # Batch AI categorization for unknowns
    if uncategorized_merchants and ai_categorize_fn:
        try:
            ai_results = ai_categorize_fn(
                list(uncategorized_merchants),
                list(valid_categories),
            )
            # ai_results: dict[str, str] mapping merchant -> category
            if ai_results:
                for merchant, category in ai_results.items():
                    if category in valid_categories:
                        rule_cache[merchant] = category
                        # Save as cached rule for future
                        db.add(CategoryRule(
                            pattern=merchant,
                            category=category,
                            priority=0,
                            is_regex=False,
                        ))

                # Apply AI results to transactions
                for tx in transactions:
                    merchant = tx.get("merchant", "").strip().lower()
                    if merchant in rule_cache and tx["category"] == "Other":
                        tx["category"] = rule_cache[merchant]

                db.commit()
        except Exception:
            pass  # AI failure is non-fatal; keep rule-based results

    return transactions
