"use client";

import React from "react";
import { DollarSign, ShieldAlert, CheckCircle } from "lucide-react";

interface FinancialSummaryProps {
  grossAmount: string | number;
  retainageWithheld: string | number;
  netRelease: string | number;
  recommendedAction?: string | null;
}

export const FinancialSummary: React.FC<FinancialSummaryProps> = ({
  grossAmount,
  retainageWithheld,
  netRelease,
  recommendedAction,
}) => {
  const formatCurrency = (val: string | number): string => {
    const num = typeof val === "string" ? parseFloat(val) : val;
    if (isNaN(num)) return "$0.00";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  };

  const getReleaseColor = () => {
    if (recommendedAction === "APPROVE_RELEASE") {
      return {
        bg: "bg-emerald-950/20 border-emerald-500/40",
        text: "text-emerald-400",
        label: "Verified for Immediate Release",
        icon: <CheckCircle className="w-4 h-4 text-emerald-400 inline mr-1" />,
      };
    }
    if (recommendedAction === "ESCALATE_LEGAL") {
      return {
        bg: "bg-red-950/20 border-red-500/40",
        text: "text-red-400",
        label: "Discharge Frozen — Legal Escalation",
        icon: <ShieldAlert className="w-4 h-4 text-red-400 inline mr-1" />,
      };
    }
    return {
      bg: "bg-amber-950/20 border-amber-500/40",
      text: "text-amber-400",
      label: "Release Held — Discrepancies Flagged",
      icon: <ShieldAlert className="w-4 h-4 text-amber-400 inline mr-1" />,
    };
  };

  const releaseStyle = getReleaseColor();

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs font-semibold tracking-wider text-gray-400 uppercase flex items-center gap-1.5">
          <DollarSign className="w-3.5 h-3.5 text-blue-400" />
          Audited Financial Summary (Zero-LLM Deterministic Math)
        </h2>
        <span className="text-[10px] text-gray-500 font-mono">
          Method: audit_retainage_math (Decimal precision)
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Tile 1: Gross Requested */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-gray-700 transition-colors">
          <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-bl-full pointer-events-none" />
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
            Gross Requested Amount
          </p>
          <div className="text-2xl lg:text-3xl font-bold font-mono text-white tracking-tight">
            {formatCurrency(grossAmount)}
          </div>
          <p className="text-[11px] text-gray-500 mt-2">
            Total completed work + stored materials this billing cycle
          </p>
        </div>

        {/* Tile 2: Retainage Withheld */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-gray-700 transition-colors">
          <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-bl-full pointer-events-none" />
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">
              Retainage Withheld
            </p>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
              Contractual Rate
            </span>
          </div>
          <div className="text-2xl lg:text-3xl font-bold font-mono text-amber-300 tracking-tight">
            {formatCurrency(retainageWithheld)}
          </div>
          <p className="text-[11px] text-gray-500 mt-2">
            Statutory & contractual escrow withheld from disbursement
          </p>
        </div>

        {/* Tile 3: Net Recommended Release */}
        <div
          className={`bg-[#111827] border rounded-xl p-5 shadow-lg relative overflow-hidden transition-all ${releaseStyle.bg}`}
        >
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">
              Net Recommended Release
            </p>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 border border-white/10 text-gray-300">
              1-Click Decision Target
            </span>
          </div>
          <div className={`text-2xl lg:text-3xl font-bold font-mono tracking-tight ${releaseStyle.text}`}>
            {formatCurrency(netRelease)}
          </div>
          <p className="text-[11px] text-gray-400 mt-2 flex items-center">
            {releaseStyle.icon}
            {releaseStyle.label}
          </p>
        </div>
      </div>
    </div>
  );
};
