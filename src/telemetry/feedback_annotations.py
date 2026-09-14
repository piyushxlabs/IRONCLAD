"""Langfuse feedback score and annotation pipeline for HITL decisions."""

from __future__ import annotations

import datetime
import logging
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.state.schema import IroncladState, LienChainStatus

logger = logging.getLogger("ironclad.telemetry.feedback")


class HITLFeedbackAnnotationRecord(BaseModel):
    """Structured record of a Human-in-the-Loop decision annotation."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Session / trace identifier")
    action: str = Field(description="Reviewer action: APPROVE_RELEASE, HOLD_REQUEST_CORRECTION, or ESCALATE_LEGAL")
    reason: str | None = Field(default=None, description="Optional explanation provided by the human reviewer")
    categorical_decision: str = Field(description="Normalized categorical score value (e.g. approve_release)")
    human_override_of_clean_audit: bool = Field(
        default=False,
        description="True if human held/escalated despite a 100% clean audit with zero discrepancies",
    )
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        description="UTC timestamp of annotation recording",
    )
    langfuse_score_recorded: bool = Field(
        default=False,
        description="True if successfully written to Langfuse client/API",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context attributes")


def record_hitl_feedback(
    session_id: str,
    action: str,
    reason: str | None = None,
    state: IroncladState | None = None,
    langfuse_client: Any | None = None,
) -> HITLFeedbackAnnotationRecord:
    """Records a Human-in-the-Loop decision as a structured Langfuse score and categorical annotation.

    Conforms to INTERFACE_OBSERVABILITY_SYSTEM.md Section 7a.
    """
    normalized_action = action.strip().upper()
    categorical_decision = normalized_action.lower()

    # Check if this decision is a human override of a clean audit
    human_override_of_clean = False
    if state is not None and normalized_action in ("HOLD_REQUEST_CORRECTION", "ESCALATE_LEGAL"):
        discrepancy_count = len(state.flagged_discrepancies)
        is_clean_waiver = state.lien_chain_status == LienChainStatus.VALID
        if discrepancy_count == 0 and is_clean_waiver:
            human_override_of_clean = True

    score_recorded = False

    # Initialize Langfuse client lazily if not provided and keys exist in environment
    client = langfuse_client
    if client is None:
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        if public_key and secret_key:
            try:
                from langfuse import Langfuse

                client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
            except Exception as exc:  # noqa: BLE001 - defensive fallback if external client init fails
                logger.warning(f"Failed to initialize Langfuse client: {exc}")
                client = None

    # Emit scores to Langfuse if client is available
    if client is not None:
        try:
            # 1. Primary categorical decision score
            client.create_score(
                name="reviewer_decision",
                value=categorical_decision,
                trace_id=session_id,
                session_id=session_id,
                data_type="CATEGORICAL",
                comment=reason,
                metadata={
                    "raw_action": normalized_action,
                    "clean_audit_override": human_override_of_clean,
                },
            )

            # 2. Boolean override score if applicable
            if human_override_of_clean:
                client.create_score(
                    name="human_override_of_clean_audit",
                    value="true",
                    trace_id=session_id,
                    session_id=session_id,
                    data_type="BOOLEAN",
                    comment=f"Reviewer selected {normalized_action} despite zero discrepancies and valid lien chain",
                )

            # Attempt non-blocking flush if method exists
            if hasattr(client, "flush"):
                client.flush()

            score_recorded = True
        except Exception as exc:  # noqa: BLE001 - defensive fallback if external network/score API fails
            logger.warning(f"Failed to record score in Langfuse: {exc}")
            score_recorded = False

    record = HITLFeedbackAnnotationRecord(
        session_id=session_id,
        action=normalized_action,
        reason=reason,
        categorical_decision=categorical_decision,
        human_override_of_clean_audit=human_override_of_clean,
        langfuse_score_recorded=score_recorded,
        metadata={
            "session_id": session_id,
            "recorded_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        },
    )

    logger.info(
        f"[HITL_FEEDBACK] Session '{session_id}' recorded decision '{normalized_action}' "
        f"(override={human_override_of_clean}, langfuse={score_recorded})"
    )
    return record
