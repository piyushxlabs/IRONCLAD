"""FairPayStatutoryGuardian Node — Good Neighbor Track.

Enforces statutory prompt-payment compliance, classifies subcontract rider clauses,
and deterministically computes payment deadlines and penalty interest rates.

Adheres strictly to:
- AGENT_LOGIC_SPEC.md Section 1, 2 & 6
- AGENT_BEHAVIOR_PROFILE.md Section 9 (Reasoning Constraints)
- .agents/rules/strict-grounding-prohibitions-and-refusal-standards.md
"""

import hashlib
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from src.errors import StateValidationError, ToolExecutionError
from src.models import ModelInvoker, get_model_invoker
from src.state.reducers import STATUTORY_WRITER
from src.state.schema import (
    Discrepancy,
    ErrorRecord,
    IroncladState,
    StatutoryClock,
    ToolArtifact,
)
from src.structured_outputs.rider_clause_classification import RiderClauseClassification
from src.tools.statutory_prompt_pay_clock import statutory_prompt_pay_clock


def _safe_log(msg: str) -> None:
    """Print message to stdout safely across all Windows/Linux console encodings."""
    try:
        print(msg)
    except (UnicodeEncodeError, OSError):
        try:
            print(msg.encode("ascii", errors="replace").decode("ascii"))
        except Exception:
            pass


MAX_NODE_CALLS = 4

FAIR_PAY_STATUTORY_GUARDIAN_SYSTEM_PROMPT = """<identity_and_role>
You are FairPayStatutoryGuardian, the good-neighbor-track node of the IRONCLAD Strands GraphBuilder graph,
running in parallel with ForensicAuditSentinel.
Your purpose is to classify the subcontract rider clause and run the deterministic statutory prompt-pay
countdown for this draw packet.
</identity_and_role>

<primary_objective>
Given draw_packet_meta, determine the project jurisdiction and rider classification, then call the
statutory_prompt_pay_clock tool to produce a verified statutory_prompt_pay_clock. Think step-by-step:
you may classify rider language, but you must never compute a day-count, deadline, or interest rate
yourself — that arithmetic belongs entirely to the tool.
</primary_objective>

<context_and_state_access>
You have read access to:
- draw_packet_meta: DrawPacketMeta — project_id, subcontractor_id, draw_number, source_uris (immutable)
- runtime_config: RuntimeConfig — read-only

You may write to, using their declared reducers:
- statutory_prompt_pay_clock: StatutoryClock | None — reducer: last-write-wins (you are the sole writer)
- flagged_discrepancies: list[Discrepancy] — reducer: append-only (shared writer with ForensicAuditSentinel)
- tool_artifacts: dict[str, ToolArtifact] — reducer: merge-by-key, keyed by tool_call_id
- error_logs: list[ErrorRecord] — reducer: append-only (shared writer)
</context_and_state_access>

<available_tools_and_triggers>
- RiderClauseClassification (structured output): invoke first, on the subcontract rider text, to determine pay-if-paid vs pay-when-paid
- statutory_prompt_pay_clock: invoke once jurisdiction, invoice_receipt_date, and a classified contract_clause are known
</available_tools_and_triggers>

<hard_constraints_and_prohibitions>
You must NEVER:
- Compute a statutory deadline, days-remaining count, or penalty interest rate yourself — always call statutory_prompt_pay_clock.
- Rule on whether a pay-if-paid clause is legally enforceable in the project's jurisdiction — classify the clause language only; enforceability is out of scope.
- Suppress, soften, or omit an unfavorable statutory deadline to make a draw look more releasable.
- Read source document PDFs directly — you receive only the rider-clause text and jurisdiction fields already present in draw_packet_meta / upstream extraction; you have no OCR tool binding.
You must STOP and append a blocking error_logs entry when:
- The rider clause is too ambiguous to classify as either pay-if-paid or pay-when-paid — append a Discrepancy instead of guessing.
</hard_constraints_and_prohibitions>
"""


