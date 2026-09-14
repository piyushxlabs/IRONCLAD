"""Statutory Reference Lookup Module.

Adheres strictly to AGENT_ORCHESTRATION_BLUEPRINT.md Section 7, AGENT_LOGIC_SPEC.md Section 6,
and AGENT_BEHAVIOR_PROFILE.md Section 11.
Provides deterministic, read-only keyed lookup and prompt-pay deadline calculation against
versioned jurisdiction reference data (reference-table v2026.3).
"""

import json
import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.errors import StateValidationError
from src.state.schema import StatutoryClock


class StatutoryJurisdictionRecord(BaseModel):
    """Statutory prompt-pay and retainage rules for a US state/jurisdiction."""

    model_config = ConfigDict(extra="forbid")

    state_code: str = Field(..., min_length=2, max_length=2, description="Two-letter postal code")
    state_name: str = Field(..., description="Full state name")
    gc_prompt_pay_days: int = Field(..., ge=1, description="Days for GC to pay subcontractor after payment/billing")
    owner_prompt_pay_days: int = Field(..., ge=1, description="Days for Owner to pay GC after invoice approval")
    penalty_interest_rate_monthly: Decimal = Field(..., ge=0, description="Statutory monthly penalty rate")
    penalty_interest_rate_annual: Decimal | None = Field(default=None, description="Statutory annualized rate")
    statute_citation: str = Field(..., description="Authoritative legal code citation")
    pay_if_paid_treatment: str = Field(..., description="Statutory stance on conditional payment clauses")
    statutory_retainage_limit_pct: Decimal | None = Field(default=None, description="Statutory retainage cap")


