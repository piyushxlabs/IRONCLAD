"""Generative UI and Rich Presentation Components for IRONCLAD Sentinel.

Implements all specialized UI components conforming strictly to:
- INTERFACE_OBSERVABILITY_SYSTEM.md Section 1, 2, 3, 4, 4a, 5, 8, 9, 10
- AGENT_BEHAVIOR_PROFILE.md (Executive Zero-Chat Mandate)
"""

from __future__ import annotations

from decimal import Decimal

import streamlit as st

from src.state.schema import (
    DecisionCardPayload,
    Discrepancy,
    LienChainStatus,
    StatutoryClock,
)
from src.ui.stream_consumer import ReasoningTraceEntry, ToolCallStatusLine


def inject_custom_styles() -> None:
    """Injects institutional-grade styling, custom card tiles, and badge formatting."""
    st.markdown(
        """
        <style>
        /* Main background & container aesthetics */
        .stApp {
            background-color: #0b0f19;
            color: #f1f5f9;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        /* Executive Header */
        .executive-header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }
        .executive-title {
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: #f8fafc;
            margin: 0 0 6px 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .executive-subtitle {
            font-size: 13px;
            color: #94a3b8;
            margin: 0;
        }

        /* Financial Metric Tiles */
        .metric-tile-container {
            display: grid;
            grid-template-columns: 1fr 1fr 1.2fr;
            gap: 16px;
            margin-bottom: 20px;
        }
        .metric-tile {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 16px 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }
        .metric-tile:hover {
            border-color: #475569;
        }
        .metric-tile.highlight {
            background: linear-gradient(135deg, #1e293b 0%, #064e3b 100%);
            border: 1px solid #10b981;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.15);
        }
        .metric-tile.danger {
            background: linear-gradient(135deg, #1e293b 0%, #450a0a 100%);
            border: 1px solid #ef4444;
            box-shadow: 0 0 20px rgba(239, 68, 68, 0.15);
        }
        .metric-label {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: #94a3b8;
            margin-bottom: 6px;
        }
        .metric-value {
            font-size: 26px;
            font-weight: 700;
            color: #f8fafc;
            font-family: 'JetBrains Mono', 'Roboto Mono', monospace;
            margin: 0;
        }
        .metric-value.highlight-text {
            color: #34d399;
        }
        .metric-value.danger-text {
            color: #f87171;
        }
        .metric-subtext {
            font-size: 11px;
            color: #64748b;
            margin-top: 4px;
        }

        /* Compliance Badges */
        .compliance-card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 16px 20px;
            height: 100%;
        }
        .badge-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }
        .badge-valid {
            background-color: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4);
        }
        .badge-defect {
            background-color: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.4);
        }
        .badge-warning {
            background-color: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.4);
        }

        /* Discrepancy clean notice */
        .clean-audit-box {
            background-color: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 8px;
            padding: 14px 18px;
            color: #34d399;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 12px 0;
        }

        /* Action Center Container */
        .action-center {
            background-color: #0f172a;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 20px 24px;
            margin-top: 24px;
            margin-bottom: 24px;
        }
        .action-title {
            font-size: 15px;
            font-weight: 600;
            color: #f8fafc;
            margin-bottom: 12px;
        }

        /* Buttons styling */
        div.stButton > button:first-child {
            font-weight: 600;
            font-size: 14px;
            border-radius: 8px;
            padding: 10px 20px;
            transition: all 0.15s ease;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(project_name: str, trade: str, draw_number: int, source_doc: str = "") -> None:
    """Renders the top executive project header banner."""
    doc_meta = f" · Source: <code>{source_doc}</code>" if source_doc else ""
    st.markdown(
        f"""
        <div class="executive-header">
            <div class="executive-title">
                🛡️ IRONCLAD Sentinel
            </div>
            <div class="executive-subtitle">
                Draw #{draw_number} Application · <strong>{project_name}</strong> · Trade: <strong>{trade}</strong>{doc_meta}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_banner(status_text: str, is_running: bool = False, is_error: bool = False) -> None:
    """Renders the top dynamic status banner."""
    if is_error:
        st.error(f"🛑 {status_text}")
    elif is_running:
        st.info(f"⏳ {status_text}")
    else:
        st.success(f"✓ {status_text}")


def render_financial_tiles(
    gross: Decimal | None,
    retainage: Decimal | None,
    net: Decimal | None,
    is_danger: bool = False,
) -> None:
    """Renders the 3 high-prominence primary card financial metric tiles."""
    gross_str = f"${gross:,.2f}" if gross is not None else "—"
    retainage_str = f"-${retainage:,.2f}" if retainage is not None else "—"
    net_str = f"${net:,.2f}" if net is not None else "—"

    highlight_class = "danger" if is_danger else "highlight"
    net_text_class = "danger-text" if is_danger else "highlight-text"

    st.markdown(
        f"""
        <div class="metric-tile-container">
            <div class="metric-tile">
                <div class="metric-label">Gross Amount Requested</div>
                <div class="metric-value">{gross_str}</div>
                <div class="metric-subtext">Work completed + stored materials</div>
            </div>
            <div class="metric-tile">
                <div class="metric-label">Contractual Retainage</div>
                <div class="metric-value">{retainage_str}</div>
                <div class="metric-subtext">Audited statutory/contract deduction</div>
            </div>
            <div class="metric-tile {highlight_class}">
                <div class="metric-label">Net Recommended Release</div>
                <div class="metric-value {net_text_class}">{net_str}</div>
                <div class="metric-subtext">Zero-LLM deterministic math verified</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_compliance_row(
    lien_status: LienChainStatus | None,
    clock: StatutoryClock | None,
) -> None:
    """Renders the Lien Chain status badge and Prompt-Pay Countdown side-by-side."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """<div class="metric-label" style="margin-bottom: 6px;">Lien Waiver Chain-of-Custody</div>""",
            unsafe_allow_html=True,
        )
        if lien_status == LienChainStatus.VALID:
            st.markdown(
                """<div class="badge-pill badge-valid">✓ VALID — Chain-of-Custody Verified</div>""",
                unsafe_allow_html=True,
            )
            st.caption("All notarized waivers chronologically verified against draw dates.")
        elif lien_status == LienChainStatus.SUSPECT_PRE_DATED_NOTARY:
            st.markdown(
                """<div class="badge-pill badge-defect">✗ SUSPECT PRE-DATED NOTARY FRAUD</div>""",
                unsafe_allow_html=True,
            )
            st.caption("Notary seal date strictly precedes check issuance date.")
        elif lien_status == LienChainStatus.MISSING_WAIVER:
            st.markdown(
                """<div class="badge-pill badge-warning">⚠ MISSING LIEN WAIVER</div>""",
                unsafe_allow_html=True,
            )
            st.caption("Continuation line item lacks matching notarized waiver record.")
        elif lien_status == LienChainStatus.INVALID_FORM:
            st.markdown(
                """<div class="badge-pill badge-defect">✗ INVALID STATUTORY WAIVER FORM</div>""",
                unsafe_allow_html=True,
            )
            st.caption("Waiver document failed statutory verification.")
        else:
            st.markdown(
                """<div class="badge-pill badge-warning">Pending Sentinel Verification...</div>""",
                unsafe_allow_html=True,
            )

    with col2:
        st.markdown(
            """<div class="metric-label" style="margin-bottom: 6px;">Statutory Prompt-Pay Window</div>""",
            unsafe_allow_html=True,
        )
        if clock is not None:
            days = clock.days_remaining
            days_color = "#34d399" if days > 5 else ("#fbbf24" if days > 2 else "#f87171")
            pct = clock.penalty_interest_rate * 100
            st.markdown(
                f"""
                <div style="font-size: 18px; font-weight: 700; color: {days_color}; font-family: monospace;">
                    ⏳ {days} Days Remaining
                </div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">
                    Jurisdiction: <strong>{clock.state}</strong> · Penalty Rate: <strong>{pct:.1f}%/mo</strong>
                </div>
                <div style="font-size: 10px; color: #64748b;">
                    Citation: {clock.statute_reference}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption("Statutory clock pending rider classification...")


def render_discrepancy_table(discrepancies: list[Discrepancy]) -> None:
    """Renders the Compliance Discrepancy table or verified clean box."""
    st.markdown(
        """<div class="metric-label" style="margin-top: 16px; margin-bottom: 8px;">Compliance Audit Variances</div>""",
        unsafe_allow_html=True,
    )
    if not discrepancies:
        st.markdown(
            """
            <div class="clean-audit-box">
                <span>🛡️</span>
                <span><strong>Clean Audit:</strong> 0 compliance defects or math discrepancies identified. Full release approved under contractual guidelines.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        table_data = []
        for d in discrepancies:
            var_str = f"${d.variance_amount:,.2f}" if d.variance_amount is not None else "—"
            table_data.append(
                {
                    "Item / Waiver ID": d.line_item_id,
                    "Discrepancy Category": d.discrepancy_type,
                    "Factual Citation & Description": d.description,
                    "Disputed Variance": var_str,
                }
            )
        st.dataframe(table_data, use_container_width=True, hide_index=True)


def render_decision_actions(
    card_payload: DecisionCardPayload | None,
    is_paused: bool,
    checkpoint_id: str | None,
) -> tuple[str | None, str]:
    """Renders the Three-Button HITL Action Center and reviewer notes input.

    Returns:
        tuple (action_clicked: str | None, notes: str)
    """
    st.markdown(
        """
        <div class="action-center">
            <div class="action-title">Executive Authorization & Fund Release Sign-Off</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    notes = st.text_input(
        "Audit Sign-Off Notes / Instructions (Optional):",
        placeholder="Enter reviewer authorization notes or explanation for hold/escalation...",
        key="hitl_reviewer_notes",
        disabled=not is_paused,
    )

    col1, col2, col3 = st.columns(3)
    clicked_action: str | None = None

    rec_action = card_payload.recommended_action if card_payload else "HOLD_REQUEST_CORRECTION"
    approve_help = (
        "Authorize fund release (Clean audit verified)"
        if rec_action == "APPROVE_RELEASE"
        else "Override warning: Audit contains discrepancies or defect findings"
    )

    with col1:
        if st.button(
            "✓ APPROVE RELEASE",
            type="primary",
            use_container_width=True,
            disabled=not is_paused,
            help=approve_help,
        ):
            clicked_action = "APPROVE_RELEASE"

    with col2:
        if st.button(
            "⚠ HOLD — REQUEST CORRECTION",
            use_container_width=True,
            disabled=not is_paused,
            help="Hold payment pending corrected lien waiver or updated billing sheet",
        ):
            clicked_action = "HOLD_REQUEST_CORRECTION"

    with col3:
        if st.button(
            "⚖ ESCALATE TO LEGAL",
            use_container_width=True,
            disabled=not is_paused,
            help="Escalate packet to legal counsel for suspected fraud or unresolvable statutory defect",
        ):
            clicked_action = "ESCALATE_LEGAL"

    return clicked_action, notes


def render_audit_trail_expander(
    node_status_lines: dict[str, list[ToolCallStatusLine]],
    node_reasoning_traces: dict[str, list[ReasoningTraceEntry]],
    calculation_trace: list[str],
    raw_snapshot_json: str | None = None,
) -> None:
    """Renders the opted-in single collapsed Forensic Audit Trail panel."""
    with st.expander("🔍 Forensic Audit Trail & Multi-Agent Traces", expanded=False):
        st.markdown(
            "<p style='font-size: 12px; color: #94a3b8; margin-bottom: 12px;'>"
            "Complete chronological execution trace across Forensic, Statutory, and Everyday sentinel tracks."
            "</p>",
            unsafe_allow_html=True,
        )

        tab1, tab2, tab3 = st.tabs(
            [
                "🔬 ForensicAuditSentinel",
                "⚖ FairPayStatutoryGuardian",
                "📋 EverydayDecisionCardEmitter",
            ]
        )

        # Tab 1: ForensicAuditSentinel
        with tab1:
            st.markdown("#### Professional Track Execution")
            lines = node_status_lines.get("ForensicAuditSentinel", [])
            for line in lines:
                icon = "✓" if line.status == "completed" else ("✗" if line.status == "failed" else "⏳")
                st.write(f"**{icon} `{line.tool_name}`** — *Status: {line.status}*")
                if line.result:
                    with st.expander(f"View `{line.tool_name}` Result", expanded=False):
                        st.json(line.result)

            if calculation_trace:
                st.markdown("##### Retainage Arithmetic Trace (Zero-LLM Math):")
                for step in calculation_trace:
                    st.markdown(f"- `{step}`")

            # Collapsible native thinking sub-expander
            traces = [t for t in node_reasoning_traces.get("ForensicAuditSentinel", []) if t.source == "native-thinking"]
            if traces:
                with st.expander("💭 Native Model Reasoning", expanded=False):
                    for t in traces:
                        st.markdown(f"*{t.content}*")

        # Tab 2: FairPayStatutoryGuardian
        with tab2:
            st.markdown("#### Good Neighbor Track Execution")
            lines = node_status_lines.get("FairPayStatutoryGuardian", [])
            for line in lines:
                icon = "✓" if line.status == "completed" else ("✗" if line.status == "failed" else "⏳")
                st.write(f"**{icon} `{line.tool_name}`** — *Status: {line.status}*")
                if line.result:
                    with st.expander(f"View `{line.tool_name}` Result", expanded=False):
                        st.json(line.result)

            stat_traces = node_reasoning_traces.get("FairPayStatutoryGuardian", [])
            if stat_traces:
                for t in stat_traces:
                    st.caption(f"[{t.source}] {t.content}")

        # Tab 3: EverydayDecisionCardEmitter
        with tab3:
            st.markdown("#### Everyday Track Synthesis")
            lines = node_status_lines.get("EverydayDecisionCardEmitter", [])
            for line in lines:
                icon = "✓" if line.status == "completed" else ("✗" if line.status == "failed" else "⏳")
                st.write(f"**{icon} `{line.tool_name}`** — *Status: {line.status}*")

        st.markdown("---")
        st.markdown(
            "<p style='font-size: 11px; color: #64748b;'>"
            "Some raw extracted text is summarized here; see the structured fields above for exact values."
            "</p>",
            unsafe_allow_html=True,
        )

        if raw_snapshot_json:
            st.download_button(
                label="📥 Download Full Audit Trail (JSON)",
                data=raw_snapshot_json,
                file_name="ironclad_audit_snapshot.json",
                mime="application/json",
            )


def render_notification_toast(notifications: list[str]) -> None:
    """Emits toast notifications for dispatched alerts."""
    for note in notifications:
        st.toast(note, icon="🔔")
