"""IRONCLAD Sentinel: Autonomous Retainage & Lien-Discharge Executive Decision Card.

Streamlit presentation layer implementing the Zero-Chat 1-Click Executive Decision Card
conforming strictly to:
- INTERFACE_OBSERVABILITY_SYSTEM.md Sections 1-10
- AGENT_BEHAVIOR_PROFILE.md (Executive Zero-Chat Mandate)
- .agents/rules/ui-non-goals-interface-boundaries.md
"""

# ruff: noqa: E402

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Force repository root into sys.path for Streamlit Cloud execution
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

# Map Streamlit Cloud secrets to os.environ if present
try:
    for key, val in st.secrets.items():
        if isinstance(val, str) and key not in os.environ:
            os.environ[key] = val
except Exception:
    pass

from src.agents.graph import build_ironclad_graph
from src.state.checkpointing import get_checkpoint_manager
from src.state.schema import DrawPacketMeta, IroncladState, RuntimeConfig
from src.ui.generative_ui import (
    inject_custom_styles,
    render_audit_trail_expander,
    render_compliance_row,
    render_decision_actions,
    render_discrepancy_table,
    render_financial_tiles,
    render_header,
    render_notification_toast,
    render_status_banner,
)
from src.ui.hitl_resumption import submit_decision
from src.ui.stream_consumer import StreamConsumer, UIStateAccumulator

