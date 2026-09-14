"""Integration Tests for Unified Runners and Entrypoint Manifests.

Validates:
- System status check utility in run_dev.py
- Multi-service entrypoint readiness (FastAPI, Streamlit, Bedrock AgentCore)
- Next.js 16 build output and production bundle assets
"""

from __future__ import annotations

import os

from run_dev import check_status
from src.agents.graph import build_ironclad_graph
from src.server import app as fastapi_app


def test_status_check_runs_without_errors(capsys) -> None:
    """Validate check_status reports all subsystems healthy."""
    check_status()
    captured = capsys.readouterr()
    assert "IRONCLAD SENTINEL SYSTEM STATUS CHECK" in captured.out
    assert "[OK] FastAPI Server Bridge" in captured.out
    assert "[OK] Tri-Track Multi-Agent DAG" in captured.out
    assert "[OK] Streamlit Presentation Layer" in captured.out
    assert "[OK] Next.js 16 App Router Frontend" in captured.out


def test_fastapi_server_app_metadata() -> None:
    """Validate FastAPI app title, version, and routing table."""
    assert fastapi_app.title == "IRONCLAD Sentinel API Bridge"
    routes = [route.path for route in fastapi_app.routes]
    assert "/api/health" in routes
    assert "/api/audit/stream" in routes
    assert "/api/hitl/decide" in routes
    assert "/api/snapshot/{checkpoint_id}" in routes


def test_tri_track_dag_compilation() -> None:
    """Validate multi-agent DAG builds all 6 required nodes."""
    graph = build_ironclad_graph()
    assert len(graph.nodes) == 6
    assert "ingress" in graph.nodes
    assert "forensic_audit_sentinel" in graph.nodes
    assert "fair_pay_statutory_guardian" in graph.nodes
    assert "everyday_decision_card_emitter" in graph.nodes
    assert "hitl_interrupt" in graph.nodes
    assert "terminal" in graph.nodes


def test_nextjs_build_artifacts_exist() -> None:
    """Validate Next.js 16 build output directory and static assets."""
    assert os.path.exists("frontend/.next"), "frontend/.next directory must exist after build"
    assert os.path.exists("frontend/src/app/page.tsx")
    assert os.path.exists("frontend/package.json")
