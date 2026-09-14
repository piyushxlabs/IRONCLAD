"""Strands GraphBuilder Multi-Agent Orchestration DAG Topology.

Defines the authoritative Tri-Track Directed Acyclic Graph (DAG) coordinating:
1. Ingress validation (deterministic, non-LLM)
2. Fan-Out: ForensicAuditSentinel || FairPayStatutoryGuardian (concurrent execution)
3. Fan-In: EverydayDecisionCardEmitter (synthesis)
4. Single HITL Interrupt Gate (durable session checkpoint & human sign-off boundary)
5. Terminal Completion Node (resumption & resolution)

Adheres strictly to:
- AGENT_ORCHESTRATION_BLUEPRINT.md Section 4 & 5
- AGENT_LOGIC_SPEC.md Section 1, 2 & 6
- .agents/rules/graph-topology-loop-caps-and-circuit-breakers.md
- .agents/rules/code-level-verification-over-model-discretion.md
"""

import asyncio
import uuid
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from src.agents.everyday_decision_card_emitter import (
    everyday_decision_card_emitter_node,
)
from src.agents.fair_pay_statutory_guardian import fair_pay_statutory_guardian_node
from src.agents.forensic_audit_sentinel import forensic_audit_sentinel_node
from src.errors import StateValidationError
from src.models import ModelInvoker, get_model_invoker
from src.state.checkpointing import BaseCheckpointManager
from src.state.reducers import (
    EVERYDAY_WRITER,
    FORENSIC_WRITER,
    HITL_WRITER,
    INGRESS_WRITER,
    STATUTORY_WRITER,
    apply_state_update,
)
from src.state.schema import (
    ApprovalDecision,
    ErrorRecord,
    IroncladState,
)
from src.telemetry import (
    record_hitl_feedback,
    trace_agent_invocation,
    trace_audit_run,
)


class NodeDefinition(BaseModel):
    """Definition of an executable node within the orchestration DAG."""

    name: str
    handler: Any = None
    is_interrupt_point: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class EdgeDefinition(BaseModel):
    """Definition of a directed transition between nodes."""

    source: str
    target: str
    condition: str | None = None


async def ingress_node(state: IroncladState) -> dict[str, Any]:
    """Deterministic, non-LLM entry node for draw packet envelope verification.

    Validates packet IDs and ensures document URIs do not contain path traversal.
    """
    errors: list[ErrorRecord] = []
    meta = state.draw_packet_meta

    if not meta.project_id or not meta.project_id.strip():
        errors.append(
            ErrorRecord(
                error_id=str(uuid.uuid4()),
                node_name=INGRESS_WRITER,
                error_type="StateValidationError",
                message="Envelope project_id is empty or missing.",
                blocking=True,
            )
        )

    if not meta.subcontractor_id or not meta.subcontractor_id.strip():
        errors.append(
            ErrorRecord(
                error_id=str(uuid.uuid4()),
                node_name=INGRESS_WRITER,
                error_type="StateValidationError",
                message="Envelope subcontractor_id is empty or missing.",
                blocking=True,
            )
        )

    if meta.draw_number < 1:
        errors.append(
            ErrorRecord(
                error_id=str(uuid.uuid4()),
                node_name=INGRESS_WRITER,
                error_type="StateValidationError",
                message=f"Invalid draw_number: {meta.draw_number}. Must be >= 1.",
                blocking=True,
            )
        )

    for uri in meta.source_uris:
        if ".." in uri or not uri.strip():
            errors.append(
                ErrorRecord(
                    error_id=str(uuid.uuid4()),
                    node_name=INGRESS_WRITER,
                    error_type="SecurityValidationError",
                    message=f"Path traversal or empty URI detected in draw_packet_meta: '{uri}'",
                    blocking=True,
                )
            )

    return {"error_logs": errors} if errors else {}


