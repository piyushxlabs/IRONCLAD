export type LienChainStatus =
  | "VALID"
  | "DEFECTIVE"
  | "SUSPECT_PRE_DATED_NOTARY"
  | "MISSING_WAIVERS"
  | "MISSING_WAIVER"
  | "INVALID_FORM"
  | "PENDING_VERIFICATION";

export type RecommendedAction =
  | "APPROVE_RELEASE"
  | "HOLD_REQUEST_CORRECTED_WAIVER"
  | "HOLD_REQUEST_CORRECTION"
  | "ESCALATE_LEGAL"
  | string;

export type ApprovalStatusAction =
  | "APPROVE_RELEASE"
  | "HOLD_REQUEST_CORRECTION"
  | "ESCALATE_LEGAL";

export interface LineItem {
  line_item_id: string;
  description: string;
  contract_retainage_pct?: string | number;
  current_billed?: string | number;
  stored_materials?: string | number;
  prior_payments?: string | number;
  // UI aliases
  scheduled_value?: string | number;
  work_completed_from_previous?: string | number;
  work_completed_this_period?: string | number;
  total_completed_and_stored?: string | number;
  retainage_rate?: string | number;
  retainage_amount?: string | number;
}

export interface RetainageAuditResult {
  gross_amount_requested?: string | number;
  contractual_retainage_withheld?: string | number;
  net_recommended_release?: string | number;
  calculation_trace?: string[];
  // UI aliases
  total_current_completed_and_stored?: string | number;
  total_retainage_withheld?: string | number;
  total_prior_payments_deducted?: string | number;
  net_current_payment_due?: string | number;
  arithmetic_verified?: boolean;
  calculation_discrepancy_amount?: string | number | null;
}

export interface StatutoryClock {
  state?: string;
  days_remaining: number;
  deadline_timestamp?: string;
  penalty_interest_rate?: string | number;
  statute_reference?: string;
  // UI aliases
  state_jurisdiction?: string;
  clause_classification?: "pay-if-paid" | "pay-when-paid" | string;
  statutory_deadline_date?: string;
  monthly_penalty_rate_pct?: string | number;
  critical_alert_threshold?: boolean;
}

export interface Discrepancy {
  line_item_id?: string | null;
  discrepancy_type?: string;
  description: string;
  variance_amount?: string | number | null;
  // UI aliases
  discrepancy_id?: string;
  type?: string;
  severity?: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  citation_source?: string;
}

export interface DecisionCardPayload {
  draw_number: number;
  project_name?: string;
  subcontractor_trade?: string;
  gross_amount_requested: string | number;
  contractual_retainage_withheld: string | number;
  net_recommended_release: string | number;
  lien_chain_status: LienChainStatus;
  statutory_prompt_pay_clock?: StatutoryClock | null;
  recommended_action: RecommendedAction;
  blocking_discrepancies?: Discrepancy[];
  confidence_score?: number;
  // UI aliases
  project_id?: string;
  subcontractor_id?: string;
  prompt_payment_days_remaining?: number;
  critical_penalty_active?: boolean;
  action_rationale?: string;
  discrepancies?: Discrepancy[];
  line_items?: LineItem[];
}

export interface ApprovalDecision {
  action: ApprovalStatusAction;
  reviewer_id: string;
  timestamp?: string;
  notes?: string | null;
}

export interface DrawPacketMeta {
  project_id: string;
  subcontractor_id: string;
  draw_number: number;
  period_start?: string | null;
  period_end?: string | null;
  source_uris: string[];
  notary_acknowledged_date?: string | null;
  check_date?: string | null;
}

export interface IroncladState {
  draw_packet_meta: DrawPacketMeta;
  extracted_line_items: LineItem[];
  retainage_audit_result?: RetainageAuditResult | null;
  lien_chain_status?: LienChainStatus | null;
  statutory_prompt_pay_clock?: StatutoryClock | null;
  flagged_discrepancies: Discrepancy[];
  decision_card_payload?: DecisionCardPayload | null;
  approval_state?: ApprovalDecision | null;
  error_logs?: any[];
}

export type StreamEventType =
  | "text-delta"
  | "state-update"
  | "approval-required"
  | "error"
  | "stream-end";

export interface TextDeltaEvent {
  event_type: "text-delta";
  node?: string;
  content: string;
  timestamp?: string;
}

export interface StateUpdateEvent {
  event_type: "state-update";
  field_name: string;
  reducer: string;
  value: any;
  caller_node: string;
  timestamp?: string;
}

export interface ApprovalRequiredEvent {
  event_type: "approval-required";
  checkpoint_id: string;
  action_preview: DecisionCardPayload;
  graph_node?: string;
  timestamp?: string;
}

export interface ErrorEvent {
  event_type: "error";
  code: string;
  message: string;
  timestamp?: string;
}

export interface StreamEndEvent {
  event_type: "stream-end";
  reason: "interrupted" | "completed" | "error";
  timestamp?: string;
}

export type IroncladStreamEvent =
  | TextDeltaEvent
  | StateUpdateEvent
  | ApprovalRequiredEvent
  | ErrorEvent
  | StreamEndEvent;

export interface AuditStreamCallbacks {
  onTextDelta?: (event: TextDeltaEvent) => void;
  onStateUpdate?: (event: StateUpdateEvent) => void;
  onApprovalRequired?: (event: ApprovalRequiredEvent) => void;
  onError?: (event: ErrorEvent) => void;
  onStreamEnd?: (event: StreamEndEvent) => void;
}
