"use client";

import { useState } from "react";

import Header from "@/components/Header";
import UploadPanel, {
  type AnalysisInput,
} from "@/components/UploadPanel";
import {
  analyseHtml,
  analyseUrl,
  analyseZip,
} from "@/lib/api";
import type { ThreeResultComplianceReport } from "@/types/report";

export default function Home() {
  const [report, setReport] =
    useState<ThreeResultComplianceReport | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function handleAnalyse(
    input: AnalysisInput,
  ): Promise<void> {
    setIsLoading(true);
    setErrorMessage("");
    setReport(null);

    try {
      let result: ThreeResultComplianceReport;

      if (input.method === "url") {
        result = await analyseUrl(
          input.url ?? "",
          input.intendedUse,
        );
      } else if (input.method === "html") {
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
      if (error instanceof Error) {
        setErrorMessage(error.message);
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
      <div className="mx-auto max-w-5xl">
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
              Analysis could not be completed
            </h2>

            <p className="mt-2 text-sm leading-6">
              {errorMessage}
            </p>
          </section>
        )}

        {report && (
          <section className="mt-8 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8">
            <div className="mb-5">
              <p className="text-sm font-semibold uppercase tracking-wider text-blue-700">
                Analysis complete
              </p>

              <h2 className="mt-1 text-2xl font-bold">
                API response received
              </h2>

              <p className="mt-2 text-sm leading-6 text-slate-600">
                The frontend successfully received the
                rule-based, AI, and comparison results from
                FastAPI. This temporary JSON view will be replaced
                with the final report dashboard.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-4">
              <article className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
                <p className="text-sm text-slate-500">
                  Rule Score
                </p>

                <p className="mt-1 text-2xl font-bold">
                  {report.overall_rule_score}%
                </p>
              </article>

              <article className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
                <p className="text-sm text-slate-500">
                  Images Analysed
                </p>

                <p className="mt-1 text-2xl font-bold">
                  {report.total_images}
                </p>
              </article>

              <article className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
                <p className="text-sm text-slate-500">
                  Systems Agree
                </p>

                <p className="mt-1 text-2xl font-bold">
                  {report.systems_disagree_count === 0
                    ? "Yes"
                    : "No"}
                </p>
              </article>

              <article className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
                <p className="text-sm text-slate-500">
                  Manual Review
                </p>

                <p className="mt-1 text-2xl font-bold">
                  {report.manual_review_recommended
                    ? "Yes"
                    : "No"}
                </p>
              </article>
            </div>

            <div className="mt-6 overflow-x-auto rounded-xl bg-slate-950 p-5">
              <pre className="text-sm leading-6 text-slate-100">
                {JSON.stringify(report, null, 2)}
              </pre>
            </div>
          </section>
        )}

        {!report && !isLoading && (
          <section className="mt-8 grid gap-4 sm:grid-cols-3">
            <article className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h3 className="font-semibold text-slate-900">
                Rule-Based Assessment
              </h3>

              <p className="mt-2 text-sm leading-6 text-slate-600">
                Applies deterministic copyright, attribution,
                and licence compliance checks.
              </p>
            </article>

            <article className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h3 className="font-semibold text-slate-900">
                AI Assessment
              </h3>

              <p className="mt-2 text-sm leading-6 text-slate-600">
                Uses a local large language model to interpret
                attribution evidence and explain its reasoning.
              </p>
            </article>

            <article className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h3 className="font-semibold text-slate-900">
                Comparison
              </h3>

              <p className="mt-2 text-sm leading-6 text-slate-600">
                Highlights agreements, disagreements, and cases
                requiring manual review.
              </p>
            </article>
          </section>
        )}
      </div>
    </main>
  );
}