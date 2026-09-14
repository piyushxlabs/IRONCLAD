"""Tool: verify_lien_chain_integrity.

Adheres strictly to AGENT_LOGIC_SPEC.md Section 3 and Section 4.
Validates the chronological sequence of notarized lien waiver execution dates against
the payment/check date and classifies overall lien-chain status.
"""

from datetime import date
from typing import Any

from strands import tool

from src.errors import StateValidationError
from src.tools.schemas.pydantic_models import (
    LienWaiverRecord,
    VerifyLienChainIntegrityInput,
    VerifyLienChainIntegrityOutput,
    WaiverFinding,
)


def _parse_date(d: date | str) -> date:
    """Parse date or ISO string."""
    if isinstance(d, date):
        return d
    try:
        return date.fromisoformat(str(d))
    except ValueError as e:
        raise StateValidationError(
            message=f"Invalid date format: '{d}'. Must be ISO format YYYY-MM-DD.",
            incident_context={"date": str(d)},
            node_name="verify_lien_chain_integrity",
        ) from e


@tool
async def verify_lien_chain_integrity(
    waivers: list[LienWaiverRecord | dict[str, Any]],
    check_date: date | str,
) -> VerifyLienChainIntegrityOutput:
    """Validate chronological sequence of notarized waiver execution dates against check date."""
    if not waivers:
        raise StateValidationError(
            message="Waivers list cannot be empty. Empty waiver list is a MISSING_WAIVER defect.",
            incident_context={"waivers_count": 0},
            node_name="verify_lien_chain_integrity",
        )

    parsed_check_date = _parse_date(check_date)

    # Validate and normalize waiver records
    typed_waivers: list[LienWaiverRecord] = []
    for w in waivers:
        if isinstance(w, LienWaiverRecord):
            typed_waivers.append(w)
        elif isinstance(w, dict):
            typed_waivers.append(LienWaiverRecord.model_validate(w))
        else:
            raise StateValidationError(
                message=f"Invalid waiver record type: {type(w)}",
                incident_context={"type": str(type(w))},
                node_name="verify_lien_chain_integrity",
            )

    # Validate input model
    VerifyLienChainIntegrityInput(waivers=typed_waivers, check_date=parsed_check_date)

    findings: list[WaiverFinding] = []
    has_pre_dated = False
    has_missing_date = False

    for waiver in typed_waivers:
        if waiver.notary_execution_date is None:
            findings.append(
                WaiverFinding(
                    waiver_id=waiver.waiver_id,
                    finding="MISSING_NOTARY_DATE",
                )
            )
            has_missing_date = True
        elif waiver.notary_execution_date < parsed_check_date:
            # Suspect: Notary executed BEFORE the check/payment date
            findings.append(
                WaiverFinding(
                    waiver_id=waiver.waiver_id,
                    finding="PRE_DATED_NOTARY",
                )
            )
            has_pre_dated = True
        else:
            findings.append(
                WaiverFinding(
                    waiver_id=waiver.waiver_id,
                    finding="OK",
                )
            )

    # Determine overall lien-chain status
    if has_pre_dated:
        overall_status = "SUSPECT_PRE_DATED_NOTARY"
    elif has_missing_date:
        overall_status = "INVALID_FORM"
    else:
        overall_status = "VALID"

    return VerifyLienChainIntegrityOutput(
        success=True,
        lien_chain_status=overall_status,
        findings=findings,
        error=None,
    )
