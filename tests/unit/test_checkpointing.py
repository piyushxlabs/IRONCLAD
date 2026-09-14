"""Unit Tests for IRONCLAD Session Checkpointing Backends.

Tests Mock, SQLite, and AgentCore checkpointing managers, verifying exact Decimal
preservation, Pydantic V2 state serialization roundtrips, resumption invariants,
and reducer boundaries.
"""

import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.errors import StateValidationError, ToolExecutionError
from src.state.checkpointing import (
    AgentCoreMemorySessionManager,
    MockCheckpointManager,
    SQLiteCheckpointManager,
    get_checkpoint_manager,
)
from src.state.schema import (
    ApprovalDecision,
    ApprovalStatus,
    DecisionCardPayload,
    Discrepancy,
    DrawPacketMeta,
    IroncladState,
    LienChainStatus,
    LineItem,
    RetainageAuditResult,
    RuntimeConfig,
    StatutoryClock,
)


@pytest.fixture
def sample_state() -> IroncladState:
    """Fixture providing a complete, populated IroncladState."""
    meta = DrawPacketMeta(
        project_id="PRJ-101",
        subcontractor_id="SUB-9988",
        draw_number=4,
        source_uris=["s3://ironclad-draws/PRJ-101/draw4.pdf"],
    )
    line_item = LineItem(
        line_item_id="LI-001",
        description="Poured concrete slab",
        contract_retainage_pct=Decimal("0.05"),
        current_billed=Decimal("50000.00"),
        stored_materials=Decimal("5000.00"),
        prior_payments=Decimal("100000.00"),
    )
    audit_res = RetainageAuditResult(
        gross_amount_requested=Decimal("55000.00"),
        contractual_retainage_withheld=Decimal("2750.00"),
        net_recommended_release=Decimal("52250.00"),
        calculation_trace=[
            "gross = 50000.00 + 5000.00 = 55000.00",
            "retainage = 55000.00 * 0.05 = 2750.00",
            "net = 55000.00 - 2750.00 = 52250.00",
        ],
    )
    clock = StatutoryClock(
        state="TX",
        days_remaining=21,
        deadline_timestamp=datetime(2026, 10, 4, 0, 0, 0, tzinfo=UTC),
        penalty_interest_rate=Decimal("0.015"),
        statute_reference="Tex. Prop. Code ch. 28",
    )
    discrepancy = Discrepancy(
        line_item_id="LI-001",
        discrepancy_type="PRE_DATED_NOTARY",
        description="per verify_lien_chain_integrity finding waiver_id=W-004: PRE_DATED_NOTARY",
        variance_amount=Decimal("1250.00"),
    )
    card = DecisionCardPayload(
        draw_number=4,
        project_name="Commercial Tower",
        subcontractor_trade="Structural Concrete",
        gross_amount_requested=Decimal("55000.00"),
        contractual_retainage_withheld=Decimal("2750.00"),
        net_recommended_release=Decimal("52250.00"),
        lien_chain_status=LienChainStatus.VALID,
        statutory_prompt_pay_clock=clock,
        recommended_action="HOLD_REQUEST_CORRECTED_WAIVER",
        blocking_discrepancies=[discrepancy],
        confidence_score=0.99,
    )
    return IroncladState(
        draw_packet_meta=meta,
        runtime_config=RuntimeConfig(runtime_mode="mock"),
        extracted_line_items=[line_item],
        retainage_audit_result=audit_res,
        lien_chain_status=LienChainStatus.VALID,
        statutory_prompt_pay_clock=clock,
        flagged_discrepancies=[discrepancy],
        decision_card_payload=card,
    )


