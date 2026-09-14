"""End-to-End Integration Tests for Streamlit Executive Decision Card Presentation Flow.

Tests:
- Preset scenario generation (Clean Case, Complex Defect Case, Edge Case) across runtimes
- Tri-Track DAG execution driving StreamConsumer & UIStateAccumulator state hydration
- Generative UI state validation (KPI figures, compliance badges, discrepancy table, audit trail)
- HITL decision submission and checkpoint resolution lifecycle
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.agents.graph import build_ironclad_graph
from src.state.checkpointing import MockCheckpointManager
from src.ui.app import get_preset_packet
from src.ui.hitl_resumption import submit_decision
from src.ui.stream_consumer import StreamConsumer


@pytest.mark.asyncio
async def test_streamlit_clean_scenario_full_flow() -> None:
    """Validate full Streamlit UI state lifecycle for Simple Clean Case."""
    state, label = get_preset_packet("Simple Clean Case (Texas Masonry - Draw #4)", runtime_mode="mock")
    assert "Simple Clean Case" in label
    assert state.draw_packet_meta.draw_number == 4

    checkpoint_mgr = MockCheckpointManager()
    session_id = f"session_clean_ui_{state.draw_packet_meta.draw_number}"

    graph = build_ironclad_graph()
    paused_state = await graph.execute(
        initial_state=state,
        checkpoint_manager=checkpoint_mgr,
        session_id=session_id,
    )

    # Ingest state snapshot into StreamConsumer
    consumer = StreamConsumer()
    consumer.ingest_state_snapshot(paused_state, checkpoint_id=session_id)
    ui_state = consumer.state

    # Verify UI state accumulator
    assert ui_state.is_paused_for_hitl is True
    assert ui_state.gross_amount_requested == Decimal("12000.00")
    assert ui_state.contractual_retainage_withheld == Decimal("600.00")
    assert ui_state.net_recommended_release == Decimal("11400.00")
    assert ui_state.decision_card_payload is not None
    assert ui_state.decision_card_payload.recommended_action == "APPROVE_RELEASE"
    assert len(ui_state.flagged_discrepancies) == 0

    # Execute 1-click HITL approval
    resolved_state = await submit_decision(
        checkpoint_id=session_id,
        action="APPROVE_RELEASE",
        reviewer_id="cfo_executive",
        notes="All retainage math and unconditional lien waivers verified.",
        checkpoint_manager=checkpoint_mgr,
    )
    assert resolved_state.approval_state is not None
    assert resolved_state.approval_state.action.value == "APPROVE_RELEASE"


@pytest.mark.asyncio
async def test_streamlit_defect_scenario_full_flow() -> None:
    """Validate full Streamlit UI state lifecycle for Complex Defect Case."""
    state, label = get_preset_packet("Complex Defect Case (Pre-Dated Notary - Draw #2)", runtime_mode="mock")
    assert "Complex Defect" in label
    assert state.draw_packet_meta.draw_number == 2

    checkpoint_mgr = MockCheckpointManager()
    session_id = f"session_defect_ui_{state.draw_packet_meta.draw_number}"

    graph = build_ironclad_graph()
    paused_state = await graph.execute(
        initial_state=state,
        checkpoint_manager=checkpoint_mgr,
        session_id=session_id,
    )

    # Ingest state snapshot into StreamConsumer
    consumer = StreamConsumer()
    consumer.ingest_state_snapshot(paused_state, checkpoint_id=session_id)
    ui_state = consumer.state

    # Verify UI state accumulator prevents ungrounded release
    assert ui_state.is_paused_for_hitl is True
    assert ui_state.decision_card_payload is not None
    assert ui_state.decision_card_payload.recommended_action != "APPROVE_RELEASE"
    assert len(ui_state.flagged_discrepancies) > 0

    # Execute Hold decision
    resolved_state = await submit_decision(
        checkpoint_id=session_id,
        action="HOLD_REQUEST_CORRECTION",
        reviewer_id="cfo_executive",
        notes="Holding release pending corrected lien waiver.",
        checkpoint_manager=checkpoint_mgr,
    )
    assert resolved_state.approval_state is not None
    assert resolved_state.approval_state.action.value == "HOLD_REQUEST_CORRECTION"


@pytest.mark.asyncio
async def test_streamlit_edge_case_scenario_full_flow() -> None:
    """Validate full Streamlit UI state lifecycle for Edge Case."""
    state, label = get_preset_packet("Edge Case (Ambiguous Pay-if-Paid - Draw #3)", runtime_mode="mock")
    assert "Edge Case" in label
    assert state.draw_packet_meta.draw_number == 3

    checkpoint_mgr = MockCheckpointManager()
    session_id = f"session_edge_ui_{state.draw_packet_meta.draw_number}"

    graph = build_ironclad_graph()
    paused_state = await graph.execute(
        initial_state=state,
        checkpoint_manager=checkpoint_mgr,
        session_id=session_id,
    )

    consumer = StreamConsumer()
    consumer.ingest_state_snapshot(paused_state, checkpoint_id=session_id)
    ui_state = consumer.state

    assert ui_state.is_paused_for_hitl is True
    assert ui_state.decision_card_payload is not None
    assert ui_state.decision_card_payload.recommended_action != "APPROVE_RELEASE"

    # Execute Escalate decision
    resolved_state = await submit_decision(
        checkpoint_id=session_id,
        action="ESCALATE_LEGAL",
        reviewer_id="cfo_executive",
        notes="Escalating ambiguous clause to legal counsel.",
        checkpoint_manager=checkpoint_mgr,
    )
    assert resolved_state.approval_state is not None
    assert resolved_state.approval_state.action.value == "ESCALATE_LEGAL"