# Authoritative versioned jurisdiction reference data (v2026.3)
DEFAULT_STATUTORY_TABLE: dict[str, StatutoryJurisdictionRecord] = {
    "TX": StatutoryJurisdictionRecord(
        state_code="TX",
        state_name="Texas",
        gc_prompt_pay_days=7,
        owner_prompt_pay_days=35,
        penalty_interest_rate_monthly=Decimal("0.015"),
        penalty_interest_rate_annual=Decimal("0.18"),
        statute_citation="Tex. Prop. Code ch. 28 (reference-table v2026.3)",
        pay_if_paid_treatment="Enforceable subject to statutory notice and exception rules (Tex. Bus. & Com. Code § 56.001)",
        statutory_retainage_limit_pct=Decimal("0.10"),
    ),
    "CA": StatutoryJurisdictionRecord(
        state_code="CA",
        state_name="California",
        gc_prompt_pay_days=7,
        owner_prompt_pay_days=30,
        penalty_interest_rate_monthly=Decimal("0.020"),
        penalty_interest_rate_annual=Decimal("0.24"),
        statute_citation="Cal. Civ. Code §§ 8800, 8814 (reference-table v2026.3)",
        pay_if_paid_treatment="Void against public policy (Wm. R. Clarke Corp. v. Safeco Ins. Co.)",
        statutory_retainage_limit_pct=Decimal("0.05"),
    ),
    "NY": StatutoryJurisdictionRecord(
        state_code="NY",
        state_name="New York",
        gc_prompt_pay_days=7,
        owner_prompt_pay_days=30,
        penalty_interest_rate_monthly=Decimal("0.010"),
        penalty_interest_rate_annual=Decimal("0.12"),
        statute_citation="N.Y. Gen. Bus. Law § 756-a et seq. (reference-table v2026.3)",
        pay_if_paid_treatment="Void against public policy (West-Fair Elec. Constr. v. Aetna Cas. & Sur. Co.)",
        statutory_retainage_limit_pct=Decimal("0.05"),
    ),
    "FL": StatutoryJurisdictionRecord(
        state_code="FL",
        state_name="Florida",
        gc_prompt_pay_days=10,
        owner_prompt_pay_days=30,
        penalty_interest_rate_monthly=Decimal("0.015"),
        penalty_interest_rate_annual=Decimal("0.18"),
        statute_citation="Fla. Stat. § 715.12 (reference-table v2026.3)",
        pay_if_paid_treatment="Enforceable if express, unambiguous condition precedent wording used",
        statutory_retainage_limit_pct=Decimal("0.10"),
    ),
    "IL": StatutoryJurisdictionRecord(
        state_code="IL",
        state_name="Illinois",
        gc_prompt_pay_days=15,
        owner_prompt_pay_days=30,
        penalty_interest_rate_monthly=Decimal("0.010"),
        penalty_interest_rate_annual=Decimal("0.12"),
        statute_citation="815 ILCS 603/ (reference-table v2026.3)",
        pay_if_paid_treatment="Enforceable with clear and unambiguous conditional language",
        statutory_retainage_limit_pct=Decimal("0.10"),
    ),
    "PA": StatutoryJurisdictionRecord(
        state_code="PA",
        state_name="Pennsylvania",
        gc_prompt_pay_days=14,
        owner_prompt_pay_days=20,
        penalty_interest_rate_monthly=Decimal("0.010"),
        penalty_interest_rate_annual=Decimal("0.12"),
        statute_citation="73 P.S. § 501 et seq. (CASPA v2026.3)",
        pay_if_paid_treatment="Enforceable if explicit language creates condition precedent",
        statutory_retainage_limit_pct=Decimal("0.10"),
    ),
    "OH": StatutoryJurisdictionRecord(
        state_code="OH",
        state_name="Ohio",
        gc_prompt_pay_days=10,
        owner_prompt_pay_days=30,
        penalty_interest_rate_monthly=Decimal("0.015"),
        penalty_interest_rate_annual=Decimal("0.18"),
        statute_citation="Ohio Rev. Code § 4113.61 (reference-table v2026.3)",
        pay_if_paid_treatment="Enforceable with explicit conditional terms",
        statutory_retainage_limit_pct=Decimal("0.08"),
    ),
    "GA": StatutoryJurisdictionRecord(
        state_code="GA",
        state_name="Georgia",
        gc_prompt_pay_days=10,
        owner_prompt_pay_days=30,
        penalty_interest_rate_monthly=Decimal("0.010"),
        penalty_interest_rate_annual=Decimal("0.12"),
        statute_citation="O.C.G.A. § 13-11-1 et seq. (reference-table v2026.3)",
        pay_if_paid_treatment="Enforceable if contract clearly demonstrates mutual intent",
        statutory_retainage_limit_pct=Decimal("0.10"),
    ),
    "NC": StatutoryJurisdictionRecord(
        state_code="NC",
        state_name="North Carolina",
        gc_prompt_pay_days=7,
        owner_prompt_pay_days=30,
        penalty_interest_rate_monthly=Decimal("0.010"),
        penalty_interest_rate_annual=Decimal("0.12"),
        statute_citation="N.C. Gen. Stat. § 22C-1 et seq. (reference-table v2026.3)",
        pay_if_paid_treatment="Void against public policy (N.C. Gen. Stat. § 22C-2)",
        statutory_retainage_limit_pct=Decimal("0.05"),
    ),
    "WA": StatutoryJurisdictionRecord(
        state_code="WA",
        state_name="Washington",
        gc_prompt_pay_days=10,
        owner_prompt_pay_days=30,
        penalty_interest_rate_monthly=Decimal("0.010"),
        penalty_interest_rate_annual=Decimal("0.12"),
        statute_citation="Wash. Rev. Code § 39.08 et seq. (reference-table v2026.3)",
        pay_if_paid_treatment="Disfavored, construed as timing mechanism unless unequivocally conditional",
        statutory_retainage_limit_pct=Decimal("0.05"),
    ),
    "AZ": StatutoryJurisdictionRecord(
        state_code="AZ",
        state_name="Arizona",
        gc_prompt_pay_days=7,
        owner_prompt_pay_days=30,
        penalty_interest_rate_monthly=Decimal("0.015"),
        penalty_interest_rate_annual=Decimal("0.18"),
        statute_citation="A.R.S. § 32-1129 et seq. (reference-table v2026.3)",
        pay_if_paid_treatment="Enforceable with explicit, clear conditional language",
        statutory_retainage_limit_pct=Decimal("0.10"),
    ),
    "CO": StatutoryJurisdictionRecord(
        state_code="CO",
        state_name="Colorado",
        gc_prompt_pay_days=7,
        owner_prompt_pay_days=30,
        penalty_interest_rate_monthly=Decimal("0.015"),
        penalty_interest_rate_annual=Decimal("0.18"),
        statute_citation="C.R.S. § 24-91-103 (reference-table v2026.3)",
        pay_if_paid_treatment="Enforceable if parties' intent is express and unambiguous",
        statutory_retainage_limit_pct=Decimal("0.05"),
    ),
    "NJ": StatutoryJurisdictionRecord(
        state_code="NJ",
        state_name="New Jersey",
        gc_prompt_pay_days=10,
        owner_prompt_pay_days=30,
        penalty_interest_rate_monthly=Decimal("0.010"),
        penalty_interest_rate_annual=Decimal("0.12"),
        statute_citation="N.J. Stat. Ann. § 2A:30A-1 et seq. (reference-table v2026.3)",
        pay_if_paid_treatment="Enforceable if explicitly stated as condition precedent",
        statutory_retainage_limit_pct=Decimal("0.10"),
    ),
    "MA": StatutoryJurisdictionRecord(
        state_code="MA",
        state_name="Massachusetts",
        gc_prompt_pay_days=7,
        owner_prompt_pay_days=30,
        penalty_interest_rate_monthly=Decimal("0.010"),
        penalty_interest_rate_annual=Decimal("0.12"),
        statute_citation="Mass. Gen. Laws ch. 149 § 29E (reference-table v2026.3)",
        pay_if_paid_treatment="Strictly limited and void on private contracts over $3M under M.G.L. c. 149 § 29E",
        statutory_retainage_limit_pct=Decimal("0.05"),
    ),
}

