"""AgentCoreMemorySessionManager and SQLite Session Checkpointing Backend.

Adheres strictly to AGENT_ORCHESTRATION_BLUEPRINT.md Section 10 and AGENT_MASTER_PLAN.md Step 9.
Provides type-safe, non-blocking asynchronous checkpoint management across Mock, SQLite (dev/staging),
and AgentCore Memory (prod) runtimes with zero Decimal precision loss and single-writer reducer compliance.
"""

import asyncio
import json
import os
import sqlite3
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

try:
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    BotoCoreError = Exception  # type: ignore[misc,assignment]
    ClientError = Exception  # type: ignore[misc,assignment]

from src.errors import StateValidationError, ToolExecutionError
from src.state.reducers import apply_state_update
from src.state.schema import ApprovalDecision, IroncladState


class BaseCheckpointManager(ABC):
    """Abstract asynchronous session checkpointing protocol."""

    @abstractmethod
    async def write_checkpoint(
        self,
        session_id: str,
        state: IroncladState | dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Persist state snapshot and return unique checkpoint identifier."""

    @abstractmethod
    async def read_checkpoint(
        self,
        session_id: str,
    ) -> IroncladState | None:
        """Retrieve most recent state snapshot for given session."""

    @abstractmethod
    async def get_checkpoint(
        self,
        checkpoint_id: str,
    ) -> IroncladState | None:
        """Retrieve exact state snapshot by checkpoint ID."""

    @abstractmethod
    async def list_checkpoints(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:
        """List checkpoint history and metadata for given session."""

    @abstractmethod
    async def resume_from_checkpoint(
        self,
        checkpoint_id: str,
        resumption_payload: dict[str, Any] | ApprovalDecision,
    ) -> IroncladState:
        """Resume graph execution from checkpoint by applying validated HITL approval decision."""


class MockCheckpointManager(BaseCheckpointManager):
    """In-memory checkpoint store for high-speed offline testing."""

    _checkpoints: ClassVar[dict[str, dict[str, Any]]] = {}
    _session_to_ids: ClassVar[dict[str, list[str]]] = {}

    def __init__(self) -> None:
        pass

    async def write_checkpoint(
        self,
        session_id: str,
        state: IroncladState | dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        checkpoint_id = f"cp_mock_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()

        if isinstance(state, IroncladState):
            state_json = state.model_dump_json()
        else:
            state_json = IroncladState.model_validate(state).model_dump_json()

        self._checkpoints[checkpoint_id] = {
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "created_at": now,
            "state_json": state_json,
            "metadata": metadata or {},
        }

        if session_id not in self._session_to_ids:
            self._session_to_ids[session_id] = []
        self._session_to_ids[session_id].append(checkpoint_id)

        return checkpoint_id

    async def read_checkpoint(self, session_id: str) -> IroncladState | None:
        ids = self._session_to_ids.get(session_id)
        if not ids:
            return None
        latest_id = ids[-1]
        entry = self._checkpoints.get(latest_id)
        if not entry:
            return None
        return IroncladState.model_validate_json(entry["state_json"])

    async def get_checkpoint(self, checkpoint_id: str) -> IroncladState | None:
        entry = self._checkpoints.get(checkpoint_id)
        if not entry:
            return None
        return IroncladState.model_validate_json(entry["state_json"])

    async def list_checkpoints(self, session_id: str) -> list[dict[str, Any]]:
        ids = self._session_to_ids.get(session_id, [])
        result = []
        for cid in ids:
            entry = self._checkpoints.get(cid)
            if entry:
                result.append(
                    {
                        "checkpoint_id": entry["checkpoint_id"],
                        "session_id": entry["session_id"],
                        "created_at": entry["created_at"],
                        "metadata": entry["metadata"],
                    }
                )
        return result

    async def resume_from_checkpoint(
        self,
        checkpoint_id: str,
        resumption_payload: dict[str, Any] | ApprovalDecision,
    ) -> IroncladState:
        state = await self.get_checkpoint(checkpoint_id)
        if state is None:
            raise ToolExecutionError(
                message=f"Checkpoint '{checkpoint_id}' not found.",
                incident_context={"checkpoint_id": checkpoint_id},
                node_name="HITLInterruptHandler",
            )

        if isinstance(resumption_payload, ApprovalDecision):
            decision = resumption_payload
        elif isinstance(resumption_payload, dict):
            decision = ApprovalDecision.model_validate(resumption_payload)
        else:
            raise StateValidationError(
                message="Invalid resumption payload type for approval state.",
                incident_context={"payload_type": str(type(resumption_payload))},
                node_name="HITLInterruptHandler",
            )

        if decision.modified_inputs is not None:
            raise StateValidationError(
                message="Financial immutability violation: modified_inputs must be None upon resumption.",
                incident_context={"modified_inputs": decision.modified_inputs},
                node_name="HITLInterruptHandler",
            )

        updated_state = apply_state_update(
            state=state,
            updates={"approval_state": decision},
            caller_node="HITLInterruptHandler",
        )
        return updated_state


class SQLiteCheckpointManager(BaseCheckpointManager):
    """Persistent SQLite-backed checkpoint store using non-blocking asyncio.to_thread."""

    def __init__(self, db_path: str = "checkpoints.db") -> None:
        self.db_path = db_path
        # Ensure parent directory exists if nested path provided
        parent_dir = Path(db_path).parent
        if str(parent_dir) not in ("", "."):
            parent_dir.mkdir(parents=True, exist_ok=True)
        self._init_db_sync()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db_sync(self) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        checkpoint_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        state_json TEXT NOT NULL,
                        metadata_json TEXT
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_checkpoints_session 
                    ON checkpoints (session_id, created_at DESC);
                    """
                )
        finally:
            conn.close()

    def _write_sync(
        self,
        checkpoint_id: str,
        session_id: str,
        created_at: str,
        state_json: str,
        metadata_json: str,
    ) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO checkpoints (checkpoint_id, session_id, created_at, state_json, metadata_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (checkpoint_id, session_id, created_at, state_json, metadata_json),
                )
        finally:
            conn.close()

    def _read_latest_sync(self, session_id: str) -> str | None:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT state_json FROM checkpoints
                WHERE session_id = ?
                ORDER BY created_at DESC, rowid DESC
                LIMIT 1
                """,
                (session_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def _get_sync(self, checkpoint_id: str) -> str | None:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT state_json FROM checkpoints
                WHERE checkpoint_id = ?
                """,
                (checkpoint_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def _list_sync(self, session_id: str) -> list[dict[str, Any]]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT checkpoint_id, session_id, created_at, metadata_json
                FROM checkpoints
                WHERE session_id = ?
                ORDER BY created_at ASC, rowid ASC
                """,
                (session_id,),
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                meta = json.loads(r[3]) if r[3] else {}
                results.append(
                    {
                        "checkpoint_id": r[0],
                        "session_id": r[1],
                        "created_at": r[2],
                        "metadata": meta,
                    }
                )
            return results
        finally:
            conn.close()

    async def write_checkpoint(
        self,
        session_id: str,
        state: IroncladState | dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        checkpoint_id = f"cp_sqlite_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()

        if isinstance(state, IroncladState):
            state_json = state.model_dump_json()
        else:
            state_json = IroncladState.model_validate(state).model_dump_json()

        metadata_json = json.dumps(metadata or {})

        await asyncio.to_thread(
            self._write_sync,
            checkpoint_id,
            session_id,
            now,
            state_json,
            metadata_json,
        )
        return checkpoint_id

    async def read_checkpoint(self, session_id: str) -> IroncladState | None:
        state_json = await asyncio.to_thread(self._read_latest_sync, session_id)
        if not state_json:
            return None
        return IroncladState.model_validate_json(state_json)

    async def get_checkpoint(self, checkpoint_id: str) -> IroncladState | None:
        state_json = await asyncio.to_thread(self._get_sync, checkpoint_id)
        if not state_json:
            return None
        return IroncladState.model_validate_json(state_json)

    async def list_checkpoints(self, session_id: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_sync, session_id)

    async def resume_from_checkpoint(
        self,
        checkpoint_id: str,
        resumption_payload: dict[str, Any] | ApprovalDecision,
    ) -> IroncladState:
        state = await self.get_checkpoint(checkpoint_id)
        if state is None:
            raise ToolExecutionError(
                message=f"Checkpoint '{checkpoint_id}' not found in SQLite store.",
                incident_context={"checkpoint_id": checkpoint_id},
                node_name="HITLInterruptHandler",
            )

        if isinstance(resumption_payload, ApprovalDecision):
            decision = resumption_payload
        elif isinstance(resumption_payload, dict):
            decision = ApprovalDecision.model_validate(resumption_payload)
        else:
            raise StateValidationError(
                message="Invalid resumption payload type for approval state.",
                incident_context={"payload_type": str(type(resumption_payload))},
                node_name="HITLInterruptHandler",
            )

        if decision.modified_inputs is not None:
            raise StateValidationError(
                message="Financial immutability violation: modified_inputs must be None upon resumption.",
                incident_context={"modified_inputs": decision.modified_inputs},
                node_name="HITLInterruptHandler",
            )

        updated_state = apply_state_update(
            state=state,
            updates={"approval_state": decision},
            caller_node="HITLInterruptHandler",
        )

        # Write resumed checkpoint
        session_id = f"session_{state.draw_packet_meta.project_id}_{state.draw_packet_meta.draw_number}"
        await self.write_checkpoint(
            session_id=session_id,
            state=updated_state,
            metadata={"resumed_from": checkpoint_id, "action": decision.action.value},
        )
        return updated_state


class AgentCoreMemorySessionManager(BaseCheckpointManager):
    """Production checkpoint manager integrating with Amazon Bedrock AgentCore memory.

    Features lazy boto3 initialization and automated local SQLite fallback when AWS credentials
    or AgentCore memory runtime are not configured.
    """

    def __init__(self, db_path: str = "checkpoints.db") -> None:
        self.db_path = db_path
        self._fallback_store = SQLiteCheckpointManager(db_path=db_path)
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy client initialization."""
        if self._client is None:
            try:
                import boto3
                from botocore.exceptions import BotoCoreError, ClientError

                region = os.getenv("AWS_REGION", "us-east-1")
                self._client = boto3.client("bedrock-agentcore", region_name=region)
            except (
                ImportError,
                AttributeError,
                RuntimeError,
                KeyError,
                ValueError,
                OSError,
                BotoCoreError,
                ClientError,
                Exception,
            ):
                self._client = None
        return self._client

    async def write_checkpoint(
        self,
        session_id: str,
        state: IroncladState | dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        client = self._get_client()
        if client is None:
            # Fallback to persistent SQLite
            return await self._fallback_store.write_checkpoint(session_id, state, metadata)

        # Production AgentCore Memory integration path
        checkpoint_id = f"cp_bedrock_{uuid.uuid4().hex[:12]}"
        if isinstance(state, IroncladState):
            state_json = state.model_dump_json()
        else:
            state_json = IroncladState.model_validate(state).model_dump_json()

        try:
            await asyncio.to_thread(
                client.create_session_checkpoint,
                SessionId=session_id,
                CheckpointId=checkpoint_id,
                StatePayload=state_json,
                Metadata=metadata or {},
            )
            return checkpoint_id
        except (
            AttributeError,
            RuntimeError,
            KeyError,
            ValueError,
            OSError,
            BotoCoreError,
            ClientError,
        ):
            # Fallback on transient / credential failure
            return await self._fallback_store.write_checkpoint(session_id, state, metadata)

    async def read_checkpoint(self, session_id: str) -> IroncladState | None:
        client = self._get_client()
        if client is None:
            return await self._fallback_store.read_checkpoint(session_id)

        try:
            response = await asyncio.to_thread(
                client.get_latest_session_checkpoint,
                SessionId=session_id,
            )
            state_json = response.get("StatePayload")
            if not state_json:
                return None
            return IroncladState.model_validate_json(state_json)
        except (
            AttributeError,
            RuntimeError,
            KeyError,
            ValueError,
            OSError,
            BotoCoreError,
            ClientError,
        ):
            return await self._fallback_store.read_checkpoint(session_id)

    async def get_checkpoint(self, checkpoint_id: str) -> IroncladState | None:
        client = self._get_client()
        if client is None:
            return await self._fallback_store.get_checkpoint(checkpoint_id)

        try:
            response = await asyncio.to_thread(
                client.get_session_checkpoint,
                CheckpointId=checkpoint_id,
            )
            state_json = response.get("StatePayload")
            if not state_json:
                return None
            return IroncladState.model_validate_json(state_json)
        except (
            AttributeError,
            RuntimeError,
            KeyError,
            ValueError,
            OSError,
            BotoCoreError,
            ClientError,
        ):
            return await self._fallback_store.get_checkpoint(checkpoint_id)

    async def list_checkpoints(self, session_id: str) -> list[dict[str, Any]]:
        client = self._get_client()
        if client is None:
            return await self._fallback_store.list_checkpoints(session_id)

        try:
            response = await asyncio.to_thread(
                client.list_session_checkpoints,
                SessionId=session_id,
            )
            return response.get("Checkpoints", [])
        except (
            AttributeError,
            RuntimeError,
            KeyError,
            ValueError,
            OSError,
            BotoCoreError,
            ClientError,
        ):
            return await self._fallback_store.list_checkpoints(session_id)

    async def resume_from_checkpoint(
        self,
        checkpoint_id: str,
        resumption_payload: dict[str, Any] | ApprovalDecision,
    ) -> IroncladState:
        return await self._fallback_store.resume_from_checkpoint(
            checkpoint_id, resumption_payload
        )


_MOCK_CHECKPOINT_SINGLETON = MockCheckpointManager()


def get_checkpoint_manager(
    mode: str | None = None,
    db_path: str = "checkpoints.db",
) -> BaseCheckpointManager:
    """Factory creating appropriate checkpoint backend according to runtime mode."""
    active_mode = (mode or os.environ.get("IRONCLAD_RUNTIME_MODE", "staging")).lower()

    if active_mode == "mock":
        return _MOCK_CHECKPOINT_SINGLETON
    if active_mode == "bedrock":
        return AgentCoreMemorySessionManager(db_path=db_path)
    if active_mode == "staging":
        return SQLiteCheckpointManager(db_path=db_path)

    return _MOCK_CHECKPOINT_SINGLETON
