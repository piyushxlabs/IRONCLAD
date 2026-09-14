import {
  ApprovalDecision,
  ApprovalRequiredEvent,
  ApprovalStatusAction,
  AuditStreamCallbacks,
  ErrorEvent,
  IroncladState,
  StateUpdateEvent,
  StreamEndEvent,
  TextDeltaEvent,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchHealth(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/health`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSnapshot(
  checkpointId: string,
  runtimeMode: string = "staging"
): Promise<IroncladState> {
  const res = await fetch(
    `${API_BASE}/api/snapshot/${encodeURIComponent(checkpointId)}?runtime_mode=${encodeURIComponent(
      runtimeMode
    )}`,
    {
      headers: { Accept: "application/json" },
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch checkpoint '${checkpointId}': ${res.statusText}`);
  }
  return res.json();
}

export async function submitHitlDecision(params: {
  checkpoint_id: string;
  action: ApprovalStatusAction;
  reason?: string;
  reviewer_id?: string;
  runtime_mode?: string;
}): Promise<{
  status: string;
  checkpoint_id: string;
  approval_state: ApprovalDecision;
  state: IroncladState;
}> {
  const res = await fetch(`${API_BASE}/api/hitl/decide`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      checkpoint_id: params.checkpoint_id,
      action: params.action,
      reason: params.reason || null,
      reviewer_id: params.reviewer_id || "executive_reviewer",
      runtime_mode: params.runtime_mode || "staging",
      modified_inputs: null, // Guaranteed null per financial immutability mandate
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.error || `HTTP ${res.status}: ${res.statusText}`);
  }

  return res.json();
}

export async function streamAudit(
  payload: {
    scenario?: string;
    runtime_mode?: string;
    session_id?: string;
    draw_packet_meta?: any;
  },
  callbacks: AuditStreamCallbacks
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/audit/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      scenario: payload.scenario,
      runtime_mode: payload.runtime_mode || "staging",
      session_id: payload.session_id,
      draw_packet_meta: payload.draw_packet_meta,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Failed to initiate audit stream: HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      const trimmed = part.trim();
      if (!trimmed) continue;

      let eventType = "";
      let dataJson = "";

      for (const line of trimmed.split("\n")) {
        const l = line.trim();
        if (l.startsWith("event:")) {
          eventType = l.slice("event:".length).trim();
        } else if (l.startsWith("data:")) {
          dataJson = l.slice("data:".length).trim();
        }
      }

      if (!eventType || !dataJson) continue;

      try {
        const parsedData = JSON.parse(dataJson);
        switch (eventType) {
          case "text-delta":
            callbacks.onTextDelta?.(parsedData as TextDeltaEvent);
            break;
          case "state-update":
            callbacks.onStateUpdate?.(parsedData as StateUpdateEvent);
            break;
          case "approval-required":
            callbacks.onApprovalRequired?.(parsedData as ApprovalRequiredEvent);
            break;
          case "error":
            callbacks.onError?.(parsedData as ErrorEvent);
            break;
          case "stream-end":
            callbacks.onStreamEnd?.(parsedData as StreamEndEvent);
            break;
        }
      } catch (err) {
        console.error("Failed to parse SSE payload chunk:", dataJson, err);
      }
    }
  }
}