async def hitl_interrupt_node(
    state: IroncladState,
    checkpoint_manager: BaseCheckpointManager | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Non-cognitive interrupt checkpoint boundary.

    Suspends execution awaiting authenticated human decision.
    """
    if checkpoint_manager and session_id:
        await checkpoint_manager.write_checkpoint(session_id=session_id, state=state)
    return {}


async def terminal_node(state: IroncladState) -> dict[str, Any]:
    """Terminal sink node reached upon completion or post-HITL resolution."""
    return {}


class CompiledGraph:
    """Executable representation of the compiled Tri-Track multi-agent DAG."""

    def __init__(
        self,
        nodes: dict[str, NodeDefinition],
        edges: list[EdgeDefinition],
        entry_point: str,
        interrupt_nodes: set[str],
    ) -> None:
        self.nodes = nodes
        self.edges = edges
        self.entry_point = entry_point
        self.interrupt_nodes = interrupt_nodes

    def get_downstream_nodes(self, node_name: str) -> list[str]:
        """Return list of immediate downstream node names for a given node."""
        return [edge.target for edge in self.edges if edge.source == node_name]

    def get_upstream_nodes(self, node_name: str) -> list[str]:
        """Return list of immediate upstream node names for a given node."""
        return [edge.source for edge in self.edges if edge.target == node_name]

    async def execute(
        self,
        initial_state: IroncladState,
        checkpoint_manager: BaseCheckpointManager | None = None,
        session_id: str | None = None,
        invoker: ModelInvoker | None = None,
    ) -> IroncladState:
        """Execute the full Tri-Track DAG from ingress to HITL interrupt.

        Flow:
        1. Ingress Node (Deterministic Validation)
        2. Parallel Fan-Out: ForensicAuditSentinel || FairPayStatutoryGuardian
        3. Barrier Join: Merges parallel updates safely through state reducers
        4. Fan-In: EverydayDecisionCardEmitter (Decision synthesis & notification)
        5. HITL Interrupt: Checkpoint snapshot and execution suspension

        Args:
            initial_state: Verified input state container.
            checkpoint_manager: Optional checkpoint store.
            session_id: Optional unique session identifier for checkpointing.
            invoker: Optional model invocation service double.

        Returns:
            Suspended IroncladState ready for executive review.
        """
        if invoker is None:
            invoker = get_model_invoker(initial_state.runtime_config.runtime_mode)

        if session_id is None:
            session_id = f"session_{initial_state.draw_packet_meta.project_id}_{initial_state.draw_packet_meta.draw_number}"

        state = initial_state

        with trace_audit_run(
            session_id=session_id,
            project_id=initial_state.draw_packet_meta.project_id,
            subcontractor_id=initial_state.draw_packet_meta.subcontractor_id,
            draw_number=initial_state.draw_packet_meta.draw_number,
        ):
            # Step 1: Ingress Node
            ingress_updates = await ingress_node(state)
            if ingress_updates:
                state = apply_state_update(state, ingress_updates, caller_node=INGRESS_WRITER)
                # If blocking ingress errors occur, return early before fan-out
                if any(e.blocking for e in state.error_logs):
                    return state

            # Step 2: Parallel Fan-Out (ForensicAuditSentinel || FairPayStatutoryGuardian)
            async def run_forensic() -> dict[str, Any]:
                async with trace_agent_invocation(FORENSIC_WRITER, session_id=session_id):
                    return await forensic_audit_sentinel_node(state=state, invoker=invoker)

            async def run_statutory() -> dict[str, Any]:
                async with trace_agent_invocation(STATUTORY_WRITER, session_id=session_id):
                    return await fair_pay_statutory_guardian_node(state=state, invoker=invoker)

            forensic_updates, statutory_updates = await asyncio.gather(
                run_forensic(), run_statutory()
            )

            # Step 3: Sequential Barrier State Merge
            # Reducers guarantee writer isolation and append-only log preservation
            state = apply_state_update(state, forensic_updates, caller_node=FORENSIC_WRITER)
            state = apply_state_update(state, statutory_updates, caller_node=STATUTORY_WRITER)

            # Step 4: Fan-In EverydayDecisionCardEmitter
            async with trace_agent_invocation(EVERYDAY_WRITER, session_id=session_id):
                everyday_updates = await everyday_decision_card_emitter_node(
                    state=state, invoker=invoker, dispatch_alert=True
                )
            state = apply_state_update(state, everyday_updates, caller_node=EVERYDAY_WRITER)

            # Step 5: HITL Interrupt Checkpoint Gate
            await hitl_interrupt_node(
                state=state,
                checkpoint_manager=checkpoint_manager,
                session_id=session_id,
            )

            return state

    async def resume_hitl(
        self,
        current_state: IroncladState,
        decision: ApprovalDecision,
        checkpoint_manager: BaseCheckpointManager | None = None,
        session_id: str | None = None,
    ) -> IroncladState:
        """Resume graph execution after human sign-off at the HITL gate.

        Transition: hitl_interrupt -> terminal.

        Args:
            current_state: State paused at the HITL interrupt.
            decision: Validated human approval decision.
            checkpoint_manager: Optional checkpoint store.
            session_id: Session identifier.

        Returns:
            Resolved IroncladState at the terminal completion state.
        """
        if decision.modified_inputs is not None:
            raise StateValidationError(
                message="Financial immutability violation: modified_inputs must be None during HITL resumption.",
                incident_context={"modified_inputs": decision.modified_inputs},
                node_name=HITL_WRITER,
            )

        # Record HITL feedback annotation to Langfuse / telemetry
        if session_id:
            record_hitl_feedback(
                session_id=session_id,
                action=decision.action.value,
                reason=decision.notes,
                state=current_state,
            )

        # Apply approval state write strictly as HITLInterruptHandler
        state = apply_state_update(
            current_state,
            {"approval_state": decision},
            caller_node=HITL_WRITER,
        )

        # Execute terminal node
        await terminal_node(state)

        # Update persistent checkpoint if manager is configured
        if checkpoint_manager and session_id:
            await checkpoint_manager.write_checkpoint(session_id=session_id, state=state)

        return state


class GraphBuilder:
    """Builder for constructing and validating Tri-Track multi-agent DAG topologies."""

    def __init__(self) -> None:
        self._nodes: dict[str, NodeDefinition] = {}
        self._edges: list[EdgeDefinition] = []
        self._entry_point: str | None = None
        self._interrupt_nodes: set[str] = set()

    def add_node(
        self,
        name: str,
        handler: Callable[..., Any] | Any = None,
        is_interrupt: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> "GraphBuilder":
        """Register a node in the graph."""
        if name in self._nodes:
            raise StateValidationError(
                message=f"Node '{name}' is already registered in GraphBuilder.",
                incident_context={"node_name": name},
                node_name="GraphBuilder",
            )
        self._nodes[name] = NodeDefinition(
            name=name,
            handler=handler,
            is_interrupt_point=is_interrupt,
            metadata=metadata or {},
        )
        if is_interrupt:
            self._interrupt_nodes.add(name)
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        condition: str | None = None,
    ) -> "GraphBuilder":
        """Add a directed transition between two nodes."""
        self._edges.append(
            EdgeDefinition(
                source=source,
                target=target,
                condition=condition,
            )
        )
        return self

    def set_entry_point(self, name: str) -> "GraphBuilder":
        """Define the initial entry point of the graph."""
        self._entry_point = name
        return self

    def set_interrupt(self, name: str) -> "GraphBuilder":
        """Mark a node as an execution pause/checkpoint gate."""
        if name not in self._nodes:
            raise StateValidationError(
                message=f"Cannot set interrupt on unregistered node: '{name}'",
                incident_context={"node_name": name},
                node_name="GraphBuilder",
            )
        self._nodes[name].is_interrupt_point = True
        self._interrupt_nodes.add(name)
        return self

    def compile(self) -> CompiledGraph:
        """Validate DAG topology and return an immutable CompiledGraph."""
        if not self._entry_point:
            if "ingress" in self._nodes:
                self._entry_point = "ingress"
            elif self._nodes:
                self._entry_point = next(iter(self._nodes.keys()))
            else:
                raise StateValidationError(
                    message="GraphBuilder has no nodes registered.",
                    node_name="GraphBuilder",
                )

        # Validate that all edge sources and targets exist
        for edge in self._edges:
            if edge.source not in self._nodes:
                raise StateValidationError(
                    message=f"Edge references non-existent source node: '{edge.source}'",
                    incident_context={"source": edge.source, "target": edge.target},
                    node_name="GraphBuilder",
                )
            if edge.target not in self._nodes:
                raise StateValidationError(
                    message=f"Edge references non-existent target node: '{edge.target}'",
                    incident_context={"source": edge.source, "target": edge.target},
                    node_name="GraphBuilder",
                )

        return CompiledGraph(
            nodes=self._nodes.copy(),
            edges=self._edges.copy(),
            entry_point=self._entry_point,
            interrupt_nodes=self._interrupt_nodes.copy(),
        )


def build_ironclad_graph() -> CompiledGraph:
    """Construct the authoritative IRONCLAD Tri-Track DAG."""
    builder = GraphBuilder()

    # 1. Ingress validation (deterministic)
    builder.add_node("ingress", handler=ingress_node)

    # 2. Parallel Cognitive Nodes (Fan-out)
    builder.add_node("forensic_audit_sentinel", handler=forensic_audit_sentinel_node)
    builder.add_node("fair_pay_statutory_guardian", handler=fair_pay_statutory_guardian_node)

    # 3. Everyday Synthesis Node (Fan-in)
    builder.add_node("everyday_decision_card_emitter", handler=everyday_decision_card_emitter_node)

    # 4. Mandatory HITL Interrupt Checkpoint Gate
    builder.add_node("hitl_interrupt", handler=hitl_interrupt_node, is_interrupt=True)

    # 5. Terminal Completion Node
    builder.add_node("terminal", handler=terminal_node)

    # Edges: Ingress -> Fan-Out
    builder.add_edge("ingress", "forensic_audit_sentinel")
    builder.add_edge("ingress", "fair_pay_statutory_guardian")

    # Edges: Fan-Out -> Fan-In join
    builder.add_edge("forensic_audit_sentinel", "everyday_decision_card_emitter")
    builder.add_edge("fair_pay_statutory_guardian", "everyday_decision_card_emitter")

    # Edges: Synthesis -> HITL Interrupt -> Terminal
    builder.add_edge("everyday_decision_card_emitter", "hitl_interrupt")
    builder.add_edge("hitl_interrupt", "terminal")

    builder.set_entry_point("ingress")
    return builder.compile()
