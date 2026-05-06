export type RiskLevel = "overdue" | "critical" | "due_soon" | "watch" | "compliant" | "archived_unverified";
export type CaseStatus = "processing" | "pending_review" | "verified" | "active" | "closed";
export type DirectiveStatus =
  | "pending_review"
  | "verified"
  | "in_progress"
  | "completed"
  | "overdue"
  | "contempt_risk";

export type UserRole = "uploader" | "reviewer" | "officer" | "admin";

export interface DashboardSummary {
  total_active_cases: number;
  overdue_count: number;
  critical_count: number;
  due_soon_count: number;
  watch_count: number;
  compliant_count: number;
}

export interface CaseStatusResponse {
  status: CaseStatus;
  progress_percent: number;
  message: string;
}

export type DirectiveType = "government_action" | "judicial_direction" | "private_party" | "ongoing_injunction" | "administrative" | "judicial_outcome" | "financial";

export interface Directive {
  id: string;
  case_id: string;
  directive_text: string;
  source_paragraph?: string | null;
  confidence_score?: number | null;
  owner_designation: string;
  owner_department?: string | null;
  deadline?: string | null;
  deadline_basis?: string | null;
  status: DirectiveStatus;
  risk_level?: RiskLevel | null;
  requires_human_review: boolean;
  directive_type?: DirectiveType | null;
  is_enforceable?: boolean | null;
  legal_confidence?: number | null;
  deadline_convention?: string | null;
  verified_by?: string | null;
  verified_at?: string | null;
  notes?: string | null;
}

export interface CaseDetailResponse {
  id: string;
  case_number: string;
  court_name: string;
  judgment_date?: string | null;
  status: CaseStatus;
  directives: Directive[];
  audit_logs: AuditLog[];
}

export interface AuditLog {
  id: string;
  table_name: string;
  record_id: string;
  action: string;
  officer_name: string;
  timestamp: string;
  old_value?: unknown;
  new_value?: unknown;
  ip_address?: string | null;
}

