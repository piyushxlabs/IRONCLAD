"use client";

import React from "react";
import { AlertTriangle, CheckCircle2, Clock, Activity } from "lucide-react";

interface StatusBannerProps {
  statusText: string;
  isAuditing: boolean;
  isPausedForHitl: boolean;
  isResolved: boolean;
  terminalAction?: string | null;
  hasErrors: boolean;
}

export const StatusBanner: React.FC<StatusBannerProps> = ({
  statusText,
  isAuditing,
  isPausedForHitl,
  isResolved,
  terminalAction,
  hasErrors,
}) => {
  if (hasErrors) {
    return (
      <div className="w-full bg-red-950/40 border-y border-red-500/40 px-6 py-3 flex items-center justify-between">
        <div className="max-w-7xl mx-auto w-full flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <div>
            <h2 className="text-sm font-semibold text-red-200">Execution Halted / Compliance Alert</h2>
            <p className="text-xs text-red-300/80">{statusText || "Audit interrupted due to state validation or compliance error."}</p>
          </div>
        </div>
      </div>
    );
  }

  if (isResolved) {
    return (
      <div className="w-full bg-emerald-950/40 border-y border-emerald-500/40 px-6 py-3">
        <div className="max-w-7xl mx-auto w-full flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            <div>
              <h2 className="text-sm font-semibold text-emerald-200">
                Audit Resolved — Action: {terminalAction || "COMPLETED"}
              </h2>
              <p className="text-xs text-emerald-300/80">
                Human sign-off recorded. Checkpoint updated and immutable audit trail committed.
              </p>
            </div>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
            TERMINAL_STATE
          </span>
        </div>
      </div>
    );
  }

  if (isPausedForHitl) {
    return (
      <div className="w-full bg-amber-950/30 border-y border-amber-500/40 px-6 py-3">
        <div className="max-w-7xl mx-auto w-full flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-amber-400 flex-shrink-0 animate-pulse" />
            <div>
              <h2 className="text-sm font-semibold text-amber-200">
                Audit Complete — Executive Decision Required
              </h2>
              <p className="text-xs text-amber-300/80">
                Multi-agent DAG paused at durable HITL checkpoint gate. Review verified figures below to submit decision.
              </p>
            </div>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
            INTERRUPT_GATE
          </span>
        </div>
      </div>
    );
  }

  if (isAuditing) {
    return (
      <div className="w-full bg-blue-950/30 border-y border-blue-500/40 px-6 py-3">
        <div className="max-w-7xl mx-auto w-full flex items-center gap-3">
          <Activity className="w-5 h-5 text-blue-400 flex-shrink-0 animate-spin" />
          <div>
            <h2 className="text-sm font-semibold text-blue-200">
              Auditing Draw Packet (Tri-Track Cascade Active)
            </h2>
            <p className="text-xs text-blue-300/80 font-mono">
              {statusText || "Forensic audit & statutory prompt-pay clock calculations in progress..."}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#111827]/60 border-y border-[#1F2937] px-6 py-2.5">
      <div className="max-w-7xl mx-auto w-full flex items-center justify-between text-xs text-gray-400">
        <span className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          Ready for audit execution. Select scenario and click &ldquo;Execute Audit&rdquo;.
        </span>
        <span className="font-mono text-gray-500">FastAPI SSE Bridge: ACTIVE</span>
      </div>
    </div>
  );
};
