from typing import Any

from .guards.money_guard import MoneyGuard
from .guards.state_guard import StateGuard


class UCPVerifier:
    """
    Universal Commerce Protocol (UCP) Verifier.
    Middleware that runs deterministic checks on Commerce Intents.
    """
    def __init__(self):
        self.money = MoneyGuard()
        self.state = StateGuard()

    def verify_checkout(self, checkout_json: dict[str, Any]) -> dict[str, Any]:
        """
        Main entry point for Universal Commerce Protocol verification.
        checkout_json structure expected:
        {
            "line_items": [{"price": 10, "quantity": 2}, ...],
            "tax_total": 2.0,
            "discount_total": 1.0,
            "grand_total": 21.0,
            "status": "paid",
            "intent": "ship"
        }
        """
        report = {"verified": True, "errors": []}
        
        # 1. Check Money (Math Integrity)
        if "grand_total" in checkout_json:
            # Extract totals from UCP schema structure
            money_res = self.money.verify_cart_totals(
                checkout_json.get("line_items", []),
                checkout_json.get("tax_total", 0),
                checkout_json.get("discount_total", 0),
                checkout_json.get("grand_total", 0)
            )
            if not money_res["verified"]:
                report["verified"] = False
                report["errors"].append(money_res["error"])

        # 2. Check State (Logic Integrity)
        if "status" in checkout_json and "intent" in checkout_json:
            state_res = self.state.verify_transition(
                checkout_json["status"], 
                checkout_json["intent"]
            )
            if not state_res["verified"]:
                report["verified"] = False
                report["errors"].append(state_res["error"])
        
        # If everything implies True (or is absent), we return results
        return report
