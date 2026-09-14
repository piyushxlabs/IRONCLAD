"""Tool: audit_retainage_math.

Adheres strictly to AGENT_LOGIC_SPEC.md Section 3 and Section 4.
Deterministic math engine for verifying retainage withholding and net recommended release
for a single draw-packet line item with zero LLM math (Prohibition 2).
"""

from decimal import Decimal, InvalidOperation

from strands import tool

from src.errors import StateValidationError
from src.tools.schemas.pydantic_models import (
    AuditRetainageMathInput,
    AuditRetainageMathOutput,
)


def _to_decimal(val: Decimal | str | float, param_name: str) -> Decimal:
    """Safely convert numeric input to exact Decimal."""
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError) as e:
        raise StateValidationError(
            message=f"Invalid numeric input for '{param_name}': {val}",
            incident_context={"param_name": param_name, "value": str(val)},
            node_name="audit_retainage_math",
        ) from e


@tool
async def audit_retainage_math(
    contract_retainage_pct: float | Decimal | str,
    current_billed: Decimal | str | float,
    stored_materials: Decimal | str | float = Decimal("0.00"),
    prior_payments: Decimal | str | float = Decimal("0.00"),
) -> AuditRetainageMathOutput:
    """Deterministically calculate gross amount, retainage deduction, and net payable release."""
    pct = _to_decimal(contract_retainage_pct, "contract_retainage_pct")
    billed = _to_decimal(current_billed, "current_billed")
    stored = _to_decimal(stored_materials, "stored_materials")
    prior = _to_decimal(prior_payments, "prior_payments")

    # Strict input validation
    if pct < Decimal("0.00") or pct > Decimal("1.00"):
        raise StateValidationError(
            message=f"contract_retainage_pct must be within [0.0, 1.0]. Got {pct}.",
            incident_context={"contract_retainage_pct": str(pct)},
            node_name="audit_retainage_math",
        )
    if billed < Decimal("0.00") or stored < Decimal("0.00") or prior < Decimal("0.00"):
        raise StateValidationError(
            message="Monetary parameters to audit_retainage_math must be non-negative.",
            incident_context={
                "current_billed": str(billed),
                "stored_materials": str(stored),
                "prior_payments": str(prior),
            },
            node_name="audit_retainage_math",
        )

    # Validate against input model
    AuditRetainageMathInput(
        contract_retainage_pct=pct,
        current_billed=billed,
        stored_materials=stored,
        prior_payments=prior,
    )

    # Deterministic calculation
    gross_amount = billed + stored
    retainage_withheld = (gross_amount * pct).quantize(Decimal("0.01"))
    net_release = gross_amount - retainage_withheld - prior

    trace = [
        f"gross_amount_requested = current_billed ({billed}) + stored_materials ({stored}) = {gross_amount}",
        f"contractual_retainage_withheld = gross ({gross_amount}) * retainage_pct ({pct}) = {retainage_withheld}",
        f"net_recommended_release = gross ({gross_amount}) - retainage ({retainage_withheld}) - prior ({prior}) = {net_release}",
    ]

    return AuditRetainageMathOutput(
        success=True,
        gross_amount_requested=gross_amount,
        contractual_retainage_withheld=retainage_withheld,
        net_recommended_release=net_release,
        calculation_trace=trace,
        error=None,
    )
