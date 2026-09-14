"""Unified Development Runner for IRONCLAD Sentinel.

Provides single-command launching and status verification for all application layers:
- FastAPI SSE Server: http://localhost:8000
- Streamlit Fallback UI: http://localhost:8501
- Bedrock AgentCore Runtime: http://localhost:8080
- Next.js 16 App Router Dashboard: http://localhost:3000

Usage:
    uv run python run_dev.py server [--port 8000]
    uv run python run_dev.py streamlit [--port 8501]
    uv run python run_dev.py agentcore [--port 8080]
    uv run python run_dev.py status
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


def run_fastapi_server(port: int = 8000, host: str = "0.0.0.0", reload: bool = True) -> None:
    """Starts the non-blocking FastAPI SSE bridge server."""
    print(f"[*] Launching IRONCLAD FastAPI Server Bridge on http://{host}:{port}...")
    import uvicorn

    uvicorn.run("src.server:app", host=host, port=port, reload=reload)


def run_streamlit_app(port: int = 8501) -> None:
    """Starts the Streamlit Executive Decision Card fallback interface."""
    print(f"[*] Launching IRONCLAD Streamlit Console on http://localhost:{port}...")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "src/ui/app.py",
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]
    subprocess.run(cmd, check=False)


def run_agentcore_server(port: int = 8080, host: str = "0.0.0.0") -> None:
    """Starts the Amazon Bedrock AgentCore runtime application."""
    print(f"[*] Launching Amazon Bedrock AgentCore Runtime on http://{host}:{port}...")
    from src.main import serve

    serve(port=port, host=host)


def check_status() -> None:
    """Inspects environment and service readiness."""
    print("=" * 60)
    print("IRONCLAD SENTINEL SYSTEM STATUS CHECK")
    print("=" * 60)
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Active Runtime Mode: {os.getenv('IRONCLAD_RUNTIME_MODE', 'mock')}")

    try:
        from src.server import app as fastapi_app
        print(f"[OK] FastAPI Server Bridge: Ready ({fastapi_app.title})")
    except Exception as exc:
        print(f"[FAIL] FastAPI Server Bridge: {exc}")

    try:
        from src.agents.graph import build_ironclad_graph
        graph = build_ironclad_graph()
        print(f"[OK] Tri-Track Multi-Agent DAG: Compiled ({len(graph.nodes)} nodes)")
    except Exception as exc:
        print(f"[FAIL] Multi-Agent DAG: {exc}")

    try:
        import streamlit
        print(f"[OK] Streamlit Presentation Layer: Ready (v{streamlit.__version__})")
    except Exception as exc:
        print(f"[FAIL] Streamlit: {exc}")

    # Check Next.js frontend directory
    if os.path.isdir("frontend/src"):
        print("[OK] Next.js 16 App Router Frontend: Scaffolding present in frontend/")
    else:
        print("[WARN] Next.js Frontend: frontend/src not found")

    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="IRONCLAD Sentinel Development Runner")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # server
    server_parser = subparsers.add_parser("server", help="Run FastAPI SSE bridge server")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    server_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    server_parser.add_argument("--no-reload", action="store_true", help="Disable auto-reloading")

    # streamlit
    ui_parser = subparsers.add_parser("streamlit", help="Run Streamlit executive interface")
    ui_parser.add_argument("--port", type=int, default=8501, help="Port to listen on (default: 8501)")

    # agentcore
    agentcore_parser = subparsers.add_parser("agentcore", help="Run Bedrock AgentCore runtime")
    agentcore_parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    agentcore_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface (default: 0.0.0.0)")

    # status
    subparsers.add_parser("status", help="Check system readiness and component health")

    args = parser.parse_args()

    if args.command == "server":
        run_fastapi_server(port=args.port, host=args.host, reload=not args.no_reload)
    elif args.command == "streamlit":
        run_streamlit_app(port=args.port)
    elif args.command == "agentcore":
        run_agentcore_server(port=args.port, host=args.host)
    elif args.command == "status":
        check_status()
    else:
        check_status()


if __name__ == "__main__":
    main()
