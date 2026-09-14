"""Unit tests for generative UI rendering components and Streamlit app helpers."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.state.schema import (
    DecisionCardPayload,
    Discrepancy,
    LienChainStatus,
    StatutoryClock,
)
from src.ui.app import get_preset_packet
from src.ui.generative_ui import (
    inject_custom_styles,
    render_compliance_row,
    render_decision_actions,
    render_discrepancy_table,
    render_financial_tiles,
    render_header,
    render_status_banner,
)


def test_get_preset_packet() -> None:
    """Verify preset packet generator returns expected project configurations."""
    clean_packet, clean_desc = get_preset_packet("Simple Clean Case", "mock")
    assert "Simple Clean Case" in clean_desc
    assert clean_packet.draw_packet_meta.draw_number == 4

    defect_packet, defect_desc = get_preset_packet("Complex Defect Case", "mock")
    assert "Complex Defect" in defect_desc
    assert defect_packet.draw_packet_meta.draw_number == 2

    edge_packet, edge_desc = get_preset_packet("Edge Case", "mock")
    assert "Edge Case" in edge_desc
    assert edge_packet.draw_packet_meta.draw_number == 3


@patch("streamlit.markdown")
def test_inject_custom_styles(mock_markdown: MagicMock) -> None:
    """Verify custom CSS injection."""
    inject_custom_styles()
    mock_markdown.assert_called_once()
    assert "<style>" in mock_markdown.call_args[0][0]


@patch("streamlit.markdown")
def test_render_header(mock_markdown: MagicMock) -> None:
    """Verify executive header rendering."""
    render_header("Skyline Tower", "Concrete", 4, "draw-04.pdf")
    mock_markdown.assert_called_once()
    rendered_text = mock_markdown.call_args[0][0]
    assert "Skyline Tower" in rendered_text
    assert "Concrete" in rendered_text
    assert "Draw #4" in rendered_text


@patch("streamlit.info")
@patch("streamlit.success")
@patch("streamlit.error")
def test_render_status_banner(
    mock_error: MagicMock, mock_success: MagicMock, mock_info: MagicMock
) -> None:
    """Verify status banner states for running, error, and completed."""
    render_status_banner("Auditing...", is_running=True)
    mock_info.assert_called_once_with("⏳ Auditing...")

    render_status_banner("Audit complete", is_running=False)
    mock_success.assert_called_once_with("✓ Audit complete")

    render_status_banner("Error detected", is_error=True)
    mock_error.assert_called_once_with("🛑 Error detected")


@patch("streamlit.markdown")
def test_render_financial_tiles(mock_markdown: MagicMock) -> None:
    """Verify 3-tile metric rendering with exact dollar strings."""
    render_financial_tiles(
        gross=Decimal("50000.00"),
        retainage=Decimal("2500.00"),
        net=Decimal("47500.00"),
    )
    mock_markdown.assert_called_once()
    rendered = mock_markdown.call_args[0][0]
    assert "$50,000.00" in rendered
    assert "-$2,500.00" in rendered
    assert "$47,500.00" in rendered


@patch("streamlit.columns")
def test_render_compliance_row(mock_columns: MagicMock) -> None:
    """Verify compliance row rendering for lien status and statutory clock."""
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_columns.return_value = (mock_col1, mock_col2)

    clock = StatutoryClock(
        state="TX",
        days_remaining=14,
        deadline_timestamp="2026-10-01T00:00:00Z",  # type: ignore[arg-type]
        penalty_interest_rate=Decimal("0.015"),
        statute_reference="Tex. Prop. Code § 28.002",
    )

    render_compliance_row(LienChainStatus.VALID, clock)
    mock_columns.assert_called_once_with(2)


@patch("streamlit.markdown")
@patch("streamlit.dataframe")
def test_render_discrepancy_table(mock_dataframe: MagicMock, mock_markdown: MagicMock) -> None:
    """Verify clean audit notice vs discrepancy table."""
    # Test clean audit
    render_discrepancy_table([])
    assert mock_markdown.called

    # Test with defects
    discrepancies = [
        Discrepancy(
            line_item_id="W-001",
            discrepancy_type="PRE_DATED_NOTARY",
            description="Notary date precedes check date",
        )
    ]
    render_discrepancy_table(discrepancies)
    mock_dataframe.assert_called_once()


@patch("streamlit.columns")
@patch("streamlit.text_input")
def test_render_decision_actions(
    mock_text_input: MagicMock, mock_columns: MagicMock
) -> None:
    """Verify 3-button HITL Action Center rendering."""
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_col3 = MagicMock()
    mock_columns.return_value = (mock_col1, mock_col2, mock_col3)
    mock_text_input.return_value = "Verified"

    card_payload = DecisionCardPayload(
        draw_number=1,
        project_name="Metro Center",
        subcontractor_trade="HVAC",
        gross_amount_requested=Decimal("10000.00"),
        contractual_retainage_withheld=Decimal("500.00"),
        net_recommended_release=Decimal("9500.00"),
        lien_chain_status=LienChainStatus.VALID,
        recommended_action="APPROVE_RELEASE",
    )

    _action, notes = render_decision_actions(card_payload, is_paused=True, checkpoint_id="chk-01")
    assert notes == "Verified"
    assert mock_columns.called
