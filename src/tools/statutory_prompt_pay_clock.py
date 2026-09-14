"""Tool: statutory_prompt_pay_clock.

Adheres strictly to AGENT_LOGIC_SPEC.md Section 3 and Section 4.
Calculates prompt-payment countdown, deadline timestamp, and applicable penalty interest rate
for a given jurisdiction, invoice date, and rider clause classification.
"""

from datetime import date

from strands import tool

from src.errors import StateValidationError
from src.statutory_reference import calculate_statutory_prompt_pay_clock as calc_clock
from src.tools.schemas.pydantic_models import (
    StatutoryPromptPayClockInput,
    StatutoryPromptPayClockOutput,
)


@tool
async def statutory_prompt_pay_clock(
    state_jurisdiction: str,
    invoice_receipt_date: date | str,
    contract_clause: str,
) -> StatutoryPromptPayClockOutput:
    """Calculate prompt-payment countdown, deadline timestamp, and applicable monthly penalty interest."""
    cleaned_state = state_jurisdiction.strip().upper()
    cleaned_clause = contract_clause.strip().lower()

    if cleaned_clause not in {"pay-if-paid", "pay-when-paid"}:
        raise StateValidationError(
            message=f"contract_clause must be 'pay-if-paid' or 'pay-when-paid'. Got '{contract_clause}'.",
            incident_context={"contract_clause": contract_clause},
            node_name="statutory_prompt_pay_clock",
        )

    # Validate input model
    parsed_date = (
        invoice_receipt_date
        if isinstance(invoice_receipt_date, date)
        else date.fromisoformat(str(invoice_receipt_date))
    )
    StatutoryPromptPayClockInput(
        state_jurisdiction=cleaned_state,
        invoice_receipt_date=parsed_date,
        contract_clause=cleaned_clause,  # type: ignore[arg-type]
    )

    try:
        clock_result = calc_clock(
            state_jurisdiction=cleaned_state,
            invoice_receipt_date=parsed_date,
            contract_clause=cleaned_clause,
        )
        return StatutoryPromptPayClockOutput(
            success=True,
            state=clock_result.state,
            days_remaining=clock_result.days_remaining,
            deadline_timestamp=clock_result.deadline_timestamp,
            penalty_interest_rate=clock_result.penalty_interest_rate,
            statute_reference=clock_result.statute_reference,
            error=None,
        )
    except StateValidationError:
        raise
    except (ValueError, KeyError, RuntimeError, TypeError, OSError) as e:
        return StatutoryPromptPayClockOutput(
            success=False,
            error=f"Statutory clock calculation failed: {e!s}",
        )
