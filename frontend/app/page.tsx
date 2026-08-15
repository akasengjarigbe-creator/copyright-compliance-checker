"use client";

import { useState } from "react";
import jsPDF from "jspdf";

import Header from "@/components/Header";
import UploadPanel, {
  type AnalysisInput,
} from "@/components/UploadPanel";
import {
  analyseHtml,
  analyseUrl,
  analyseZip,
} from "@/lib/api";
import type {
  ComplianceLabel,
  ComplianceReport,
} from "@/types/report";


function getLabelClasses(
  label: ComplianceLabel,
): string {
  if (label === "Fully Compliant") {
    return (
      "bg-emerald-100 text-emerald-800 " +
      "ring-emerald-200"
    );
  }

  if (label === "Partially Compliant") {
    return (
      "bg-amber-100 text-amber-800 " +
      "ring-amber-200"
    );
  }

  return (
    "bg-red-100 text-red-800 " +
    "ring-red-200"
  );
}


function getStatusText(
  passed: boolean,
): string {
  return passed ? "Pass" : "Fail";
}


function displayValue(
  value: string | null | undefined,
): string {
  if (!value || !value.trim()) {
    return "Not detected";
  }

  return value;
}


function exportReportAsPdf(
  report: ComplianceReport,
): void {
  const pdf = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const margin = 15;

  const pageWidth =
    pdf.internal.pageSize.getWidth();

  const pageHeight =
    pdf.internal.pageSize.getHeight();

  const contentWidth =
    pageWidth - margin * 2;

  let y = 20;


  function ensureSpace(
    requiredHeight: number,
  ): void {
    if (
      y + requiredHeight >
      pageHeight - 15
    ) {
      pdf.addPage();
      y = 20;
    }
  }


  function addHeading(
    text: string,
    size = 14,
  ): void {
    ensureSpace(12);

    pdf.setFont(
      "helvetica",
      "bold",
    );

    pdf.setFontSize(size);

    const lines =
      pdf.splitTextToSize(
        text,
        contentWidth,
      );

    pdf.text(
      lines,
      margin,
      y,
    );

    y +=
      lines.length *
        (size * 0.45) +
      4;
  }


  function addText(
    text: string,
    size = 10,
  ): void {
    pdf.setFont(
      "helvetica",
      "normal",
    );

    pdf.setFontSize(size);

    const lines =
      pdf.splitTextToSize(
        text,
        contentWidth,
      );

    for (const line of lines) {
      ensureSpace(6);

      pdf.text(
        line,
        margin,
        y,
      );

      y += 5;
    }

    y += 2;
  }


  function addLabelValue(
    label: string,
    value: string | number,
  ): void {
    ensureSpace(12);

    pdf.setFont(
      "helvetica",
      "bold",
    );

    pdf.setFontSize(10);

    pdf.text(
      `${label}:`,
      margin,
      y,
    );

    y += 5;

    addText(
      String(value),
      10,
    );
  }


  addHeading(
    "Copyright Compliance Report",
    18,
  );

  addText(
    report.summary,
  );

  addLabelValue(
    "Overall rule-based score",
    `${report.overall_rule_score}%`,
  );

  addLabelValue(
    "Images analysed",
    report.total_images,
  );

  addLabelValue(
    "Images requiring manual review",
    report.manual_review_count,
  );


  report.image_results.forEach(
    (
      imageResult,
      index,
    ) => {
      const evidence =
        imageResult.evidence;

      const ruleResult =
        imageResult.rule_based_result;

      const aiResult =
        imageResult.ai_result;

      pdf.addPage();
      y = 20;

      addHeading(
        `Image ${index + 1}`,
        16,
      );

      addLabelValue(
        "Image source",
        imageResult.image_src,
      );


      /*
       * Evidence
       */

      addHeading(
        "Evidence Used for Assessment",
        13,
      );

      addHeading(
        "Copyright evidence",
        11,
      );

      addLabelValue(
        "Found in",
        displayValue(
          evidence.author_evidence_source,
        ),
      );

      addLabelValue(
        "Evidence",
        displayValue(
          evidence.author_evidence_text,
        ),
      );


      addHeading(
        "Source evidence",
        11,
      );

      addLabelValue(
        "Found in",
        displayValue(
          evidence.source_evidence_source,
        ),
      );

      addLabelValue(
        "Evidence",
        displayValue(
          evidence.source_evidence_text,
        ),
      );


      addHeading(
        "Licence evidence",
        11,
      );

      addLabelValue(
        "Found in",
        displayValue(
          evidence.licence_evidence_source,
        ),
      );

      addLabelValue(
        "Evidence",
        displayValue(
          evidence.licence_evidence_text,
        ),
      );

      addLabelValue(
        "Licence terms URL",
        displayValue(
          evidence.licence_url,
        ),
      );


      /*
       * Rule assessment
       */

      addHeading(
        "Rule-Based Assessment",
        14,
      );

      addLabelValue(
        "Classification",
        ruleResult.label,
      );

      addLabelValue(
        "Score",
        `${ruleResult.total_score}%`,
      );

      ruleResult.criteria.forEach(
        (criterion) => {
          addHeading(
            criterion.criterion,
            11,
          );

          addText(
            `Result: ${
              criterion.passed
                ? "Pass"
                : "Fail"
            }`,
          );

          addText(
            `Score: ${criterion.score}/${criterion.weight}`,
          );

          addText(
            criterion.rationale,
          );
        },
      );


      if (
        ruleResult.recommendations
          .length > 0
      ) {
        addHeading(
          "Recommendations",
          11,
        );

        ruleResult.recommendations.forEach(
          (recommendation) => {
            addText(
              `- ${recommendation}`,
            );
          },
        );
      }


      if (
        ruleResult.manual_review_required
      ) {
        addHeading(
          "Manual Review Required",
          11,
        );

        addText(
          ruleResult.manual_review_reason ??
            "Manual review is required.",
        );
      }


      /*
       * AI assessment
       */

      addHeading(
        "AI Assessment",
        14,
      );

      addLabelValue(
        "Classification",
        aiResult.overall_label,
      );

      addText(
        aiResult.explanation,
      );

      aiResult.criteria.forEach(
        (criterion) => {
          addHeading(
            criterion.criterion,
            11,
          );

          addText(
            `Result: ${
              criterion.passed
                ? "Pass"
                : "Fail"
            }`,
          );

          addText(
            criterion.rationale,
          );
        },
      );


      if (
        aiResult.manual_review_required
      ) {
        addHeading(
          "Manual Review Required",
          11,
        );

        addText(
          aiResult.manual_review_reason ??
            "Manual review is required.",
        );
      }
    },
  );


  pdf.save(
    "copyright-compliance-report.pdf",
  );
}


