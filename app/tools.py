"""Deterministic demo tool implementations for the Step 3 agent loop."""

DEMO_PRICES = {
    "medjool": 42.0,
    "khalas": 18.0,
    "fard": 22.0,
    "lulu": 20.0,
    "ajwa": 55.0,
    "sukkary": 24.0,
}
DEMO_MIN_ORDER_KG = 10.0


def record_inquiry(
    name: str,
    variety: str,
    quantity_kg: float,
    packaging: str,
    city: str,
    notes: str,
) -> str:
    """Return a fixed fake lead row ID without writing external state."""
    return "demo-lead-001"


def get_price_quote(variety: str, quantity_kg: float) -> dict[str, float | bool]:
    """Return a deterministic fake price quote."""
    quantity = float(quantity_kg)
    unit_price = DEMO_PRICES.get(variety.strip().lower(), 25.0)
    return {
        "unit_price": unit_price,
        "total": round(unit_price * quantity, 2),
        "moq_ok": quantity >= DEMO_MIN_ORDER_KG,
    }


def check_availability(date_iso: str) -> list[str]:
    """Return two fixed demo slots for the requested date."""
    return [
        f"{date_iso}T10:00:00+04:00",
        f"{date_iso}T14:00:00+04:00",
    ]


def book_meeting(
    name: str,
    phone: str,
    start_iso: str,
    notes: str,
) -> dict[str, str]:
    """Return a deterministic fake calendar booking."""
    return {
        "event_id": "demo-event-001",
        "gcal_link": "https://calendar.google.com/calendar/event?eid=demo-event-001",
    }
