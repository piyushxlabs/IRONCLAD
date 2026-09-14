"""Tool: extract_draw_packet_metadata.

Adheres strictly to AGENT_LOGIC_SPEC.md Section 3 and Section 4.
Form-aware OCR and key-value extraction of AIA G702/G703 fields and lien waiver records from a source draw-packet PDF.
"""

from strands import tool

from src.errors import StateValidationError, ToolExecutionError
from src.providers import get_runtime
from src.tools.schemas.pydantic_models import (
    ExtractDrawPacketMetadataInput,
    ExtractDrawPacketMetadataOutput,
)


def sanitize_pdf_uri(pdf_uri: str) -> str:
    """Sanitize and validate input document URI per AGENT_LOGIC_SPEC.md Section 8."""
    cleaned = pdf_uri.strip()
    if not cleaned:
        raise StateValidationError(
            message="pdf_uri cannot be empty.",
            incident_context={"pdf_uri": pdf_uri},
            node_name="extract_draw_packet_metadata",
        )
    if ".." in cleaned or "/../" in cleaned or "\\..\\" in cleaned:
        raise StateValidationError(
            message="Path traversal sequence detected in pdf_uri.",
            incident_context={"pdf_uri": pdf_uri},
            node_name="extract_draw_packet_metadata",
        )
    # Valid URI prefixes allowed
    valid_schemes = ("s3://", "file://", "https://", "http://")
    if not any(cleaned.startswith(prefix) for prefix in valid_schemes) and not cleaned.endswith(".pdf"):
        raise StateValidationError(
            message=f"Invalid pdf_uri scheme or extension: '{pdf_uri}'. Must be s3:// or .pdf path.",
            incident_context={"pdf_uri": pdf_uri},
            node_name="extract_draw_packet_metadata",
        )
    return cleaned


@tool
async def extract_draw_packet_metadata(
    pdf_uri: str,
) -> ExtractDrawPacketMetadataOutput:
    """Extract AIA G702/G703 continuation sheet line items and lien waiver records from source PDF."""
    sanitized_uri = sanitize_pdf_uri(pdf_uri)
    # Validate input schema
    ExtractDrawPacketMetadataInput(pdf_uri=sanitized_uri)

    runtime = get_runtime()
    try:
        raw_result = await runtime.call_mcp_tool(
            tool_name="extract_draw_packet_metadata",
            tool_input={"pdf_uri": sanitized_uri},
        )
        return ExtractDrawPacketMetadataOutput.model_validate(raw_result)
    except Exception as e:
        if isinstance(e, StateValidationError):
            raise
        raise ToolExecutionError(
            message=f"OCR extraction failed for '{sanitized_uri}': {e!s}",
            incident_context={"pdf_uri": sanitized_uri, "error": str(e)},
            node_name="extract_draw_packet_metadata",
        ) from e
