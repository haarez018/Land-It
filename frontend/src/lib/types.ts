/** Shared TypeScript types matching backend Pydantic schemas. */

export interface ResumeContact {
  name: string;
  email: string;
  phone?: string;
  linkedin?: string;
  github?: string;
  location?: string;
  portfolio?: string;
}

export interface WorkExperience {
  company: string;
  title: string;
  start_date: string;
  end_date?: string;
  location?: string;
  bullets: string[];
  technologies: string[];
  impact_metrics: string[];
  seniority_signals: string[];
}

export interface Education {
  institution: string;
  degree: string;
  field: string;
  graduation_date?: string;
  gpa?: number;
  honors: string[];
  relevant_courses: string[];
}

export interface Resume {
  id: string;
  user_id: string;
  raw_text: string;
  contact: ResumeContact;
  summary?: string;
  work_experience: WorkExperience[];
  education: Education[];
  skills: Record<string, string[]>;
  total_yoe: number;
  seniority_level: string;
  primary_domain: string;
}

export interface JDRequirement {
  text: string;
  category: "must_have" | "nice_to_have" | "bonus";
  skill_type: "technical" | "soft" | "domain" | "tool";
  extracted_keyword: string;
}

export interface JobDescription {
  id: string;
  raw_text: string;
  title: string;
  company: string;
  location: string;
  remote_policy: string;
  salary_range?: [number, number];
  seniority_level: string;
  employment_type: string;
  required_skills: string[];
  preferred_skills: string[];
  tech_stack: string[];
  requirements: JDRequirement[];
  fit_score?: number;
}

export interface DimensionScore {
  dimension_id: string;
  dimension_name: string;
  raw_score: number;
  weighted_score: number;
  weight: number;
  explanation: string;
  issues: string[];
  suggestions: string[];
  priority: "critical" | "high" | "medium" | "low";
}

export interface ATSScoreResult {
  total_score: number;
  letter_grade: string;
  dimension_scores: DimensionScore[];
  top_3_issues: string[];
  top_3_wins: string[];
  predicted_ats_pass: boolean;
  role_type: string;
  seniority_level: string;
  weights_used: Record<string, number>;
}

export type ApplicationStatus =
  | "discovered"
  | "queued"
  | "tailoring"
  | "ready"
  | "submitted"
  | "followed_up"
  | "phone_screen"
  | "interviewing"
  | "offer"
  | "rejected"
  | "withdrawn";

export interface Application {
  id: string;
  user_id: string;
  job_id: string;
  job: JobDescription;
  status: ApplicationStatus;
  fit_score: number;
  ats_score_before?: number;
  ats_score_after?: number;
  planner_priority: number;
}

// ── Tailor types ───────────────────────────────────────────────────────────

export interface ChangeLogEntry {
  section: string;
  original: string;
  rewritten: string;
  reason: string;
  dimension_improved: string[];
  confidence: string;
  requires_verification: boolean;
}

export interface TailorResult {
  score_before: number;
  score_after: number;
  improvement: number;
  letter_grade_before: string;
  letter_grade_after: string;
  predicted_ats_pass: boolean;
  change_log: ChangeLogEntry[];
  passes_applied: string[];
  sections_reordered: boolean;
  summary_rewritten: boolean;
  unified_diff: string;
  total_changes: number;
  changes_by_type: Record<string, number>;
  rewritten_resume: Resume;
}

// ── Standout types ─────────────────────────────────────────────────────────

export interface StandoutDimensionScore {
  dimension_id: string;
  dimension_name: string;
  raw_score: number;
  weighted_score: number;
  weight: number;
  explanation: string;
  issues: string[];
  suggestions: string[];
  priority: "critical" | "high" | "medium" | "low";
}

export interface StandoutScoreResult {
  total_score: number;
  letter_grade: string;
  dimension_scores: StandoutDimensionScore[];
  top_3_issues: string[];
  top_3_wins: string[];
  spike_detected: boolean;
  role_type: string;
  seniority_level: string;
  weights_used: Record<string, number>;
  amplification_tips: string[];
}

export interface CallbackPrediction {
  probability: number;
  confidence_interval: [number, number];
  confidence_level: "high" | "medium" | "low";
  top_positive_factors: string[];
  top_negative_factors: string[];
  vs_average_applicant: number;
  score_needed_for_50pct: number;
  fixes_for_10pct_boost: string[];
  role_type: string;
  seniority_level: string;
  combined_score: number;
  base_rate: number;
}

export interface DualScoreResult {
  ats_score: ATSScoreResult;
  standout_score: StandoutScoreResult;
  combined_score: number;
  combined_grade: string;
  total_dimensions: number;
  summary: string;
  callback_prediction?: CallbackPrediction;
}

// ── A/B Testing types ─────────────────────────────────────────────────────

export interface ABDimensionComparison {
  dimension_id: string;
  dimension_name: string;
  score_a: number;
  score_b: number;
  delta: number;
  winner: "A" | "B" | "tie";
  weight: number;
  weighted_impact: number;
}

export interface ABMergeSuggestion {
  section: string;
  recommendation: "use_a" | "use_b" | "combine" | "either";
  reason: string;
}

export interface ABTestResult {
  version_a_id: string;
  version_b_id: string;
  jd_id: string;
  version_a_ats: number;
  version_b_ats: number;
  version_a_standout: number;
  version_b_standout: number;
  version_a_combined: number;
  version_b_combined: number;
  version_a_callback: number;
  version_b_callback: number;
  overall_winner: "A" | "B" | "tie";
  win_margin: number;
  dimension_comparisons: ABDimensionComparison[];
  a_advantages: string[];
  b_advantages: string[];
  merge_suggestions: ABMergeSuggestion[];
  recommendation: string;
  role_type: string;
  seniority_level: string;
}

// ── Analytics types ───────────────────────────────────────────────────────

export interface FunnelMetrics {
  jobs_discovered: number;
  jobs_queued: number;
  jobs_applied: number;
  responses_received: number;
  interviews_scheduled: number;
  offers_received: number;
  rejections: number;
  conversion_rates: Record<string, number>;
  benchmark_comparisons: Record<string, string>;
}

export interface WeekBucket {
  week: string;
  avg_score: number;
  count: number;
}

export interface DimensionHeatmapData {
  dimension_averages: Record<string, number>;
  strongest_dimensions: string[];
  weakest_dimensions: string[];
  dimension_consistency: Record<string, number>;
}

export interface JobSearchAnalytics {
  funnel: FunnelMetrics;
  score_trends: Record<string, WeekBucket[]>;
  score_improvement: number;
  is_improving: boolean;
  dimension_heatmap: DimensionHeatmapData;
  this_week_wins: string[];
  focus_areas: string[];
  one_sentence_summary: string;
}

// ── Pitcher types ──────────────────────────────────────────────────────────

export interface CoverLetter {
  text: string;
  word_count: number;
  paragraphs: number;
  company_name: string;
  role_title: string;
  voice_match_score: number;
  company_personalization_score: number;
  requirements_addressed: string[];
  verification_notes: string[];
}

export interface VoiceProfile {
  avg_sentence_length: number;
  formality_level: string;
  characteristic_phrases: string[];
  punctuation_style: string;
  enthusiasm_markers: string[];
  hedging_frequency: string;
  storytelling_style: string;
  tone: string;
  vocabulary_complexity: string;
}

export interface CompanyContext {
  company_name: string;
  mission: string;
  values: string[];
  products: string[];
  culture_signals: string[];
  industry: string;
  tone: string;
  key_talking_points: string[];
}