export default function Home() {
  const [report, setReport] =
    useState<ComplianceReport | null>(
      null,
    );

  const [isLoading, setIsLoading] =
    useState(false);

  const [
    errorMessage,
    setErrorMessage,
  ] = useState("");


  async function handleAnalyse(
    input: AnalysisInput,
  ): Promise<void> {
    setIsLoading(true);
    setErrorMessage("");
    setReport(null);

    try {
      let result: ComplianceReport;

      if (
        input.method === "url"
      ) {
        result = await analyseUrl(
          input.url ?? "",
          input.intendedUse,
        );
      } else if (
        input.method === "html"
      ) {
        result = await analyseHtml(
          input.html ?? "",
          input.intendedUse,
          input.baseUrl,
        );
      } else {
        if (!input.file) {
          throw new Error(
            "No ZIP file was selected.",
          );
        }

        result = await analyseZip(
          input.file,
          input.intendedUse,
        );
      }

      setReport(result);
    } catch (error) {
      if (
        error instanceof Error
      ) {
        setErrorMessage(
          error.message,
        );
      } else {
        setErrorMessage(
          "An unexpected error occurred during analysis.",
        );
      }
    } finally {
      setIsLoading(false);
    }
  }


  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10 text-slate-900">
      <div className="mx-auto max-w-6xl">
        <Header />

        <UploadPanel
          onAnalyse={handleAnalyse}
          isLoading={isLoading}
        />


        {errorMessage && (
          <section
            role="alert"
            className="mt-8 rounded-xl border border-red-200 bg-red-50 p-5 text-red-900"
          >
            <h2 className="font-semibold">
              Analysis could not be
              completed
            </h2>

            <p className="mt-2 text-sm leading-6">
              {errorMessage}
            </p>
          </section>
        )}


        {report && (
          <section className="mt-8 space-y-8">

            {/* Report summary */}

            <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8">
              <div className="flex flex-wrap items-start justify-between gap-5">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wider text-blue-700">
                    Analysis complete
                  </p>

                  <h2 className="mt-1 text-2xl font-bold">
                    Copyright compliance
                    report
                  </h2>

                  <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
                    {report.summary}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    exportReportAsPdf(
                      report,
                    )
                  }
                  className="rounded-lg bg-blue-700 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  Export PDF
                </button>
              </div>


              <div className="mt-6 grid gap-4 sm:grid-cols-3">
                <article className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
                  <p className="text-sm text-slate-500">
                    Rule score
                  </p>

                  <p className="mt-1 text-2xl font-bold">
                    {
                      report.overall_rule_score
                    }
                    %
                  </p>
                </article>


                <article className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
                  <p className="text-sm text-slate-500">
                    Images analysed
                  </p>

                  <p className="mt-1 text-2xl font-bold">
                    {report.total_images}
                  </p>
                </article>


                <article className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
                  <p className="text-sm text-slate-500">
                    Manual review
                  </p>

                  <p className="mt-1 text-2xl font-bold">
                    {
                      report.manual_review_count
                    }
                  </p>
                </article>
              </div>
            </section>


            {/* Image results */}

            <section className="space-y-6">
              {report.image_results.map(
                (
                  imageResult,
                  imageIndex,
                ) => {
                  const evidence =
                    imageResult.evidence;

                  const ruleResult =
                    imageResult.rule_based_result;

                  const aiResult =
                    imageResult.ai_result;

                  return (
                    <article
                      key={`${imageResult.image_src}-${imageIndex}`}
                      className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8"
                    >

                      {/* Image heading */}

                      <div className="border-b border-slate-200 pb-5">
                        <p className="text-sm font-semibold uppercase tracking-wider text-blue-700">
                          Image{" "}
                          {imageIndex + 1}
                        </p>

                        <h3 className="mt-1 break-all text-lg font-bold">
                          {
                            imageResult.image_src
                          }
                        </h3>
                      </div>


                      <div className="mt-6 grid gap-6 lg:grid-cols-2">

                        {/* Rule assessment */}

                        <section className="min-w-0 overflow-hidden rounded-xl bg-slate-50 p-5 ring-1 ring-slate-200">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <h4 className="font-bold">
                              Rule-based
                              assessment
                            </h4>

                            <span
                              className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${getLabelClasses(
                                ruleResult.label,
                              )}`}
                            >
                              {
                                ruleResult.label
                              }
                            </span>
                          </div>


                          <p className="mt-4 text-3xl font-bold">
                            {
                              ruleResult.total_score
                            }
                            %
                          </p>


                          {/*
                            Evidence is intentionally
                            displayed inside the
                            assessment rather than in a
                            separate "Information found"
                            section.
                          */}

                          <div className="mt-5">
                            <h5 className="text-base font-bold text-slate-900">
                              Evidence used for
                              assessment
                            </h5>

                            <p className="mt-1 text-sm leading-6 text-slate-600">
                              The following evidence
                              was extracted from the
                              webpage for this image.
                            </p>
                          </div>


                          <div className="mt-4 grid gap-4">

                            {/* Copyright evidence */}

                            <div className="min-w-0 overflow-hidden rounded-lg bg-white p-4 ring-1 ring-slate-200">
                              <h5 className="font-semibold">
                                Copyright
                                evidence
                              </h5>

                              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Found in
                              </p>

                              <p className="mt-1 text-sm leading-6 text-slate-800">
                                {displayValue(
                                  evidence.author_evidence_source,
                                )}
                              </p>

                              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Evidence
                              </p>

                              <p className="mt-1 break-words text-sm leading-6 text-slate-800">
                                {displayValue(
                                  evidence.author_evidence_text,
                                )}
                              </p>
                            </div>


                            {/* Source evidence */}

                            <div className="min-w-0 overflow-hidden rounded-lg bg-white p-4 ring-1 ring-slate-200">
                              <h5 className="font-semibold">
                                Source evidence
                              </h5>

                              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Found in
                              </p>

                              <p className="mt-1 text-sm leading-6 text-slate-800">
                                {displayValue(
                                  evidence.source_evidence_source,
                                )}
                              </p>

                              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Evidence
                              </p>

                              <p className="mt-1 break-all text-sm leading-6 text-slate-800">
                                {displayValue(
                                  evidence.source_evidence_text,
                                )}
                              </p>
                            </div>


                            {/* Licence evidence */}

                            <div className="min-w-0 overflow-hidden rounded-lg bg-white p-4 ring-1 ring-slate-200">
                              <h5 className="font-semibold">
                                Licence evidence
                              </h5>

                              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Found in
                              </p>

                              <p className="mt-1 text-sm leading-6 text-slate-800">
                                {displayValue(
                                  evidence.licence_evidence_source,
                                )}
                              </p>

                              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Evidence
                              </p>

                              <p className="mt-1 break-words text-sm leading-6 text-slate-800">
                                {displayValue(
                                  evidence.licence_evidence_text,
                                )}
                              </p>

                              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Licence terms URL
                              </p>

                              <div className="mt-1 break-all text-sm leading-6 text-slate-800">
                                {evidence.licence_url ? (
                                  <a
                                    href={
                                      evidence.licence_url
                                    }
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-blue-700 underline decoration-blue-300 underline-offset-2 hover:text-blue-900"
                                  >
                                    {
                                      evidence.licence_url
                                    }
                                  </a>
                                ) : (
                                  "Not detected"
                                )}
                              </div>
                            </div>
                          </div>


                          {/* Criteria */}

                          <div className="mt-6 space-y-3">
                            {ruleResult.criteria.map(
                              (
                                criterion,
                                criterionIndex,
                              ) => (
                                <div
                                  key={`${criterion.criterion}-${criterionIndex}`}
                                  className="min-w-0 overflow-hidden rounded-lg bg-white p-4 ring-1 ring-slate-200"
                                >
                                  <div className="flex items-start justify-between gap-4">
                                    <p className="font-medium">
                                      {
                                        criterion.criterion
                                      }
                                    </p>

                                    <span
                                      className={
                                        criterion.passed
                                          ? "text-sm font-semibold text-emerald-700"
                                          : "text-sm font-semibold text-red-700"
                                      }
                                    >
                                      {getStatusText(
                                        criterion.passed,
                                      )}
                                    </span>
                                  </div>

                                  <p className="mt-2 max-w-full break-words [overflow-wrap:anywhere] text-sm leading-6 text-slate-600">
                                    {
                                      criterion.rationale
                                    }
                                  </p>

                                  <p className="mt-2 text-xs text-slate-500">
                                    Score:{" "}
                                    {
                                      criterion.score
                                    }
                                    /
                                    {
                                      criterion.weight
                                    }
                                  </p>
                                </div>
                              ),
                            )}
                          </div>


                          {/* Recommendations */}

                          {ruleResult
                            .recommendations
                            .length > 0 && (
                            <div className="mt-5">
                              <h5 className="font-semibold">
                                Recommendations
                              </h5>

                              <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-600">
                                {ruleResult.recommendations.map(
                                  (
                                    recommendation,
                                    recommendationIndex,
                                  ) => (
                                    <li
                                      key={`${recommendation}-${recommendationIndex}`}
                                      className="rounded-lg bg-white px-4 py-3 ring-1 ring-slate-200"
                                    >
                                      {
                                        recommendation
                                      }
                                    </li>
                                  ),
                                )}
                              </ul>
                            </div>
                          )}


                          {/* Rule manual review */}

                          {ruleResult.manual_review_required && (
                            <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4">
                              <p className="font-semibold text-amber-950">
                                Manual review
                                required
                              </p>

                              <p className="mt-2 text-sm leading-6 text-amber-900">
                                {ruleResult.manual_review_reason ??
                                  "Manual review is required."}
                              </p>
                            </div>
                          )}
                        </section>


                        {/* AI assessment */}

                        <section className="min-w-0 overflow-hidden rounded-xl bg-slate-50 p-5 ring-1 ring-slate-200">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <h4 className="font-bold">
                              AI assessment
                            </h4>

                            <span
                              className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${getLabelClasses(
                                aiResult.overall_label,
                              )}`}
                            >
                              {
                                aiResult.overall_label
                              }
                            </span>
                          </div>


                          <p className="mt-4 max-w-full break-words [overflow-wrap:anywhere] text-sm leading-6 text-slate-700">
                            {
                              aiResult.explanation
                            }
                          </p>


                          <div className="mt-5 space-y-3">
                            {aiResult.criteria.map(
                              (
                                criterion,
                                criterionIndex,
                              ) => (
                                <div
                                  key={`${criterion.criterion}-${criterionIndex}`}
                                  className="min-w-0 overflow-hidden rounded-lg bg-white p-4 ring-1 ring-slate-200"
                                >
                                  <div className="flex items-start justify-between gap-4">
                                    <p className="font-medium">
                                      {
                                        criterion.criterion
                                      }
                                    </p>

                                    <span
                                      className={
                                        criterion.passed
                                          ? "text-sm font-semibold text-emerald-700"
                                          : "text-sm font-semibold text-red-700"
                                      }
                                    >
                                      {getStatusText(
                                        criterion.passed,
                                      )}
                                    </span>
                                  </div>

                                  <p className="mt-2 max-w-full break-words [overflow-wrap:anywhere] text-sm leading-6 text-slate-600">
                                    {
                                      criterion.rationale
                                    }
                                  </p>
                                </div>
                              ),
                            )}
                          </div>


                          {/* AI manual review */}

                          {aiResult.manual_review_required && (
                            <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4">
                              <p className="font-semibold text-amber-950">
                                Manual review
                                required
                              </p>

                              <p className="mt-2 text-sm leading-6 text-amber-900">
                                {aiResult.manual_review_reason ??
                                  "Manual review is required."}
                              </p>
                            </div>
                          )}
                        </section>
                      </div>
                    </article>
                  );
                },
              )}
            </section>
          </section>
        )}


        {!report &&
          !isLoading && (
            <section className="mt-8 grid gap-4 sm:grid-cols-2">
              <article className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                <h3 className="font-semibold text-slate-900">
                  Rule-based
                  assessment
                </h3>

                <p className="mt-2 max-w-full break-words [overflow-wrap:anywhere] text-sm leading-6 text-slate-600">
                  Applies deterministic
                  checks for the image
                  creator or copyright
                  holder, licence or
                  permission basis, and
                  location of the
                  applicable licence
                  terms.
                </p>
              </article>


              <article className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                <h3 className="font-semibold text-slate-900">
                  AI assessment
                </h3>

                <p className="mt-2 max-w-full break-words [overflow-wrap:anywhere] text-sm leading-6 text-slate-600">
                  Uses a local language
                  model to independently
                  interpret the extracted
                  copyright and licence
                  evidence and explain its
                  classification.
                </p>
              </article>
            </section>
          )}
      </div>
    </main>
  );
}