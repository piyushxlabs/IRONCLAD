"use client";

import React, { useState } from "react";
import { CheckCircle2, PauseCircle, AlertTriangle, ShieldCheck, Lock } from "lucide-react";
import { ApprovalDecision, ApprovalStatusAction } from "@/types";

interface ActionCenterProps {
  checkpointId?: string | null;
  canApprove: boolean;
  approvalReasonDisallowed?: string | null;
  approvalState?: ApprovalDecision | null;
  isSubmitting: boolean;
  onSubmitDecision: (action: ApprovalStatusAction, reason?: string) => Promise<void>;
}

export const ActionCenter: React.FC<ActionCenterProps> = ({
  checkpointId,
  canApprove,
  approvalReasonDisallowed,
  approvalState,
  isSubmitting,
  onSubmitDecision,
}) => {
  const [showReasonModal, setShowReasonModal] = useState(false);
  const [selectedAction, setSelectedAction] = useState<ApprovalStatusAction | null>(null);
  const [reasonInput, setReasonInput] = useState("");

  const handleActionClick = (action: ApprovalStatusAction) => {
    if (action === "APPROVE_RELEASE") {
      // Direct 1-click execution for verified release
      onSubmitDecision("APPROVE_RELEASE", "Executive approval: all calculations and lien waivers verified.");
    } else {
      setSelectedAction(action);
      setReasonInput(
        action === "HOLD_REQUEST_CORRECTION"
          ? "Hold release: Requesting corrected unconditional lien waiver from subcontractor."
          : "Escalate to Legal: Defective lien waiver / suspected pre-dated notary fraud."
      );
      setShowReasonModal(true);
    }
  };

  const handleConfirmModal = async () => {
    if (!selectedAction) return;
    await onSubmitDecision(selectedAction, reasonInput);
    setShowReasonModal(false);
    setSelectedAction(null);
  };

  if (approvalState) {
    const getResolvedDetails = () => {
      switch (approvalState.action) {
        case "APPROVE_RELEASE":
          return {
            title: "Release Approved by Executive",
            color: "bg-emerald-950/30 border-emerald-500/40 text-emerald-400",
            icon: <CheckCircle2 className="w-5 h-5 text-emerald-400" />,
          };
        case "HOLD_REQUEST_CORRECTION":
          return {
            title: "Disbursement Held — Correction Requested",
            color: "bg-amber-950/30 border-amber-500/40 text-amber-400",
            icon: <PauseCircle className="w-5 h-5 text-amber-400" />,
          };
        case "ESCALATE_LEGAL":
          return {
            title: "Escalated to General Counsel",
            color: "bg-red-950/30 border-red-500/40 text-red-400",
            icon: <AlertTriangle className="w-5 h-5 text-red-400" />,
          };
      }
    };

    const details = getResolvedDetails();

    return (
      <div className={`w-full border rounded-xl p-6 shadow-lg ${details.color}`}>
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-black/30 border border-white/10">
              {details.icon}
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                {details.title}
                <span className="text-xs font-mono font-normal px-2 py-0.5 rounded bg-white/10 text-gray-200">
                  ACTION RECORDED
                </span>
              </h3>
              <p className="text-xs text-gray-300 mt-1">
                Reviewer: <span className="font-semibold text-white">{approvalState.reviewer_id}</span>
                {approvalState.notes && <span> — &ldquo;{approvalState.notes}&rdquo;</span>}
              </p>
            </div>
          </div>
          <div className="text-right font-mono text-xs text-gray-400">
            <span>HITL Resumption: Terminal Gate Reached</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#111827] border border-[#1F2937] rounded-xl p-6 shadow-xl relative">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-5">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-blue-400" />
            Human-in-the-Loop (HITL) Decision Center
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Single-click authenticated gate. No fund release can occur without explicit executive authorization.
          </p>
        </div>

        {checkpointId && (
          <span className="text-xs font-mono text-gray-400 bg-[#0B0F19] px-3 py-1.5 rounded-lg border border-[#1F2937]">
            Checkpoint: <span className="text-blue-400">{checkpointId}</span>
          </span>
        )}
      </div>

      {/* 3 Action Buttons */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Button 1: Approve Release */}
        <div className="relative group">
          <button
            onClick={() => handleActionClick("APPROVE_RELEASE")}
            disabled={!canApprove || isSubmitting}
            className={`w-full flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl font-bold text-sm shadow-lg transition-all ${
              canApprove && !isSubmitting
                ? "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20 active:scale-[0.98]"
                : "bg-gray-800/80 text-gray-500 border border-gray-700/50 cursor-not-allowed"
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Approve Release</span>
            {!canApprove && <Lock className="w-3.5 h-3.5 ml-1 text-gray-500" />}
          </button>
          {!canApprove && approvalReasonDisallowed && (
            <p className="text-[11px] text-amber-400/90 text-center mt-1.5 font-sans leading-tight">
              {approvalReasonDisallowed}
            </p>
          )}
        </div>

        {/* Button 2: Hold & Request Correction */}
        <button
          onClick={() => handleActionClick("HOLD_REQUEST_CORRECTION")}
          disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl font-bold text-sm bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-600/20 active:scale-[0.98] transition-all disabled:opacity-50"
        >
          <PauseCircle className="w-4 h-4" />
          <span>Hold & Request Correction</span>
        </button>

        {/* Button 3: Escalate to Legal */}
        <button
          onClick={() => handleActionClick("ESCALATE_LEGAL")}
          disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl font-bold text-sm bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-600/20 active:scale-[0.98] transition-all disabled:opacity-50"
        >
          <AlertTriangle className="w-4 h-4" />
          <span>Escalate to Legal</span>
        </button>
      </div>

      {/* Confirmation Modal */}
      {showReasonModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <h4 className="text-base font-bold text-white mb-1">
              Confirm Action: {selectedAction?.replace(/_/g, " ")}
            </h4>
            <p className="text-xs text-gray-400 mb-4">
              Provide justification notes to be logged to the immutable compliance audit trail.
            </p>

            <textarea
              value={reasonInput}
              onChange={(e) => setReasonInput(e.target.value)}
              rows={3}
              className="w-full bg-[#0B0F19] border border-[#1F2937] rounded-xl p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors resize-none"
              placeholder="Enter audit explanation or note..."
            />

            <div className="flex items-center justify-end gap-3 mt-4">
              <button
                onClick={() => setShowReasonModal(false)}
                className="px-4 py-2 rounded-lg text-xs font-semibold text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmModal}
                disabled={isSubmitting}
                className="px-5 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-all shadow-md active:scale-95"
              >
                {isSubmitting ? "Submitting..." : "Confirm & Resume DAG"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
