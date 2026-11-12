"""
Canonical Currency Conversion Module (AG-003).

Provides a single source of truth for foreign exchange (FX) rates across all backend
agents, tools, and endpoints, preventing conflicting static tables and double-conversion bugs.

FX Direction Convention:
- USD is the base currency (1.0 USD).
- USD_TO_CURRENCY values represent: 1.0 USD = X units of foreign currency.
  Example: USD_TO_CURRENCY["INR"] = 83.0 means 1 USD = 83.0 INR.
  Example: USD_TO_CURRENCY["EUR"] = 0.92 means 1 USD = 0.92 EUR.
"""

from typing import Dict, Optional

# Canonical baseline exchange rates (Units of CURRENCY per 1.0 USD)
USD_TO_CURRENCY: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,       # 1 USD = 0.92 EUR (~1 EUR = 1.087 USD)
    "GBP": 0.79,       # 1 USD = 0.79 GBP (~1 GBP = 1.266 USD)
    "INR": 83.0,       # 1 USD = 83.0 INR (~1 INR = 0.01205 USD)
    "JPY": 155.0,      # 1 USD = 155.0 JPY (~1 JPY = 0.00645 USD)
    "CAD": 1.36,       # 1 USD = 1.36 CAD (~1 CAD = 0.735 USD)
    "AUD": 1.52,       # 1 USD = 1.52 AUD (~1 AUD = 0.658 USD)
    "CHF": 0.90,       # 1 USD = 0.90 CHF (~1 CHF = 1.111 USD)
    "SEK": 10.8,       # 1 USD = 10.8 SEK (~1 SEK = 0.0926 USD)
    "SGD": 1.35,       # 1 USD = 1.35 SGD (~1 SGD = 0.741 USD)
    "THB": 36.5,       # 1 USD = 36.5 THB (~1 THB = 0.0274 USD)
    "NZD": 1.65,       # 1 USD = 1.65 NZD (~1 NZD = 0.606 USD)
    "KRW": 1330.0,     # 1 USD = 1330.0 KRW (~1 KRW = 0.000752 USD)
    "CNY": 7.24,       # 1 USD = 7.24 CNY (~1 CNY = 0.138 USD)
}


def get_rate_to_usd(currency: Optional[str]) -> float:
    """
    Return the multiplier to convert 1 unit of `currency` to USD.
    Example: get_rate_to_usd("INR") -> ~0.012048 (since 1 INR = 1/83 USD).
    """
    if not currency:
        return 1.0
    code = currency.upper().strip()
    rate = USD_TO_CURRENCY.get(code, 1.0)
    return 1.0 / rate if rate > 0 else 1.0


def get_rate_from_usd(currency: Optional[str]) -> float:
    """
    Return the multiplier to convert 1 USD to `currency`.
    Example: get_rate_from_usd("INR") -> 83.0 (1 USD = 83 INR).
    """
    if not currency:
        return 1.0
    code = currency.upper().strip()
    return USD_TO_CURRENCY.get(code, 1.0)


def to_usd(amount: float, from_currency: Optional[str]) -> float:
    """
    Convert an amount from `from_currency` to USD.
    If already in USD, returns amount directly.
    """
    if amount == 0:
        return 0.0
    if not from_currency or from_currency.upper().strip() == "USD":
        return amount
    code = from_currency.upper().strip()
    rate = USD_TO_CURRENCY.get(code, 1.0)
    return round(amount / rate, 2) if rate > 0 else amount


def from_usd(amount: float, to_currency: Optional[str]) -> float:
    """
    Convert an amount from USD to `to_currency`.
    If already in USD, returns amount directly.
    """
    if amount == 0:
        return 0.0
    if not to_currency or to_currency.upper().strip() == "USD":
        return amount
    code = to_currency.upper().strip()
    rate = USD_TO_CURRENCY.get(code, 1.0)
    return round(amount * rate, 2)


def convert_currency(
    amount: float,
    from_currency: Optional[str],
    to_currency: Optional[str]
) -> float:
    """
    Safely convert an amount between any two currencies.
    Guarantees idempotency when currencies match (no precision degradation).
    
    Prevents double-conversion (AG-004): if an offer is already in INR,
    convert_currency(1000, "INR", "INR") returns 1000.0 without applying USD*83 again.
    """
    if amount == 0:
        return 0.0
    
    from_code = (from_currency or "USD").upper().strip()
    to_code = (to_currency or "USD").upper().strip()
    
    if from_code == to_code:
        return round(amount, 2)
    
    # Normalise through USD base
    usd_val = to_usd(amount, from_code)
    return from_usd(usd_val, to_code)

