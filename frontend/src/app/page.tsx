"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/Header";
import { StatusBanner } from "@/components/StatusBanner";
import { FinancialSummary } from "@/components/FinancialSummary";
import { ComplianceRow } from "@/components/ComplianceRow";
import { DiscrepancyTable } from "@/components/DiscrepancyTable";
import { ActionCenter } from "@/components/ActionCenter";
import { AuditTrailDrawer } from "@/components/AuditTrailDrawer";
import { fetchHealth, streamAudit, submitHitlDecision } from "@/lib/api";
import { ApprovalStatusAction, IroncladState } from "@/types";

const INITIAL_EMPTY_STATE: IroncladState = {
  draw_packet_meta: {
    project_id: "PROJ-SKYLINE-04",
    subcontractor_id: "SUB-CONCRETE-001",
    draw_number: 4,
    source_uris: ["tests/mocks/fixtures/draw_4_hvac_invoice.pdf"],
  },
  extracted_line_items: [],
  retainage_audit_result: null,
  lien_chain_status: "PENDING_VERIFICATION",
  statutory_prompt_pay_clock: {
    state_jurisdiction: "Texas Commercial",
    clause_classification: "pay-when-paid",
    statutory_deadline_date: "2026-09-30",
    days_remaining: 16,
    monthly_penalty_rate_pct: 1.5,
    critical_alert_threshold: false,
  },
  flagged_discrepancies: [],
  decision_card_payload: null,
  approval_state: null,
  error_logs: [],
};