# State name to code mapping
_STATE_NAME_TO_CODE: dict[str, str] = {
    record.state_name.upper(): record.state_code
    for record in DEFAULT_STATUTORY_TABLE.values()
}


def normalize_jurisdiction_code(jurisdiction_input: str) -> str | None:
    """Normalize input state code or full state name to 2-letter uppercase postal code."""
    cleaned = jurisdiction_input.strip().upper()
    if len(cleaned) == 2 and cleaned in DEFAULT_STATUTORY_TABLE:
        return cleaned
    return _STATE_NAME_TO_CODE.get(cleaned)


def get_jurisdiction_record(
    jurisdiction_input: str,
    table_uri: str | None = None,
) -> StatutoryJurisdictionRecord | None:
    """Retrieve statutory jurisdiction record from reference store or memory catalog."""
    normalized_code = normalize_jurisdiction_code(jurisdiction_input)
    if not normalized_code:
        return None

    # Check if external table URI provided
    uri = table_uri or os.getenv("STATUTORY_TABLE_URI")
    if uri and uri.startswith("file://"):
        file_path = Path(uri[7:])
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                if normalized_code in data:
                    return StatutoryJurisdictionRecord.model_validate(data[normalized_code])
            except (json.JSONDecodeError, OSError, ValueError):
                pass

    return DEFAULT_STATUTORY_TABLE.get(normalized_code)


def calculate_statutory_prompt_pay_clock(
    state_jurisdiction: str,
    invoice_receipt_date: str | date | datetime,
    contract_clause: str,
    reference_now: datetime | None = None,
) -> StatutoryClock:
    """Deterministically compute prompt-pay statutory countdown and penalty rate.

    Enforces Silence-Over-Guessing: Raises StateValidationError if state is unknown or
    if contract_clause is not 'pay-if-paid' or 'pay-when-paid'.
    """
    normalized_clause = contract_clause.strip().lower()
    if normalized_clause not in {"pay-if-paid", "pay-when-paid"}:
        raise StateValidationError(
            message=f"Invalid contract_clause '{contract_clause}'. Must be 'pay-if-paid' or 'pay-when-paid'.",
            incident_context={"contract_clause": contract_clause},
            node_name="FairPayStatutoryGuardian",
        )

    record = get_jurisdiction_record(state_jurisdiction)
    if record is None:
        raise StateValidationError(
            message=f"Unresolvable or unsupported state jurisdiction: '{state_jurisdiction}'. Guessing is prohibited.",
            incident_context={"state_jurisdiction": state_jurisdiction},
            node_name="FairPayStatutoryGuardian",
        )

    # Parse receipt date
    if isinstance(invoice_receipt_date, datetime):
        receipt_dt = invoice_receipt_date if invoice_receipt_date.tzinfo else invoice_receipt_date.replace(tzinfo=UTC)
    elif isinstance(invoice_receipt_date, date):
        receipt_dt = datetime.combine(invoice_receipt_date, datetime.min.time(), tzinfo=UTC)
    elif isinstance(invoice_receipt_date, str):
        try:
            # Try ISO format
            receipt_dt = datetime.fromisoformat(invoice_receipt_date)
            if not receipt_dt.tzinfo:
                receipt_dt = receipt_dt.replace(tzinfo=UTC)
        except ValueError as e:
            try:
                parsed_d = date.fromisoformat(invoice_receipt_date)
                receipt_dt = datetime.combine(parsed_d, datetime.min.time(), tzinfo=UTC)
            except ValueError:
                raise StateValidationError(
                    message=f"Invalid invoice_receipt_date format: '{invoice_receipt_date}'. Must be ISO format.",
                    incident_context={"invoice_receipt_date": invoice_receipt_date},
                    node_name="FairPayStatutoryGuardian",
                ) from e
    else:
        raise StateValidationError(
            message=f"Unsupported invoice_receipt_date type: {type(invoice_receipt_date)}",
            incident_context={"type": str(type(invoice_receipt_date))},
            node_name="FairPayStatutoryGuardian",
        )

    # Deterministic date computation
    deadline = receipt_dt + timedelta(days=record.gc_prompt_pay_days)
    now_dt = reference_now if reference_now is not None else datetime.now(UTC)

    days_remaining = (deadline.date() - now_dt.date()).days

    return StatutoryClock(
        state=record.state_code,
        days_remaining=days_remaining,
        deadline_timestamp=deadline,
        penalty_interest_rate=record.penalty_interest_rate_monthly,
        statute_reference=record.statute_citation,
    )
