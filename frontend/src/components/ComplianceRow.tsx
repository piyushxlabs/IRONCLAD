"use client";

import React from "react";
import { ShieldCheck, ShieldAlert, Clock, AlertCircle, Scale } from "lucide-react";
import { LienChainStatus, StatutoryClock } from "@/types";

interface ComplianceRowProps {
  lienStatus?: LienChainStatus | string | null;
  statutoryClock?: StatutoryClock | null;
}

export const ComplianceRow: React.FC<ComplianceRowProps> = ({
  lienStatus,
  statutoryClock,
}) => {
  const getLienBadge = () => {
    switch (lienStatus) {
      case "VALID":
        return {
          title: "Mechanics Lien Chain: PASSED",
          desc: "Unconditional progress waivers verified across all periods. Execution & notary dates validated.",
          badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
          icon: <ShieldCheck className="w-5 h-5 text-emerald-400" />,
        };
      case "SUSPECT_PRE_DATED_NOTARY":
        return {
          title: "Mechanics Lien Chain: FLAGGED (Pre-Dated Notary)",
          desc: "Critical fraud warning: Notary acknowledgment date precedes check disbursement date.",
          badge: "bg-red-500/10 text-red-400 border-red-500/30",
          icon: <ShieldAlert className="w-5 h-5 text-red-400" />,
        };
      case "DEFECTIVE":
      case "MISSING_WAIVERS":
        return {
          title: `Mechanics Lien Chain: ${lienStatus}`,
          desc: "Missing unconditional waiver or gap in chain of custody. Potential double-payment liability.",
          badge: "bg-amber-500/10 text-amber-400 border-amber-500/30",
          icon: <ShieldAlert className="w-5 h-5 text-amber-400" />,
        };
      default:
        return {
          title: "Mechanics Lien Chain: PENDING AUDIT",
          desc: "Awaiting document verification against county recorder & disbursement records.",
          badge: "bg-gray-500/10 text-gray-400 border-gray-500/30",
          icon: <ShieldAlert className="w-5 h-5 text-gray-400" />,
        };
    }
  };

  const lien = getLienBadge();
  const daysRemaining = statutoryClock?.days_remaining ?? 0;
  const isCritical = statutoryClock?.critical_alert_threshold ?? (daysRemaining <= 2);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
      {/* Lien Chain Custody Card */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 shadow-lg flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-blue-400" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                Lien Waiver Chain-of-Custody
              </h3>
            </div>
            <span className={`text-xs font-mono font-medium px-2.5 py-0.5 rounded-full border ${lien.badge}`}>
              {lienStatus || "PENDING"}
            </span>
          </div>

          <div className="flex items-start gap-3 mt-2">
            <div className="p-2 rounded-lg bg-[#0B0F19] border border-[#1F2937] flex-shrink-0">
              {lien.icon}
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">{lien.title}</h4>
              <p className="text-xs text-gray-400 mt-1 leading-relaxed">{lien.desc}</p>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-[#1F2937] flex items-center justify-between text-[11px] text-gray-500 font-mono">
          <span>Rule: verify_lien_chain_integrity</span>
          <span>Notary Check: Deterministic</span>
        </div>
      </div>

      {/* Statutory Prompt-Payment Clock Card */}
      <div
        className={`bg-[#111827] border rounded-xl p-5 shadow-lg flex flex-col justify-between transition-colors ${
          isCritical ? "border-amber-500/50 bg-amber-950/10" : "border-[#1F2937]"
        }`}
      >
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-400" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                Statutory Prompt-Pay Countdown
              </h3>
            </div>
            {isCritical && (
              <span className="text-xs font-mono font-medium px-2.5 py-0.5 rounded-full border bg-red-500/10 text-red-400 border-red-500/30 flex items-center gap-1 animate-pulse">
                <AlertCircle className="w-3 h-3" />
                CRITICAL THRESHOLD (&le;48h)
              </span>
            )}
          </div>

          <div className="flex items-center justify-between mt-2">
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold font-mono text-white tracking-tight">
                  {daysRemaining}
                </span>
                <span className="text-sm font-semibold text-gray-300">Days Remaining</span>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Deadline:{" "}
                <span className="text-gray-200 font-mono">
                  {statutoryClock?.statutory_deadline_date || "—"}
                </span>
              </p>
            </div>

            <div className="text-right bg-[#0B0F19] border border-[#1F2937] rounded-lg p-2.5">
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block">
                Statutory Interest Penalty
              </span>
              <span className="text-sm font-bold font-mono text-amber-400">
                {statutoryClock?.monthly_penalty_rate_pct ? `${statutoryClock.monthly_penalty_rate_pct}% / mo` : "1.50% / mo"}
              </span>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-[#1F2937] flex items-center justify-between text-[11px] text-gray-500 font-mono">
          <span>Jurisdiction: {statutoryClock?.state_jurisdiction || "Texas Commercial"}</span>
          <span>Clause: {statutoryClock?.clause_classification || "pay-when-paid"}</span>
        </div>
      </div>
    </div>
  );
};