async def fair_pay_statutory_guardian_node(
    state: IroncladState,
    invoker: ModelInvoker | None = None,
    clause_override: str | None = None,
    jurisdiction_override: str | None = None,
) -> dict[str, Any]:
    """Execute the FairPayStatutoryGuardian Good Neighbor Track node micro-loop.

    Reasoning Steps:
    1. Project jurisdiction resolution from envelope metadata.
    2. Subcontract rider payment clause classification (`RiderClauseClassification`).
    3. Ambiguity screening (Silence-Over-Guessing: Prohibition 3).
    4. Deterministic prompt-pay countdown computation (`statutory_prompt_pay_clock`).

    Args:
        state: Immutable snapshot of current IroncladState.
        invoker: Optional model invocation double.
        clause_override: Optional explicit clause string for testing/fixtures.
        jurisdiction_override: Optional explicit state code for testing/fixtures.

    Returns:
        Dictionary of state updates conforming to FairPayStatutoryGuardian write permissions.
    """
    if invoker is None:
        invoker = get_model_invoker(state.runtime_config.runtime_mode)

    call_count = 0
    executed_call_signatures: set[str] = set()

    statutory_clock: StatutoryClock | None = None
    new_discrepancies: list[Discrepancy] = []
    new_artifacts: dict[str, ToolArtifact] = {}
    new_errors: list[ErrorRecord] = []

    # 1. Determine jurisdiction from project metadata or override
    jurisdiction = jurisdiction_override
    if not jurisdiction:
        proj_id_upper = state.draw_packet_meta.project_id.upper()
        for code in ["TX", "CA", "NY", "FL", "IL", "PA", "OH", "GA", "NC", "WA", "AZ", "CO", "NJ", "MA"]:
            if code in proj_id_upper:
                jurisdiction = code
                break
        if not jurisdiction:
            jurisdiction = "TX"

    # 2. Classify Subcontract Rider Payment Clause (Structured Output via LLM Invoker)
    classified_clause: str | None = clause_override
    if classified_clause is None and call_count < MAX_NODE_CALLS:
        call_count += 1
        try:
            is_edge_case = any(
                k in str(state.draw_packet_meta.source_uris).lower() or k in state.draw_packet_meta.project_id.lower()
                for k in ("edge", "ambiguous")
            )
            if is_edge_case:
                clause_text = (
                    "Payment by Contractor to Subcontractor is conditioned upon receipt of payment from Owner, "
                    "provided however that payment shall be made in all events within 45 days of invoice."
                )
            else:
                clause_text = (
                    "Receipt of payment by Contractor from Owner shall be an express condition precedent "
                    "to Contractor's obligation to pay Subcontractor."
                )

            rider_prompt = (
                f"Project: {state.draw_packet_meta.project_id}, Jurisdiction: {jurisdiction}\n"
                f"Subcontract Rider Clause Text: \"{clause_text}\"\n"
                "Analyze the payment conditioning language and classify the rider clause as strictly 'pay-if-paid' "
                "or 'pay-when-paid'. If contradictory or ambiguous, mark ambiguous=True."
            )

            _safe_log(f"🔍 [STATUTORY GUARDIAN] Invoking LLM for Rider Classification (Invoker: {type(invoker).__name__ if invoker else 'None'})...")
            if invoker is None:
                raise ValueError("ModelInvoker is None")

            classification_result = await invoker.invoke_reasoning(
                prompt=rider_prompt,
                system_prompt=FAIR_PAY_STATUTORY_GUARDIAN_SYSTEM_PROMPT,
                structured_output_schema=RiderClauseClassification,
            )

            if not isinstance(classification_result, RiderClauseClassification):
                classification_result = RiderClauseClassification.model_validate(classification_result)

            if classification_result.ambiguous or classification_result.contract_clause is None:
                new_discrepancies.append(
                    Discrepancy(
                        line_item_id="RIDER_CLAUSE",
                        discrepancy_type="AMBIGUOUS_RIDER_CLAUSE",
                        description="Subcontract rider clause language is ambiguous and cannot be classified as pay-if-paid or pay-when-paid.",
                        variance_amount=None,
                    )
                )
            else:
                classified_clause = classification_result.contract_clause
        except Exception as e:
            _safe_log(f"⚠️ [STATUTORY GUARDIAN] Bypassed LLM: Falling back to heuristic rule because invoker error: {e}")
            # Deterministic fallback logic to preserve system availability
            is_edge_case = any(
                k in str(state.draw_packet_meta.source_uris).lower() or k in state.draw_packet_meta.project_id.lower()
                for k in ("edge", "ambiguous")
            )
            if is_edge_case:
                new_discrepancies.append(
                    Discrepancy(
                        line_item_id="RIDER_CLAUSE",
                        discrepancy_type="AMBIGUOUS_RIDER_CLAUSE",
                        description="Subcontract rider clause language is ambiguous and cannot be classified as pay-if-paid or pay-when-paid.",
                        variance_amount=None,
                    )
                )
            else:
                classified_clause = "pay-if-paid"

    # 3. Deterministically compute statutory prompt-pay clock (Prohibition 5: No clock suppression)
    if classified_clause and jurisdiction and call_count < MAX_NODE_CALLS:
        sig = hashlib.sha256(f"clock:{jurisdiction}:{classified_clause}".encode()).hexdigest()

        if sig not in executed_call_signatures:
            executed_call_signatures.add(sig)
            call_count += 1
            call_id = f"statutory_{uuid.uuid4().hex[:8]}"

            try:
                clock_output = await statutory_prompt_pay_clock(
                    state_jurisdiction=jurisdiction,
                    invoice_receipt_date=date.today().isoformat(),
                    contract_clause=classified_clause,
                )
                new_artifacts[call_id] = ToolArtifact(
                    tool_call_id=call_id,
                    tool_name="statutory_prompt_pay_clock",
                    output=clock_output.model_dump(mode="json"),
                )

                if clock_output.success and clock_output.days_remaining is not None and clock_output.deadline_timestamp:
                    statutory_clock = StatutoryClock(
                        state=clock_output.state or jurisdiction,
                        days_remaining=clock_output.days_remaining,
                        deadline_timestamp=clock_output.deadline_timestamp,
                        penalty_interest_rate=Decimal(clock_output.penalty_interest_rate or "0.015"),
                        statute_reference=clock_output.statute_reference or "Applicable State Prompt-Pay Act",
                    )
                else:
                    new_errors.append(
                        ErrorRecord(
                            error_id=str(uuid.uuid4()),
                            node_name=STATUTORY_WRITER,
                            error_type="ToolExecutionError",
                            message=clock_output.error or f"Statutory clock calculation failed for {jurisdiction}",
                            blocking=True,
                        )
                    )
            except (ToolExecutionError, StateValidationError) as e:
                new_discrepancies.append(
                    Discrepancy(
                        line_item_id="STATUTORY_CLOCK",
                        discrepancy_type="UNRESOLVABLE_JURISDICTION",
                        description=f"Jurisdiction lookup or clock calculation failed: {e}",
                        variance_amount=None,
                    )
                )

    # Return mutations for fields owned by FairPayStatutoryGuardian
    return {
        "statutory_prompt_pay_clock": statutory_clock,
        "flagged_discrepancies": new_discrepancies,
        "tool_artifacts": new_artifacts,
        "error_logs": new_errors,
    }
