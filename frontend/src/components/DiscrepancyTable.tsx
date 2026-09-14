"use client";

import React from "react";
import { AlertOctagon, CheckCircle, FileWarning } from "lucide-react";
import { Discrepancy } from "@/types";

interface DiscrepancyTableProps {
  discrepancies: Discrepancy[];
}

export const DiscrepancyTable: React.FC<DiscrepancyTableProps> = ({ discrepancies }) => {
  const formatCurrency = (val?: string | number | null): string => {
    if (!val) return "—";
    const num = typeof val === "string" ? parseFloat(val) : val;
    if (isNaN(num) || num === 0) return "—";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case "CRITICAL":
        return "bg-red-500/15 text-red-400 border-red-500/30";
      case "HIGH":
        return "bg-amber-500/15 text-amber-400 border-amber-500/30";
      case "MEDIUM":
        return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
      default:
        return "bg-blue-500/15 text-blue-400 border-blue-500/30";
    }
  };

  if (!discrepancies || discrepancies.length === 0) {
    return (
      <div className="w-full bg-[#111827] border border-[#1F2937] rounded-xl p-6 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <CheckCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              Audit Findings & Discrepancies
              <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                0 Open Findings
              </span>
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              All line items, retainage arithmetic, and lien waiver chronological dates verified with 100% deterministic precision.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#111827] border border-[#1F2937] rounded-xl overflow-hidden shadow-lg">
      <div className="px-6 py-4 border-b border-[#1F2937] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileWarning className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-semibold text-white">Flagged Discrepancies & Audit Exceptions</h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30 font-mono font-medium">
            {discrepancies.length} {discrepancies.length === 1 ? "Issue" : "Issues"} Flagged
          </span>
        </div>
        <span className="text-[11px] text-gray-400 font-mono">
          Code-Enforced Gate: Fund release locked
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-gray-300">
          <thead className="bg-[#0B0F19] text-gray-400 uppercase tracking-wider font-semibold text-[10px] border-b border-[#1F2937]">
            <tr>
              <th className="px-6 py-3">Line Item / Source</th>
              <th className="px-6 py-3">Discrepancy Type</th>
              <th className="px-6 py-3">Finding Description</th>
              <th className="px-6 py-3 text-right">Variance Amount</th>
              <th className="px-6 py-3 text-center">Severity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1F2937]/70 font-mono">
            {discrepancies.map((d, index) => (
              <tr key={d.discrepancy_id || index} className="hover:bg-[#1F2937]/30 transition-colors">
                <td className="px-6 py-3.5 text-blue-400 font-semibold whitespace-nowrap">
                  {d.line_item_id || "DRAW_ENVELOPE"}
                </td>
                <td className="px-6 py-3.5 text-gray-200 whitespace-nowrap">
                  <div className="flex items-center gap-1.5">
                    <AlertOctagon className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                    <span>{d.type}</span>
                  </div>
                </td>
                <td className="px-6 py-3.5 text-gray-300 font-sans max-w-md">
                  <p className="leading-snug">{d.description}</p>
                  {d.citation_source && (
                    <span className="text-[10px] text-gray-500 font-mono block mt-1">
                      Ref: {d.citation_source}
                    </span>
                  )}
                </td>
                <td className="px-6 py-3.5 text-right font-semibold text-amber-300 whitespace-nowrap">
                  {formatCurrency(d.variance_amount)}
                </td>
                <td className="px-6 py-3.5 text-center whitespace-nowrap">
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded border font-semibold uppercase ${getSeverityBadge(
                      d.severity
                    )}`}
                  >
                    {d.severity}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
