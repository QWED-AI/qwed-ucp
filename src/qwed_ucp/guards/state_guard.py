from typing import Any

from z3 import Implies, Or, Solver, String, sat


class StateGuard:
    """
    Verifies e-commerce state transitions using Z3 Solver.
    Enforces the Universal Commerce Protocol (UCP) State Machine.
    """
    def __init__(self):
        self.solver = Solver()
        
    def verify_transition(self, current_state: str, action: str) -> dict[str, Any]:
        """
        Verifies if an action is legally allowed in the current commerce state.
        """
        # Clear solver for new check
        self.solver.reset()
        
        s_curr = current_state.lower().strip()
        s_act = action.lower().strip()
        
        # Define atoms (Logic Variables could be used, but here we encode logic directly)
        
        # Valid Transitions Logic (UCP Model):
        # 1. SHIP action requires PAID state
        # 2. REFUND action requires PAID, SHIPPED, or DELIVERED state
        # 3. CANCEL action is allowed from PENDING or PAID (before shipping) - *Adding heuristic constraint*
        
        
        # We formulate the "Validity Condition":
        # The transition is VALID IF...
        
        # Combining logic: 
        # We want to check if the specific combination provided is VALID.
        # But Z3 is best for solving "Is there a case where...". 
        # Here we just implement the rule check directly or use Z3 to validate complex multi-step if needed.
        # Following the prompt's direction, we use Z3 to check consistency of the transition.
        
        # We assert the specific scenario is valid according to rules.
        # Actually, let's use Z3 to *define* the rules and check if the *current instance* satisfies them.
        
        State = String('Start_State')
        Action = String('Action')
        
        # Rules
        # If Action is Ship, State MUST be Paid
        rule_ship = Implies(Action == "ship", State == "paid")
        
        # If Action is Refund, State MUST be Paid/Shipped/Delivered
        rule_refund = Implies(Action == "refund", Or(State == "paid", State == "shipped", State == "delivered"))
        
        # If Action is Pay, State MUST be Pending
        rule_pay = Implies(Action == "pay", State == "pending")

        self.solver.add(rule_ship)
        self.solver.add(rule_refund)
        self.solver.add(rule_pay)
        
        # Add the instance constraints
        self.solver.add(State == s_curr)
        self.solver.add(Action == s_act)
        
        # Check satisifiability
        # If SAT, then the instance is consistent with rules.
        # If UNSAT, then the instance violates a rule.
        
        if self.solver.check() == sat:
            return {"verified": True}
        else:
            return {
                "verified": False, 
                "error": f"Invalid State Transition: Cannot perform '{action}' while order is '{current_state}'."
            }
