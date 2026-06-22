/**
 * ExportButton — shared component for downloading PDF/HTML reports.
 *
 * On click: POST to endpoint, receive blob, trigger browser download.
 * Shows loading spinner while generating.
 */

import { useState } from "react";
import api from "../../lib/api";

interface Props {
  endpoint: string;
  body?: Record<string, unknown>;
  filename: string;
  label?: string;
}

export default function ExportButton({
  endpoint,
  body = {},
  filename,
  label = "Export Report",
}: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.post(endpoint, body, {
        responseType: "blob",
      });

      const contentType = String(response.headers["content-type"] || "text/html");
      const ext = contentType.includes("pdf") ? "pdf" : "html";
      const fullFilename = filename.includes(".") ? filename : `${filename}.${ext}`;

      const blob = new Blob([response.data], { type: String(contentType) });
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = fullFilename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setError("Export failed — try again");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="inline-flex flex-col items-start">
      <button
        onClick={handleExport}
        disabled={loading}
        className="inline-flex items-center gap-2 rounded-lg border border-navy-600 bg-navy-800 px-4 py-2 text-sm font-medium text-navy-200 transition-colors hover:border-amber-500/50 hover:text-white disabled:opacity-50"
        title="Download as PDF or HTML"
      >
        {loading ? (
          <>
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
            Generating...
          </>
        ) : (
          <>
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            {label}
          </>
        )}
      </button>
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}