@pytest.mark.asyncio
async def test_mock_checkpoint_roundtrip(sample_state: IroncladState) -> None:
    """Verify MockCheckpointManager write, read, get, and decimal precision preservation."""
    mgr = MockCheckpointManager()
    session_id = "session_mock_1"

    checkpoint_id = await mgr.write_checkpoint(
        session_id=session_id,
        state=sample_state,
        metadata={"phase": "pre_hitl"},
    )
    assert checkpoint_id.startswith("cp_mock_")

    # Read latest
    read_state = await mgr.read_checkpoint(session_id)
    assert read_state is not None
    assert read_state.draw_packet_meta.project_id == "PRJ-101"
    assert len(read_state.extracted_line_items) == 1
    assert isinstance(read_state.extracted_line_items[0].current_billed, Decimal)
    assert read_state.extracted_line_items[0].current_billed == Decimal("50000.00")
    assert read_state.retainage_audit_result is not None
    assert read_state.retainage_audit_result.net_recommended_release == Decimal("52250.00")

    # Get by checkpoint ID
    by_id = await mgr.get_checkpoint(checkpoint_id)
    assert by_id is not None
    assert by_id.draw_packet_meta.draw_number == 4

    # List checkpoints
    history = await mgr.list_checkpoints(session_id)
    assert len(history) == 1
    assert history[0]["checkpoint_id"] == checkpoint_id
    assert history[0]["metadata"]["phase"] == "pre_hitl"


@pytest.mark.asyncio
async def test_mock_checkpoint_resumption(sample_state: IroncladState) -> None:
    """Verify HITL resumption transitions approval_state correctly."""
    mgr = MockCheckpointManager()
    session_id = "session_mock_resume"

    checkpoint_id = await mgr.write_checkpoint(session_id=session_id, state=sample_state)
    decision = ApprovalDecision(
        action=ApprovalStatus.APPROVE_RELEASE,
        reviewer_id="lead_auditor_01",
        notes="All lien waivers verified and retainage cleared.",
    )

    resumed_state = await mgr.resume_from_checkpoint(
        checkpoint_id=checkpoint_id,
        resumption_payload=decision,
    )
    assert resumed_state.approval_state is not None
    assert resumed_state.approval_state.action == ApprovalStatus.APPROVE_RELEASE
    assert resumed_state.approval_state.reviewer_id == "lead_auditor_01"


@pytest.mark.asyncio
async def test_mock_checkpoint_resumption_immutability_rejection(
    sample_state: IroncladState,
) -> None:
    """Assert resumption with modified financial inputs is rejected."""
    mgr = MockCheckpointManager()
    checkpoint_id = await mgr.write_checkpoint("session_mock_immut", sample_state)

    payload = {
        "action": "APPROVE_RELEASE",
        "reviewer_id": "auditor_1",
        "modified_inputs": {"gross_amount": 99999.00},
    }
    with pytest.raises(StateValidationError) as exc:
        await mgr.resume_from_checkpoint(checkpoint_id, payload)
    assert "Financial immutability violation" in str(exc.value)


@pytest.mark.asyncio
async def test_mock_checkpoint_missing_checkpoint_error(sample_state: IroncladState) -> None:
    """Assert resume on non-existent checkpoint raises ToolExecutionError."""
    mgr = MockCheckpointManager()
    decision = ApprovalDecision(
        action=ApprovalStatus.APPROVE_RELEASE,
        reviewer_id="auditor_1",
    )
    with pytest.raises(ToolExecutionError) as exc:
        await mgr.resume_from_checkpoint("non_existent_cp", decision)
    assert "not found" in str(exc.value)


