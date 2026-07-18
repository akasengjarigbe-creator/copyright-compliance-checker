"use client";

import { useState } from "react";

type InputMethod = "url" | "html" | "zip";

export default function Home() {
  const [inputMethod, setInputMethod] = useState<InputMethod>("url");

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10 text-slate-900">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8 text-center">
          <p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-blue-700">
            AI-assisted assessment
          </p>

          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Copyright Compliance Checker
          </h1>

          <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-slate-600">
            Analyse webpages, HTML source code, or ZIP website submissions
            using rule-based checks, AI reasoning, and a transparent comparison
            of both results.
          </p>
        </header>

        <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8">
          <div className="mb-6">
            <h2 className="text-xl font-semibold">Choose an analysis method</h2>
            <p className="mt-1 text-sm text-slate-600">
              Select the type of content you want to assess.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <button
              type="button"
              onClick={() => setInputMethod("url")}
              className={`rounded-xl border px-4 py-4 text-left transition ${
                inputMethod === "url"
                  ? "border-blue-600 bg-blue-50 text-blue-900"
                  : "border-slate-300 bg-white hover:border-blue-400"
              }`}
            >
              <span className="block font-semibold">Analyse URL</span>
              <span className="mt-1 block text-sm text-slate-600">
                Check a live webpage.
              </span>
            </button>

            <button
              type="button"
              onClick={() => setInputMethod("html")}
              className={`rounded-xl border px-4 py-4 text-left transition ${
                inputMethod === "html"
                  ? "border-blue-600 bg-blue-50 text-blue-900"
                  : "border-slate-300 bg-white hover:border-blue-400"
              }`}
            >
              <span className="block font-semibold">Paste HTML</span>
              <span className="mt-1 block text-sm text-slate-600">
                Analyse a source-code snippet.
              </span>
            </button>

            <button
              type="button"
              onClick={() => setInputMethod("zip")}
              className={`rounded-xl border px-4 py-4 text-left transition ${
                inputMethod === "zip"
                  ? "border-blue-600 bg-blue-50 text-blue-900"
                  : "border-slate-300 bg-white hover:border-blue-400"
              }`}
            >
              <span className="block font-semibold">Upload ZIP</span>
              <span className="mt-1 block text-sm text-slate-600">
                Assess a complete website submission.
              </span>
            </button>
          </div>

          <div className="mt-8 rounded-xl border border-slate-200 bg-slate-50 p-5">
            {inputMethod === "url" && (
              <div>
                <label
                  htmlFor="url"
                  className="mb-2 block text-sm font-medium text-slate-800"
                >
                  Webpage URL
                </label>

                <input
                  id="url"
                  type="url"
                  placeholder="https://example.com/coursework"
                  className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>
            )}

            {inputMethod === "html" && (
              <div>
                <label
                  htmlFor="html"
                  className="mb-2 block text-sm font-medium text-slate-800"
                >
                  HTML source
                </label>

                <textarea
                  id="html"
                  rows={10}
                  placeholder="<html>...</html>"
                  className="w-full resize-y rounded-lg border border-slate-300 bg-white px-4 py-3 font-mono text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>
            )}

            {inputMethod === "zip" && (
              <div>
                <label
                  htmlFor="zip"
                  className="mb-2 block text-sm font-medium text-slate-800"
                >
                  ZIP submission
                </label>

                <input
                  id="zip"
                  type="file"
                  accept=".zip,application/zip"
                  className="block w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm"
                />

                <p className="mt-2 text-sm text-slate-500">
                  Upload a ZIP containing one or more HTML pages and related
                  website assets.
                </p>
              </div>
            )}

            <div className="mt-5">
              <label
                htmlFor="intended-use"
                className="mb-2 block text-sm font-medium text-slate-800"
              >
                Intended use
              </label>

              <input
                id="intended-use"
                type="text"
                defaultValue="educational coursework"
                className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </div>

            <button
              type="button"
              className="mt-6 w-full rounded-lg bg-blue-700 px-5 py-3 font-semibold text-white transition hover:bg-blue-800 focus:outline-none focus:ring-4 focus:ring-blue-200"
            >
              Analyse content
            </button>
          </div>
        </section>

        <section className="mt-8 grid gap-4 sm:grid-cols-3">
          <article className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h3 className="font-semibold text-slate-900">
              Rule-Based Assessment
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Applies deterministic copyright, attribution, and licence checks.
            </p>
          </article>

          <article className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h3 className="font-semibold text-slate-900">AI Assessment</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Interprets attribution evidence and explains its reasoning.
            </p>
          </article>

          <article className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h3 className="font-semibold text-slate-900">Comparison</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Highlights agreement, disagreement, and cases requiring review.
            </p>
          </article>
        </section>
      </div>
    </main>
  );
}