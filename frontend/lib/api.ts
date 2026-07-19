import type { ThreeResultComplianceReport } from "@/types/report";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000/api";

async function parseResponse(
  response: Response,
): Promise<ThreeResultComplianceReport> {
  if (!response.ok) {
    let message = "The analysis request failed.";

    try {
      const errorBody = await response.json();

      if (typeof errorBody.detail === "string") {
        message = errorBody.detail;
      }
    } catch {
      // Keep the fallback message when the response is not JSON.
    }

    throw new Error(message);
  }

  return response.json() as Promise<ThreeResultComplianceReport>;
}

export async function analyseUrl(
  url: string,
  intendedUse: string,
): Promise<ThreeResultComplianceReport> {
  const response = await fetch(`${API_BASE_URL}/analyse-url`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      url,
      intended_use: intendedUse,
    }),
  });

  return parseResponse(response);
}

export async function analyseHtml(
  html: string,
  intendedUse: string,
  baseUrl?: string,
): Promise<ThreeResultComplianceReport> {
  const response = await fetch(`${API_BASE_URL}/analyse-html`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      html,
      base_url: baseUrl || null,
      intended_use: intendedUse,
    }),
  });

  return parseResponse(response);
}

export async function analyseZip(
  file: File,
  intendedUse: string,
): Promise<ThreeResultComplianceReport> {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("intended_use", intendedUse);

  const response = await fetch(`${API_BASE_URL}/analyse-zip`, {
    method: "POST",
    body: formData,
  });

  return parseResponse(response);
}