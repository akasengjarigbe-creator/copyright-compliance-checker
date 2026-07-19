"use client";

import { FormEvent, useState } from "react";

export type InputMethod = "url" | "html" | "zip";

export interface AnalysisInput {
  method: InputMethod;
  url?: string;
  html?: string;
  baseUrl?: string;
  file?: File;
  intendedUse: string;
}

interface UploadPanelProps {
  onAnalyse: (input: AnalysisInput) => Promise<void>;
  isLoading: boolean;
}

export default function UploadPanel({
  onAnalyse,
  isLoading,
}: UploadPanelProps) {
  const [inputMethod, setInputMethod] =
    useState<InputMethod>("url");

  const [url, setUrl] = useState("");
  const [html, setHtml] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [zipFile, setZipFile] = useState<File | null>(null);

  const [intendedUse, setIntendedUse] = useState(
    "educational coursework",
  );

  const [validationError, setValidationError] = useState("");

  function selectInputMethod(method: InputMethod) {
    setInputMethod(method);
    setValidationError("");
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    setValidationError("");

    const cleanedIntendedUse = intendedUse.trim();

    if (!cleanedIntendedUse) {
      setValidationError(
        "Please describe the intended use of the image.",
      );
      return;
    }

    if (inputMethod === "url") {
      const cleanedUrl = url.trim();

      if (!cleanedUrl) {
        setValidationError(
          "Please enter a webpage URL.",
        );
        return;
      }

      await onAnalyse({
        method: "url",
        url: cleanedUrl,
        intendedUse: cleanedIntendedUse,
      });

      return;
    }

    if (inputMethod === "html") {
      const cleanedHtml = html.trim();

      if (!cleanedHtml) {
        setValidationError(
          "Please paste the HTML you want to analyse.",
        );
        return;
      }

      await onAnalyse({
        method: "html",
        html: cleanedHtml,
        baseUrl: baseUrl.trim() || undefined,
        intendedUse: cleanedIntendedUse,
      });

      return;
    }

    if (!zipFile) {
      setValidationError(
        "Please choose a ZIP file.",
      );
      return;
    }

    if (!zipFile.name.toLowerCase().endsWith(".zip")) {
      setValidationError(
        "The selected file must have a .zip extension.",
      );
      return;
    }

    await onAnalyse({
      method: "zip",
      file: zipFile,
      intendedUse: cleanedIntendedUse,
    });
  }

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8">
      <div className="mb-6">
        <h2 className="text-xl font-semibold">
          Choose an analysis method
        </h2>

        <p className="mt-1 text-sm text-slate-600">
          Select the type of content you want to assess.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <button
          type="button"
          onClick={() => selectInputMethod("url")}
          disabled={isLoading}
          className={`rounded-xl border px-4 py-4 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
            inputMethod === "url"
              ? "border-blue-600 bg-blue-50 text-blue-900"
              : "border-slate-300 bg-white hover:border-blue-400"
          }`}
        >
          <span className="block font-semibold">
            Analyse URL
          </span>

          <span className="mt-1 block text-sm text-slate-600">
            Check a live webpage.
          </span>
        </button>

        <button
          type="button"
          onClick={() => selectInputMethod("html")}
          disabled={isLoading}
          className={`rounded-xl border px-4 py-4 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
            inputMethod === "html"
              ? "border-blue-600 bg-blue-50 text-blue-900"
              : "border-slate-300 bg-white hover:border-blue-400"
          }`}
        >
          <span className="block font-semibold">
            Paste HTML
          </span>

          <span className="mt-1 block text-sm text-slate-600">
            Analyse a source-code snippet.
          </span>
        </button>

        <button
          type="button"
          onClick={() => selectInputMethod("zip")}
          disabled={isLoading}
          className={`rounded-xl border px-4 py-4 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
            inputMethod === "zip"
              ? "border-blue-600 bg-blue-50 text-blue-900"
              : "border-slate-300 bg-white hover:border-blue-400"
          }`}
        >
          <span className="block font-semibold">
            Upload ZIP
          </span>

          <span className="mt-1 block text-sm text-slate-600">
            Assess a complete website submission.
          </span>
        </button>
      </div>

      <form
        onSubmit={handleSubmit}
        className="mt-8 rounded-xl border border-slate-200 bg-slate-50 p-5"
      >
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
              value={url}
              onChange={(event) =>
                setUrl(event.target.value)
              }
              disabled={isLoading}
              placeholder="https://example.com/coursework"
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100"
            />
          </div>
        )}

        {inputMethod === "html" && (
          <div className="space-y-5">
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
                value={html}
                onChange={(event) =>
                  setHtml(event.target.value)
                }
                disabled={isLoading}
                placeholder="<html>...</html>"
                className="w-full resize-y rounded-lg border border-slate-300 bg-white px-4 py-3 font-mono text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100"
              />
            </div>

            <div>
              <label
                htmlFor="base-url"
                className="mb-2 block text-sm font-medium text-slate-800"
              >
                Base URL{" "}
                <span className="font-normal text-slate-500">
                  (optional)
                </span>
              </label>

              <input
                id="base-url"
                type="url"
                value={baseUrl}
                onChange={(event) =>
                  setBaseUrl(event.target.value)
                }
                disabled={isLoading}
                placeholder="https://example.com/page.html"
                className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100"
              />

              <p className="mt-2 text-sm text-slate-500">
                This helps resolve relative image paths such as
                images/photo.jpg.
              </p>
            </div>
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
              disabled={isLoading}
              onChange={(event) =>
                setZipFile(
                  event.target.files?.[0] ?? null,
                )
              }
              className="block w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm disabled:cursor-not-allowed disabled:bg-slate-100"
            />

            <p className="mt-2 text-sm text-slate-500">
              Upload a ZIP containing one or more HTML pages and
              related website assets.
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
            value={intendedUse}
            onChange={(event) =>
              setIntendedUse(event.target.value)
            }
            disabled={isLoading}
            className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100"
          />
        </div>

        {validationError && (
          <div
            role="alert"
            className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
          >
            {validationError}
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="mt-6 flex w-full items-center justify-center rounded-lg bg-blue-700 px-5 py-3 font-semibold text-white transition hover:bg-blue-800 focus:outline-none focus:ring-4 focus:ring-blue-200 disabled:cursor-not-allowed disabled:bg-blue-400"
        >
          {isLoading ? (
            <>
              <span
                aria-hidden="true"
                className="mr-3 h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent"
              />

              Analysing content...
            </>
          ) : (
            "Analyse content"
          )}
        </button>

        {isLoading && (
          <p className="mt-3 text-center text-sm text-slate-500">
            The local AI assessment may take several minutes.
          </p>
        )}
      </form>
    </section>
  );
}