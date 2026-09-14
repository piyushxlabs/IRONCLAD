"""Unit tests for GraphBuilder and Tri-Track DAG scaffolding."""

import pytest

from src.agents.graph import GraphBuilder, build_ironclad_graph
from src.errors import StateValidationError


def test_graph_builder_initialization() -> None:
    """Verify empty GraphBuilder instantiation and node addition."""
    builder = GraphBuilder()
    builder.add_node("node_a")
    builder.add_node("node_b")
    builder.add_edge("node_a", "node_b")
    builder.set_entry_point("node_a")
    builder.set_interrupt("node_b")

    graph = builder.compile()
    assert "node_a" in graph.nodes
    assert "node_b" in graph.nodes
    assert graph.entry_point == "node_a"
    assert "node_b" in graph.interrupt_nodes
    assert graph.get_downstream_nodes("node_a") == ["node_b"]


def test_graph_builder_duplicate_node_error() -> None:
    """Verify adding duplicate node raises StateValidationError."""
    builder = GraphBuilder()
    builder.add_node("duplicate_node")
    with pytest.raises(StateValidationError):
        builder.add_node("duplicate_node")


def test_graph_builder_invalid_edge_error() -> None:
    """Verify edge connecting unregistered node raises StateValidationError on compile."""
    builder = GraphBuilder()
    builder.add_node("valid_node")
    builder.add_edge("valid_node", "non_existent_node")
    with pytest.raises(StateValidationError):
        builder.compile()


def test_authoritative_ironclad_graph_topology() -> None:
    """Verify authoritative Tri-Track DAG structure from Section 4 specification."""
    graph = build_ironclad_graph()

    expected_nodes = {
        "ingress",
        "forensic_audit_sentinel",
        "fair_pay_statutory_guardian",
        "everyday_decision_card_emitter",
        "hitl_interrupt",
        "terminal",
    }
    assert set(graph.nodes.keys()) == expected_nodes
    assert graph.entry_point == "ingress"
    assert "hitl_interrupt" in graph.interrupt_nodes

    # Ingress fans out to both parallel nodes
    downstream_ingress = graph.get_downstream_nodes("ingress")
    assert "forensic_audit_sentinel" in downstream_ingress
    assert "fair_pay_statutory_guardian" in downstream_ingress

    # Both parallel nodes fan in to EverydayDecisionCardEmitter
    assert graph.get_downstream_nodes("forensic_audit_sentinel") == ["everyday_decision_card_emitter"]
    assert graph.get_downstream_nodes("fair_pay_statutory_guardian") == ["everyday_decision_card_emitter"]

    # Synthesis flows to HITL interrupt gate
    assert graph.get_downstream_nodes("everyday_decision_card_emitter") == ["hitl_interrupt"]
    assert graph.get_downstream_nodes("hitl_interrupt") == ["terminal"]
