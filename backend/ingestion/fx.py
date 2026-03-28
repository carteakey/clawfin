"""
Bank of Canada FX rate fetcher.

Uses the BoC Valet API to get daily exchange rates.
Docs: https://www.bankofcanada.ca/valet/docs

Note: Rates have a one-business-day lag and don't cover crypto or minor currencies.
"""
import httpx
from datetime import date, timedelta
from sqlalchemy.orm import Session
from backend.db.models import FxRate


# BoC series for USD/CAD — most common need
BOC_SERIES = {
    "USD": "FXUSDCAD",
    "EUR": "FXEURCAD",
    "GBP": "FXGBPCAD",
}

VALET_BASE = "https://www.bankofcanada.ca/valet/observations"


async def fetch_rate(from_currency: str, to_currency: str = "CAD") -> float | None:
    """Fetch the latest FX rate from Bank of Canada."""
    if from_currency.upper() == "CAD":
        return 1.0

    series = BOC_SERIES.get(from_currency.upper())
    if not series:
        return None

    end = date.today()
    start = end - timedelta(days=7)  # Look back a week to handle weekends/holidays

    url = f"{VALET_BASE}/{series}/json"
    params = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            observations = data.get("observations", [])
            if not observations:
                return None

            # Get the most recent observation
            latest = observations[-1]
            rate_str = latest.get(series, {}).get("v", None)
            if rate_str:
                return float(rate_str)
        except Exception:
            return None

    return None


async def get_rate(from_currency: str, to_currency: str = "CAD", db: Session | None = None) -> float:
    """
    Get FX rate, checking DB cache first.

    Returns 1.0 for CAD->CAD. Returns cached rate if fresh (today).
    Fetches from BoC if stale or missing.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return 1.0

    # Check cache
    if db:
        cached = (
            db.query(FxRate)
            .filter(
                FxRate.from_currency == from_currency,
                FxRate.to_currency == to_currency,
                FxRate.rate_date == date.today(),
            )
            .first()
        )
        if cached:
            return cached.rate

    # Fetch fresh rate
    rate = await fetch_rate(from_currency, to_currency)
    if rate is None:
        # Fallback: try most recent cached rate regardless of date
        if db:
            fallback = (
                db.query(FxRate)
                .filter(
                    FxRate.from_currency == from_currency,
                    FxRate.to_currency == to_currency,
                )
                .order_by(FxRate.rate_date.desc())
                .first()
            )
            if fallback:
                return fallback.rate
        return 1.0  # Last resort

    # Cache the rate
    if db:
        db.add(FxRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            rate_date=date.today(),
            source="bank_of_canada",
        ))
        db.commit()

    return rate


def convert(amount: float, from_currency: str, rate: float) -> float:
    """Convert an amount to CAD using a given rate."""
    if from_currency.upper() == "CAD":
        return amount
    return round(amount * rate, 2)
