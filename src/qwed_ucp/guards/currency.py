"""Currency Guard - Verifies currency consistency and format.

Validates that:
- Currency code is valid ISO 4217
- Currency is consistent across all amounts
- Currency conversions are accurate (if applicable)
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from qwed_ucp.types import TrustStatus, reconcile_trust_status


# Common ISO 4217 currency codes
VALID_CURRENCIES = {
    # Major currencies
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    # Asian currencies
    "CNY", "HKD", "SGD", "KRW", "INR", "THB", "MYR", "PHP", "IDR", "VND",
    # European currencies
    "NOK", "SEK", "DKK", "PLN", "CZK", "HUF", "RUB", "TRY",
    # Latin American
    "MXN", "BRL", "ARS", "CLP", "COP", "PEN",
    # Middle East / Africa
    "AED", "SAR", "ZAR", "EGP", "ILS",
    # Crypto (some merchants accept)
    "BTC", "ETH", "USDT", "USDC",
}


@dataclass
class CurrencyGuardResult:
    """Result from Currency Guard verification."""
    
    verified: bool = False
    error: Optional[str] = None
    details: dict = field(default_factory=dict)
    status: Optional[TrustStatus] = None

    def __post_init__(self):
        self.verified, self.status = reconcile_trust_status(self.verified, self.status)


class CurrencyGuard:
    """
    Verify currency format and consistency.
    
    Checks:
    1. Currency code is valid 3-letter ISO 4217 code
    2. Currency is consistent throughout checkout
    3. Amounts are appropriate for currency (e.g., JPY has no decimals)
    """
    
    # Currencies that don't use decimal places
    ZERO_DECIMAL_CURRENCIES = {"JPY", "KRW", "VND", "IDR"}
    
    def __init__(self, custom_currencies: set[str] = None):
        """
        Initialize Currency Guard.
        
        Args:
            custom_currencies: Additional valid currency codes
        """
        self.valid_currencies = VALID_CURRENCIES.copy()
        if custom_currencies:
            self.valid_currencies.update(custom_currencies)
    
    def verify(self, checkout: dict[str, Any]) -> CurrencyGuardResult:
        """
        Verify currency in checkout object.
        
        Args:
            checkout: UCP checkout object
            
        Returns:
            CurrencyGuardResult
        """
        currency = checkout.get("currency")
        
        if currency is None:
            return CurrencyGuardResult(
                verified=False,
                error="Currency is required but missing",
                details={}
            )
        
        # Check format
        if not isinstance(currency, str) or len(currency) != 3:
            return CurrencyGuardResult(
                verified=False,
                error=f"Currency must be 3-letter code, got: {currency}",
                details={"currency": currency}
            )
        
        currency = currency.upper()
        
        # Check if valid
        if currency not in self.valid_currencies:
            return CurrencyGuardResult(
                verified=False,
                error=f"Unknown currency code: {currency}",
                details={
                    "currency": currency,
                    "suggestion": "Use ISO 4217 3-letter codes like USD, EUR, GBP"
                }
            )
        
        # Check decimal places for zero-decimal currencies
        is_zero_decimal = currency in self.ZERO_DECIMAL_CURRENCIES
        totals = checkout.get("totals", [])
        
        for total in totals:
            amount = total.get("amount")
            if amount is not None and is_zero_decimal:
                # Check if amount has decimals
                if isinstance(amount, float) and amount != int(amount):
                    return CurrencyGuardResult(
                        verified=False,
                        error=f"{currency} doesn't use decimal places, but got {amount}",
                        details={
                            "currency": currency,
                            "amount": amount,
                            "type": total.get("type")
                        }
                    )
        
        return CurrencyGuardResult(
            verified=True,
            details={
                "currency": currency,
                "is_zero_decimal": is_zero_decimal,
                "totals_count": len(totals)
            }
        )
    
    def verify_conversion(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        converted_amount: Decimal,
        exchange_rate: Decimal
    ) -> CurrencyGuardResult:
        """
        Verify a currency conversion.
        
        Args:
            amount: Original amount
            from_currency: Source currency
            to_currency: Target currency
            converted_amount: Claimed converted amount
            exchange_rate: Exchange rate used
            
        Returns:
            CurrencyGuardResult
        """
        expected = (amount * exchange_rate).quantize(Decimal("0.01"))
        actual = converted_amount.quantize(Decimal("0.01"))
        
        if expected == actual:
            return CurrencyGuardResult(
                verified=True,
                details={
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "original_amount": float(amount),
                    "exchange_rate": float(exchange_rate),
                    "converted_amount": float(actual)
                }
            )
        else:
            return CurrencyGuardResult(
                verified=False,
                error=f"{amount} {from_currency} × {exchange_rate} = {expected} {to_currency}, not {actual}",
                details={
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "original_amount": float(amount),
                    "exchange_rate": float(exchange_rate),
                    "expected": float(expected),
                    "actual": float(actual),
                    "difference": float(expected - actual)
                }
            )
