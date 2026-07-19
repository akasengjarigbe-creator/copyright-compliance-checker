export type ComplianceLabel =
  | "Fully Compliant"
  | "Partially Compliant"
  | "Non-Compliant";

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
}

export interface ComparisonAssessment {
  image_src: string;
  rule_assessment: ComplianceLabel;
  ai_assessment: ComplianceLabel;
  systems_agree: boolean;
  manual_review_recommended: boolean;
  criterion_disagreements: string[];
  explanation: string;
}

export interface ThreeResultImageAssessment {
  image_src: string;
  rule_based_result: RuleBasedAssessment;
  ai_result: AiAssessment;
  comparison_result: ComparisonAssessment;
}

export interface ThreeResultComplianceReport {
  overall_rule_score: number;
  total_images: number;

  rule_fully_compliant: number;
  rule_partially_compliant: number;
  rule_non_compliant: number;

  ai_fully_compliant: number;
  ai_partially_compliant: number;
  ai_non_compliant: number;

  systems_agree_count: number;
  systems_disagree_count: number;

  manual_review_recommended: boolean;
  manual_review_count: number;

  summary: string;
  image_results: ThreeResultImageAssessment[];
}