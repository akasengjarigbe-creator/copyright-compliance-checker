export type ComplianceLabel =
  | "Fully Compliant"
  | "Partially Compliant"
  | "Non-Compliant";


export interface ImageRecord {
  src: string;

  alt: string | null;
  title: string | null;

  attributes: Record<string, string>;
}


export interface AttributionEvidence {
  image: ImageRecord;

  nearby_text: string;
  caption: string | null;

  possible_author: string | null;

  licence_name: string | null;
  licence_url: string | null;

  rights_url: string | null;

  source_name: string | null;
  source_url: string | null;

  image_html: string | null;
  analysed_html_fragment: string | null;

  author_evidence_text: string | null;
  author_evidence_source: string | null;

  licence_evidence_text: string | null;
  licence_evidence_source: string | null;

  licence_url_evidence_text: string | null;
  licence_url_evidence_source: string | null;

  source_evidence_text: string | null;
  source_evidence_source: string | null;

  rights_evidence_text: string | null;
  rights_evidence_source: string | null;
}


export interface CriterionResult {
  criterion: string;
  passed: boolean;

  score: number;
  weight: number;

  rationale: string;
}


export interface RuleBasedAssessment {
  image_src: string;

  total_score: number;
  label: ComplianceLabel;

  criteria: CriterionResult[];

  manual_review_required: boolean;
  manual_review_reason: string | null;

  recommendations: string[];
}


export interface AiCriterionAssessment {
  criterion: string;
  passed: boolean;

  rationale: string;
}


export interface AiAssessment {
  image_src: string;

  overall_label: ComplianceLabel;

  criteria: AiCriterionAssessment[];

  explanation: string;

  manual_review_required: boolean;
  manual_review_reason: string | null;
}


export interface ImageAnalysisResult {
  image_src: string;

  evidence: AttributionEvidence;

  rule_based_result: RuleBasedAssessment;
  ai_result: AiAssessment;
}


export interface ComplianceReport {
  overall_rule_score: number;
  total_images: number;

  rule_fully_compliant: number;
  rule_partially_compliant: number;
  rule_non_compliant: number;

  ai_fully_compliant: number;
  ai_partially_compliant: number;
  ai_non_compliant: number;

  manual_review_recommended: boolean;
  manual_review_count: number;

  summary: string;

  image_results: ImageAnalysisResult[];
}