@pytest.mark.asyncio
async def test_sqlite_checkpoint_roundtrip(
    tmp_path: Path, sample_state: IroncladState
) -> None:
    """Verify SQLiteCheckpointManager write, read, get, list, and persistence across instances."""
    db_file = str(tmp_path / "test_checkpoints.db")
    mgr = SQLiteCheckpointManager(db_path=db_file)
    session_id = "session_sqlite_1"

    # Write first checkpoint
    cp1 = await mgr.write_checkpoint(
        session_id=session_id, state=sample_state, metadata={"step": 1}
    )
    assert cp1.startswith("cp_sqlite_")

    # Write second checkpoint
    sample_state2 = sample_state.model_copy(deep=True)
    sample_state2.runtime_config.max_node_calls = 3
    cp2 = await mgr.write_checkpoint(
        session_id=session_id, state=sample_state2, metadata={"step": 2}
    )

    # Read latest checkpoint (should be cp2)
    latest = await mgr.read_checkpoint(session_id)
    assert latest is not None
    assert latest.draw_packet_meta.project_id == "PRJ-101"

    # Get specific checkpoint by id
    first_cp = await mgr.get_checkpoint(cp1)
    assert first_cp is not None
    assert first_cp.retainage_audit_result is not None
    assert first_cp.retainage_audit_result.contractual_retainage_withheld == Decimal("2750.00")

    # List all checkpoints
    checkpoints = await mgr.list_checkpoints(session_id)
    assert len(checkpoints) == 2
    assert checkpoints[0]["checkpoint_id"] == cp1
    assert checkpoints[1]["checkpoint_id"] == cp2

    # Verify a newly instantiated manager on the same DB file reads the exact state
    mgr_reopened = SQLiteCheckpointManager(db_path=db_file)
    reopened_latest = await mgr_reopened.read_checkpoint(session_id)
    assert reopened_latest is not None
    assert reopened_latest.statutory_prompt_pay_clock is not None
    assert reopened_latest.statutory_prompt_pay_clock.penalty_interest_rate == Decimal("0.015")


@pytest.mark.asyncio
async def test_sqlite_checkpoint_resumption(
    tmp_path: Path, sample_state: IroncladState
) -> None:
    """Verify SQLite resumption transitions state and writes resumed checkpoint."""
    db_file = str(tmp_path / "resume_test.db")
    mgr = SQLiteCheckpointManager(db_path=db_file)
    session_id = "session_resume_sqlite"

    checkpoint_id = await mgr.write_checkpoint(session_id=session_id, state=sample_state)
    decision = ApprovalDecision(
        action=ApprovalStatus.HOLD_REQUEST_CORRECTION,
        reviewer_id="chief_risk_officer",
        notes="Waiver notary pre-dates payment date.",
    )

    resumed_state = await mgr.resume_from_checkpoint(checkpoint_id, decision)
    assert resumed_state.approval_state is not None
    assert resumed_state.approval_state.action == ApprovalStatus.HOLD_REQUEST_CORRECTION

    # Verify resumed checkpoint was written
    target_session = f"session_{sample_state.draw_packet_meta.project_id}_{sample_state.draw_packet_meta.draw_number}"
    latest = await mgr.read_checkpoint(target_session)
    assert latest is not None
    assert latest.approval_state is not None
    assert latest.approval_state.reviewer_id == "chief_risk_officer"


@pytest.mark.asyncio
async def test_agentcore_memory_fallback(tmp_path: Path, sample_state: IroncladState) -> None:
    """Verify AgentCoreMemorySessionManager handles offline / unauthenticated AWS environment gracefully."""
    db_file = str(tmp_path / "agentcore_test.db")
    mgr = AgentCoreMemorySessionManager(db_path=db_file)
    session_id = "session_agentcore_1"

    checkpoint_id = await mgr.write_checkpoint(session_id, sample_state)
    assert checkpoint_id is not None

    read_state = await mgr.read_checkpoint(session_id)
    assert read_state is not None
    assert read_state.draw_packet_meta.project_id == "PRJ-101"


def test_get_checkpoint_manager_factory(tmp_path: Path) -> None:
    """Verify get_checkpoint_manager selects backend correctly based on mode / env."""
    db_file = str(tmp_path / "factory.db")

    mock_mgr = get_checkpoint_manager(mode="mock")
    assert isinstance(mock_mgr, MockCheckpointManager)

    staging_mgr = get_checkpoint_manager(mode="staging", db_path=db_file)
    assert isinstance(staging_mgr, SQLiteCheckpointManager)

    bedrock_mgr = get_checkpoint_manager(mode="bedrock", db_path=db_file)
    assert isinstance(bedrock_mgr, AgentCoreMemorySessionManager)

    # Environment variable resolution
    os.environ["IRONCLAD_RUNTIME_MODE"] = "staging"
    env_mgr = get_checkpoint_manager(db_path=db_file)
    assert isinstance(env_mgr, SQLiteCheckpointManager)