st.set_page_config(
    page_title="IRONCLAD — Retainage & Lien Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state() -> None:
    """Initializes Streamlit session state containers."""
    if "consumer" not in st.session_state:
        st.session_state.consumer = StreamConsumer()
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "raw_state_snapshot" not in st.session_state:
        st.session_state.raw_state_snapshot = None
    if "audit_completed" not in st.session_state:
        st.session_state.audit_completed = False
    if "terminal_decision" not in st.session_state:
        st.session_state.terminal_decision = None


def get_preset_packet(preset_name: str, runtime_mode: str) -> tuple[IroncladState, str]:
    """Generates mock / staging input packets based on user scenario selection."""
    if "Complex Defect" in preset_name:
        meta = DrawPacketMeta(
            project_id="PROJ-METRO-02",
            subcontractor_id="SUB-ELECTRICAL-902",
            draw_number=2,
            source_uris=["tests/mocks/fixtures/draw_2_electrical_defect_invoice.pdf"],
        )
        return (
            IroncladState(
                draw_packet_meta=meta,
                runtime_config=RuntimeConfig(runtime_mode=runtime_mode),
            ),
            "Complex Defect Case (Pre-Dated Notary Fraud)",
        )
    elif "Edge Case" in preset_name:
        meta = DrawPacketMeta(
            project_id="PROJ-BAY-03",
            subcontractor_id="SUB-HVAC-303",
            draw_number=3,
            source_uris=["tests/mocks/fixtures/draw_3_plumbing_edge_case.pdf"],
        )
        return (
            IroncladState(
                draw_packet_meta=meta,
                runtime_config=RuntimeConfig(runtime_mode=runtime_mode),
            ),
            "Edge Case (Ambiguous Pay-if-Paid Rider Clause)",
        )
    else:  # Simple Clean Case
        meta = DrawPacketMeta(
            project_id="PROJ-SKYLINE-04",
            subcontractor_id="SUB-CONCRETE-001",
            draw_number=4,
            source_uris=["tests/mocks/fixtures/draw_4_hvac_invoice.pdf"],
        )
        return (
            IroncladState(
                draw_packet_meta=meta,
                runtime_config=RuntimeConfig(runtime_mode=runtime_mode),
            ),
            "Simple Clean Case (Texas Commercial Masonry)",
        )


def main() -> None:
    init_session_state()
    inject_custom_styles()

    # Sidebar: Scenario Selection & Execution Controls
    st.sidebar.markdown("### ⚙️ Audit Controls")
    runtime_mode = os.getenv("IRONCLAD_RUNTIME_MODE", "staging").lower()
    st.sidebar.caption(f"Active Runtime: **{runtime_mode.upper()}**")

    scenario_options = [
        "Simple Clean Case (Texas Masonry - Draw #4)",
        "Complex Defect Case (Pre-Dated Notary - Draw #2)",
        "Edge Case (Ambiguous Pay-if-Paid - Draw #3)",
        "Upload Custom Draw Packet PDF",
    ]
    selected_scenario = st.sidebar.selectbox("Select Draw Packet Scenario:", scenario_options)

    uploaded_file = None
    if "Upload Custom" in selected_scenario:
        uploaded_file = st.sidebar.file_uploader(
            "Upload AIA G702/G703 Draw Application (PDF):", type=["pdf"]
        )

    run_clicked = st.sidebar.button(
        "▶ Run Autonomous Audit",
        type="primary",
        use_container_width=True,
    )

    # Process Run Execution
    if run_clicked:
        st.session_state.terminal_decision = None
        st.session_state.audit_completed = False

        if uploaded_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            meta = DrawPacketMeta(
                project_id="PROJ-UPLOAD-01",
                subcontractor_id="SUB-CUSTOM-01",
                draw_number=1,
                source_uris=[tmp_path],
            )
            initial_state = IroncladState(
                draw_packet_meta=meta,
                runtime_config=RuntimeConfig(runtime_mode=runtime_mode),
            )
            session_id = f"session_custom_{meta.project_id}_{meta.draw_number}"
        else:
            initial_state, _ = get_preset_packet(selected_scenario, runtime_mode)
            session_id = f"session_{initial_state.draw_packet_meta.project_id}_{initial_state.draw_packet_meta.draw_number}"

        st.session_state.current_session_id = session_id

        # Execute Graph
        with st.spinner("Auditing draw packet across parallel sentinel tracks..."):
            graph = build_ironclad_graph()
            checkpoint_mgr = get_checkpoint_manager()

            paused_state = asyncio.run(
                graph.execute(
                    initial_state=initial_state,
                    checkpoint_manager=checkpoint_mgr,
                    session_id=session_id,
                )
            )

            # Ingest paused snapshot into UI consumer
            consumer = StreamConsumer()
            consumer.ingest_state_snapshot(paused_state, checkpoint_id=session_id)
            st.session_state.consumer = consumer
            st.session_state.raw_state_snapshot = paused_state.model_dump_json(indent=2)
            st.session_state.audit_completed = True

    # Main Application Rendering
    consumer: StreamConsumer = st.session_state.consumer
    ui_state: UIStateAccumulator = consumer.state
    card_payload = ui_state.decision_card_payload

    # 1. Executive Header
    proj_name = card_payload.project_name if card_payload else "Commercial Project"
    trade_name = card_payload.subcontractor_trade if card_payload else "Trade Division"
    draw_num = card_payload.draw_number if card_payload else 1
    render_header(proj_name, trade_name, draw_num)

    # 2. Status Banner
    if st.session_state.terminal_decision:
        dec = st.session_state.terminal_decision
        st.success(f"✓ Decision Executed: {dec['action']} by {dec['reviewer']} — Checkpoint Resolved.")
    else:
        is_err = ui_state.error_notice is not None
        render_status_banner(ui_state.status_banner, is_running=ui_state.is_running, is_error=is_err)

    # 3. Financial Summary Metric Tiles
    is_danger_rec = card_payload is not None and card_payload.recommended_action == "ESCALATE_LEGAL"
    render_financial_tiles(
        gross=ui_state.gross_amount_requested,
        retainage=ui_state.contractual_retainage_withheld,
        net=ui_state.net_recommended_release,
        is_danger=is_danger_rec,
    )

    # 4. Compliance Badges Row
    render_compliance_row(
        lien_status=ui_state.lien_chain_status,
        clock=ui_state.statutory_clock,
    )

    # 5. Discrepancies Table
    render_discrepancy_table(ui_state.flagged_discrepancies)

    # 6. Three-Button HITL Decision Action Center
    if not st.session_state.terminal_decision:
        clicked_action, notes = render_decision_actions(
            card_payload=card_payload,
            is_paused=ui_state.is_paused_for_hitl,
            checkpoint_id=ui_state.checkpoint_id or st.session_state.current_session_id,
        )

        if clicked_action and st.session_state.current_session_id:
            with st.spinner(f"Submitting '{clicked_action}' decision..."):
                res_state = asyncio.run(
                    submit_decision(
                        checkpoint_id=st.session_state.current_session_id,
                        action=clicked_action,
                        reviewer_id="executive_cfo",
                        notes=notes,
                    )
                )

                st.session_state.terminal_decision = {
                    "action": clicked_action,
                    "reviewer": "executive_cfo",
                    "notes": notes,
                }
                st.session_state.consumer.ingest_state_snapshot(res_state)
                st.session_state.raw_state_snapshot = res_state.model_dump_json(indent=2)
                st.toast(f"Decision '{clicked_action}' recorded successfully!", icon="✅")
                st.rerun()

    # 7. Collapsible Forensic Audit Trail Panel (Opt-In Expander)
    render_audit_trail_expander(
        node_status_lines=ui_state.node_status_lines,
        node_reasoning_traces=ui_state.node_reasoning_traces,
        calculation_trace=ui_state.calculation_trace,
        raw_snapshot_json=st.session_state.raw_state_snapshot,
    )

    # 8. Notification Toasts
    if ui_state.toast_notifications:
        render_notification_toast(ui_state.toast_notifications)


if __name__ == "__main__":
    main()
