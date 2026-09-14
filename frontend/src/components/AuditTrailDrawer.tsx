"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronUp, Download, FileCode, CheckSquare, Terminal } from "lucide-react";
import { IroncladState } from "@/types";

interface AuditTrailDrawerProps {
  state: IroncladState;
  auditEvents: Array<{ time: string; node?: string; message: string }>;
}

export const AuditTrailDrawer: React.FC<AuditTrailDrawerProps> = ({ state, auditEvents }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"trace" | "json" | "items">("trace");

  const downloadJson = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(state, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute(
      "download",
      `ironclad_audit_${state.draw_packet_meta?.project_id || "draw"}_draw${
        state.draw_packet_meta?.draw_number || 1
      }.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const lineItems = state.extracted_line_items || [];

  return (
    <div className="w-full bg-[#111827] border border-[#1F2937] rounded-xl overflow-hidden shadow-xl">
      {/* Header Bar */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-[#161F30] transition-colors"
      >
        <div className="flex items-center gap-3">
          <Terminal className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-bold text-white">Forensic Audit Trail & State Inspection</h3>
          <span className="text-[11px] px-2.5 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 font-mono">
            {auditEvents.length} Verified Traces
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              downloadJson();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#0B0F19] text-gray-300 border border-[#1F2937] hover:border-gray-600 hover:text-white transition-all shadow-sm"
          >
            <Download className="w-3.5 h-3.5 text-blue-400" />
            <span>Download Audit JSON</span>
          </button>
          <div className="text-gray-400 hover:text-white transition-colors">
            {isOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isOpen && (
        <div className="border-t border-[#1F2937] bg-[#0B0F19]/80 p-6">
          {/* Sub-navigation Tabs */}
          <div className="flex items-center gap-2 mb-4 border-b border-[#1F2937] pb-3">
            <button
              onClick={() => setActiveTab("trace")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === "trace"
                  ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <CheckSquare className="w-3.5 h-3.5" />
              <span>Execution Timeline</span>
            </button>
            <button
              onClick={() => setActiveTab("items")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === "items"
                  ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Extracted Line Items ({lineItems.length})</span>
            </button>
            <button
              onClick={() => setActiveTab("json")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === "json"
                  ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              <span>Immutable State JSON</span>
            </button>
          </div>

          {/* Tab 1: Execution Timeline */}
          {activeTab === "trace" && (
            <div className="space-y-2.5 max-h-72 overflow-y-auto pr-2 font-mono text-xs">
              {auditEvents.length === 0 ? (
                <p className="text-gray-500 italic">No events logged yet. Execute an audit to begin trace.</p>
              ) : (
                auditEvents.map((evt, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 bg-[#111827] border border-[#1F2937] rounded-lg p-2.5"
                  >
                    <span className="text-[10px] text-gray-500 flex-shrink-0 mt-0.5">{evt.time}</span>
                    {evt.node && (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 flex-shrink-0">
                        {evt.node}
                      </span>
                    )}
                    <span className="text-gray-300 font-sans">{evt.message}</span>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Tab 2: Extracted Line Items */}
          {activeTab === "items" && (
            <div className="overflow-x-auto max-h-72 overflow-y-auto">
              <table className="w-full text-left text-xs text-gray-300 font-mono">
                <thead className="text-[10px] text-gray-400 uppercase bg-[#111827] sticky top-0 border-b border-[#1F2937]">
                  <tr>
                    <th className="px-4 py-2">ID</th>
                    <th className="px-4 py-2">Description</th>
                    <th className="px-4 py-2 text-right">Scheduled Value</th>
                    <th className="px-4 py-2 text-right">Completed This Period</th>
                    <th className="px-4 py-2 text-right">Stored Materials</th>
                    <th className="px-4 py-2 text-right">Retainage Rate</th>
                    <th className="px-4 py-2 text-right">Retainage Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1F2937]">
                  {lineItems.map((item, idx) => {
                    const scheduled = item.scheduled_value != null ? Number(item.scheduled_value) : null;
                    const billed = (item.current_billed != null ? Number(item.current_billed) : null)
                      ?? (item.work_completed_this_period != null ? Number(item.work_completed_this_period) : null);
                    const stored = item.stored_materials != null ? Number(item.stored_materials) : null;
                    const rate = (item.contract_retainage_pct != null ? Number(item.contract_retainage_pct) : null)
                      ?? (item.retainage_rate != null ? Number(item.retainage_rate) : null);
                    const retainage = (item.retainage_amount != null ? Number(item.retainage_amount) : null)
                      ?? (billed != null && rate != null ? (billed + (stored || 0)) * rate : null);

                    const fmt = (v: number | null) => (v != null && !isNaN(v) ? `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—");
                    const fmtPct = (v: number | null) => (v != null && !isNaN(v) ? `${(v * 100).toFixed(0)}%` : "—");

                    return (
                      <tr key={item.line_item_id || idx} className="hover:bg-[#111827]/40">
                        <td className="px-4 py-2 text-blue-400">{item.line_item_id}</td>
                        <td className="px-4 py-2 font-sans">{item.description}</td>
                        <td className="px-4 py-2 text-right">{fmt(scheduled)}</td>
                        <td className="px-4 py-2 text-right">{fmt(billed)}</td>
                        <td className="px-4 py-2 text-right">{fmt(stored)}</td>
                        <td className="px-4 py-2 text-right">{fmtPct(rate)}</td>
                        <td className="px-4 py-2 text-right text-amber-300">{fmt(retainage)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Tab 3: Raw JSON */}
          {activeTab === "json" && (
            <pre className="bg-[#050811] text-emerald-400 p-4 rounded-xl border border-[#1F2937] text-xs font-mono max-h-80 overflow-auto whitespace-pre-wrap leading-relaxed">
              {JSON.stringify(state, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};