export default function ExecutiveConsolePage() {
  const [state, setState] = useState<IroncladState>(INITIAL_EMPTY_STATE);
  const [runtimeMode, setRuntimeMode] = useState<string>("staging");
  const [selectedScenario, setSelectedScenario] = useState<string>("simple_clean");
  const [statusText, setStatusText] = useState<string>("");
  const [isAuditing, setIsAuditing] = useState<boolean>(false);
  const [isPausedForHitl, setIsPausedForHitl] = useState<boolean>(false);
  const [isSubmittingDecision, setIsSubmittingDecision] = useState<boolean>(false);
  const [checkpointId, setCheckpointId] = useState<string | null>(null);
  const [hasErrors, setHasErrors] = useState<boolean>(false);
  const [auditEvents, setAuditEvents] = useState<Array<{ time: string; node?: string; message: string }>>([]);

  // Fetch API health on mount
  useEffect(() => {
    fetchHealth()
      .then((health) => {
        if (health?.runtime_mode) {
          setRuntimeMode(health.runtime_mode);
        }
      })
      .catch((err) => {
        console.warn("Backend API not reachable at mount:", err);
      });
  }, []);

  const handleRunAudit = useCallback(async () => {
    setIsAuditing(true);
    setIsPausedForHitl(false);
    setHasErrors(false);
    setStatusText("Initiating forensic audit DAG...");
    setAuditEvents([]);

    const timestamp = () => new Date().toLocaleTimeString();

    try {
      await streamAudit(
        {
          scenario: selectedScenario,
          runtime_mode: runtimeMode,
        },
        {
          onTextDelta: (evt) => {
            setStatusText(evt.content);
            setAuditEvents((prev) => [
              ...prev,
              { time: timestamp(), node: evt.node, message: evt.content },
            ]);
          },
          onStateUpdate: (evt) => {
            setAuditEvents((prev) => [
              ...prev,
              {
                time: timestamp(),
                node: evt.caller_node,
                message: `State mutation merged: ${evt.field_name} (reducer: ${evt.reducer})`,
              },
            ]);

            setState((prev) => {
              const updated = { ...prev };
              if (evt.field_name === "extracted_line_items") {
                updated.extracted_line_items = evt.value;
              } else if (evt.field_name === "retainage_audit_result") {
                updated.retainage_audit_result = evt.value;
              } else if (evt.field_name === "lien_chain_status") {
                updated.lien_chain_status = evt.value;
              } else if (evt.field_name === "statutory_prompt_pay_clock") {
                updated.statutory_prompt_pay_clock = evt.value;
              } else if (evt.field_name === "flagged_discrepancies") {
                updated.flagged_discrepancies = evt.value;
              } else if (evt.field_name === "decision_card_payload") {
                updated.decision_card_payload = evt.value;
              }
              return updated;
            });
          },
          onApprovalRequired: (evt) => {
            setIsPausedForHitl(true);
            setCheckpointId(evt.checkpoint_id);
            setStatusText("Execution paused at HITL interrupt gate. Human authorization required.");
            setAuditEvents((prev) => [
              ...prev,
              {
                time: timestamp(),
                node: "HITLInterruptGate",
                message: `Durable checkpoint saved (${evt.checkpoint_id}). Paused for executive decision.`,
              },
            ]);

            setState((prev) => ({
              ...prev,
              decision_card_payload: evt.action_preview,
            }));
          },
          onError: (evt) => {
            setHasErrors(true);
            setStatusText(`Error [${evt.code}]: ${evt.message}`);
            setAuditEvents((prev) => [
              ...prev,
              { time: timestamp(), node: "ErrorHandler", message: `ERROR: ${evt.message}` },
            ]);
          },
          onStreamEnd: (evt) => {
            setIsAuditing(false);
            if (evt.reason === "completed") {
              setStatusText("Audit DAG completed successfully.");
            }
          },
        }
      );
    } catch (err: any) {
      setHasErrors(true);
      setIsAuditing(false);
      setStatusText(`Connection error: ${err.message || err}`);
    }
  }, [selectedScenario, runtimeMode]);

  const handleSubmitDecision = async (action: ApprovalStatusAction, reason?: string) => {
    if (!checkpointId) {
      alert("No active checkpoint available for resumption.");
      return;
    }

    setIsSubmittingDecision(true);
    const timestamp = new Date().toLocaleTimeString();

    try {
      const result = await submitHitlDecision({
        checkpoint_id: checkpointId,
        action,
        reason,
        runtime_mode: runtimeMode,
      });

      setState(result.state);
      setIsPausedForHitl(false);
      setStatusText(`Decision recorded: ${action}. Checkpoint resumed and resolved.`);
      setAuditEvents((prev) => [
        ...prev,
        {
          time: timestamp,
          node: "HITLResumptionHandler",
          message: `Decision '${action}' authenticated. Resumed graph and reached terminal completion.`,
        },
      ]);
    } catch (err: any) {
      alert(`Decision failed: ${err.message || err}`);
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  // Code-level verification for release authorization
  const openDiscrepancyCount = state.flagged_discrepancies?.length || 0;
  const isLienValid = state.lien_chain_status === "VALID";
  const canApprove =
    openDiscrepancyCount === 0 &&
    isLienValid &&
    state.approval_state === null &&
    isPausedForHitl;

  let approvalReasonDisallowed: string | null = null;
  if (!isPausedForHitl && !state.approval_state) {
    approvalReasonDisallowed = "Audit run required before release sign-off";
  } else if (openDiscrepancyCount > 0) {
    approvalReasonDisallowed = `Locked: ${openDiscrepancyCount} unaddressed discrepancy ${
      openDiscrepancyCount === 1 ? "flagged" : "flags"
    }`;
  } else if (!isLienValid) {
    approvalReasonDisallowed = `Locked: Lien chain status is ${state.lien_chain_status || "UNVERIFIED"}`;
  }

  // Derive display figures
  const grossAmount =
    state.decision_card_payload?.gross_amount_requested ||
    state.retainage_audit_result?.total_current_completed_and_stored ||
    "0.00";
  const retainageWithheld =
    state.decision_card_payload?.contractual_retainage_withheld ||
    state.retainage_audit_result?.total_retainage_withheld ||
    "0.00";
  const netRelease =
    state.decision_card_payload?.net_recommended_release ||
    state.retainage_audit_result?.net_current_payment_due ||
    "0.00";

  return (
    <main className="min-h-screen bg-[#0B0F19] text-gray-100 flex flex-col">
      {/* Top Header */}
      <Header
        projectId={state.draw_packet_meta?.project_id || "PROJ-SKYLINE-04"}
        subcontractorId={state.draw_packet_meta?.subcontractor_id || "SUB-CONCRETE-001"}
        drawNumber={state.draw_packet_meta?.draw_number || 4}
        runtimeMode={runtimeMode}
        selectedScenario={selectedScenario}
        isAuditing={isAuditing}
        onSelectScenario={(scen) => {
          setSelectedScenario(scen);
          // Set scenario preview info
          if (scen === "complex_defect") {
            setState((prev) => ({
              ...prev,
              draw_packet_meta: {
                project_id: "PROJ-METRO-02",
                subcontractor_id: "SUB-ELECTRICAL-902",
                draw_number: 2,
                source_uris: ["tests/mocks/fixtures/draw_2_electrical_defect_invoice.pdf"],
              },
              approval_state: null,
            }));
          } else if (scen === "edge_case") {
            setState((prev) => ({
              ...prev,
              draw_packet_meta: {
                project_id: "PROJ-BAY-03",
                subcontractor_id: "SUB-HVAC-303",
                draw_number: 3,
                source_uris: ["tests/mocks/fixtures/draw_3_plumbing_edge_case.pdf"],
              },
              approval_state: null,
            }));
          } else {
            setState((prev) => ({
              ...prev,
              draw_packet_meta: {
                project_id: "PROJ-SKYLINE-04",
                subcontractor_id: "SUB-CONCRETE-001",
                draw_number: 4,
                source_uris: ["tests/mocks/fixtures/draw_4_hvac_invoice.pdf"],
              },
              approval_state: null,
            }));
          }
        }}
        onRunAudit={handleRunAudit}
      />

      {/* Real-time State Banner */}
      <StatusBanner
        statusText={statusText}
        isAuditing={isAuditing}
        isPausedForHitl={isPausedForHitl}
        isResolved={state.approval_state !== null && state.approval_state !== undefined}
        terminalAction={state.approval_state?.action}
        hasErrors={hasErrors}
      />

      {/* Main Console Content */}
      <div className="max-w-7xl mx-auto w-full px-6 py-6 flex-1 flex flex-col gap-6">
        {/* 3 Dominant Financial KPI Tiles */}
        <FinancialSummary
          grossAmount={grossAmount}
          retainageWithheld={retainageWithheld}
          netRelease={netRelease}
          recommendedAction={state.decision_card_payload?.recommended_action}
        />

        {/* Compliance Row: Lien Chain & Statutory Prompt-Pay Countdown */}
        <ComplianceRow
          lienStatus={state.lien_chain_status}
          statutoryClock={state.statutory_prompt_pay_clock}
        />

        {/* Interactive Discrepancy Table */}
        <DiscrepancyTable discrepancies={state.flagged_discrepancies} />

        {/* 1-Click HITL Action Center */}
        <ActionCenter
          checkpointId={checkpointId}
          canApprove={canApprove}
          approvalReasonDisallowed={approvalReasonDisallowed}
          approvalState={state.approval_state}
          isSubmitting={isSubmittingDecision}
          onSubmitDecision={handleSubmitDecision}
        />

        {/* Expandable Forensic Audit Trail Drawer */}
        <AuditTrailDrawer state={state} auditEvents={auditEvents} />
      </div>

      {/* Institutional Compliance Footer */}
      <footer className="w-full border-t border-[#1F2937] bg-[#0B0F19] py-4 px-6 text-center text-xs text-gray-500 font-mono">
        IRONCLAD Sentinel Compliance Engine &bull; Zero-Chat Semi-Autonomous Review &bull; Tri-Track Multi-Agent DAG
      </footer>
    </main>
  );
}
