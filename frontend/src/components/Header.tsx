"use client";

import React from "react";
import { ShieldCheck, Cpu, RefreshCw, Layers } from "lucide-react";

interface HeaderProps {
  projectId: string;
  subcontractorId: string;
  drawNumber: number;
  runtimeMode: string;
  selectedScenario: string;
  isAuditing: boolean;
  onSelectScenario: (scenario: string) => void;
  onRunAudit: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  projectId,
  subcontractorId,
  drawNumber,
  runtimeMode,
  selectedScenario,
  isAuditing,
  onSelectScenario,
  onRunAudit,
}) => {
  const getRuntimeBadge = () => {
    switch (runtimeMode.toLowerCase()) {
      case "staging":
        return {
          label: "Gemini 3.8 Flash Staging",
          color: "bg-blue-500/10 text-blue-400 border-blue-500/30",
        };
      case "bedrock":
        return {
          label: "AWS Bedrock AgentCore",
          color: "bg-purple-500/10 text-purple-400 border-purple-500/30",
        };
      default:
        return {
          label: "Hermetic Mock Double",
          color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
        };
    }
  };

  const badge = getRuntimeBadge();

  return (
    <header className="w-full bg-[#111827] border-b border-[#1F2937] px-6 py-4 shadow-xl">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        {/* Brand & Project Identity */}
        <div className="flex items-center space-x-4">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white shadow-lg shadow-blue-500/20">
            <ShieldCheck className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                IRONCLAD
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-900/60 text-blue-300 border border-blue-700/50 uppercase tracking-wider">
                  SENTINEL
                </span>
              </h1>
              <span className={`text-xs px-2.5 py-0.5 rounded-full border font-medium flex items-center gap-1.5 ${badge.color}`}>
                <Cpu className="w-3 h-3" />
                {badge.label}
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-2">
              <span>AIA G702/G703 Retainage & Lien-Discharge Sentinel</span>
              <span className="text-gray-600">•</span>
              <span className="font-mono text-gray-300">Project: {projectId || "—"}</span>
              <span className="text-gray-600">•</span>
              <span className="font-mono text-gray-300">Sub: {subcontractorId || "—"}</span>
              <span className="text-gray-600">•</span>
              <span className="font-mono text-blue-400">Draw #{drawNumber || 0}</span>
            </p>
          </div>
        </div>

        {/* Scenario Controls & Actions */}
        <div className="flex items-center space-x-3 w-full md:w-auto justify-end">
          <div className="flex items-center bg-[#0B0F19] rounded-lg border border-[#1F2937] p-1 text-xs">
            <Layers className="w-3.5 h-3.5 text-gray-400 ml-2 mr-1" />
            <select
              value={selectedScenario}
              onChange={(e) => onSelectScenario(e.target.value)}
              disabled={isAuditing}
              className="bg-transparent text-gray-200 text-xs px-2 py-1.5 outline-none cursor-pointer focus:ring-0"
            >
              <option value="simple_clean" className="bg-[#111827] text-white">
                Simple Clean Case (Texas Masonry)
              </option>
              <option value="complex_defect" className="bg-[#111827] text-white">
                Complex Defect Case (Pre-Dated Notary)
              </option>
              <option value="edge_case" className="bg-[#111827] text-white">
                Edge Case (Pay-if-Paid Rider)
              </option>
            </select>
          </div>

          <button
            onClick={onRunAudit}
            disabled={isAuditing}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold shadow-md transition-all ${
              isAuditing
                ? "bg-blue-600/40 text-blue-200 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/20 active:scale-95"
            }`}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isAuditing ? "animate-spin" : ""}`} />
            {isAuditing ? "Auditing DAG..." : "Execute Audit"}
          </button>
        </div>
      </div>
    </header>
  );
};
