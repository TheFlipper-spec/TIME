"""Economy rules: clue rewards, utilities, loans, shopping."""
from __future__ import annotations

from ..config import LOAN_INTEREST, UTILITIES_PER_DAY


def reward_for_yesterday(state, yesterday_day: int) -> float:
    """Sum of rewards for clues found on `yesterday_day`."""
    total = 0.0
    for clue_id, found_day in state.clue_found_day.items():
        if found_day == yesterday_day:
            from .clues import get as get_clue
            total += get_clue(clue_id).reward
    return total


def pay_utilities(state) -> tuple[bool, float]:
    """Pay $30 utilities. Returns (paid, amount)."""
    amount = UTILITIES_PER_DAY
    if state.money >= amount:
        state.money -= amount
        state.stats["utilities_paid"] += 1
        return True, amount
    state.utilities_debt += amount
    state.stats["utilities_missed"] += 1
    return False, amount


def loan_due_total(loan: dict) -> float:
    return round(loan["amount"] * (1.0 + LOAN_INTEREST))


def can_repay(state, loan: dict) -> bool:
    return state.money >= loan_due_total(loan)


def repay_loan(state, loan: dict) -> bool:
    total = loan_due_total(loan)
    if state.money < total:
        return False
    state.money -= total
    state.loans.remove(loan)
    state.stats["loans_repaid"] += 1
    return True


def take_loan(state, amount: float, current_total_min: int) -> dict:
    loan = {
        "amount": round(float(amount), 2),
        "due_min": current_total_min + 3 * 24 * 60,
    }
    state.loans.append(loan)
    state.money += loan["amount"]
    return loan
