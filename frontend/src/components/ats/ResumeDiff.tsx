/** Side-by-side resume diff view using react-diff-viewer-continued. */

import ReactDiffViewer, { DiffMethod } from "react-diff-viewer-continued";
import type { ChangeLogEntry } from "../../lib/types";

interface Props {
  unifiedDiff: string;
  changeLog: ChangeLogEntry[];
  originalText?: string;
  rewrittenText?: string;
}

const diffStyles = {
  variables: {
    dark: {
      diffViewerBackground: "#0f172a",
      addedBackground: "#064e3b30",
      removedBackground: "#7f1d1d30",
      addedColor: "#6ee7b7",
      removedColor: "#fca5a5",
      wordAddedBackground: "#065f4640",
      wordRemovedBackground: "#991b1b40",
      addedGutterBackground: "#064e3b20",
      removedGutterBackground: "#7f1d1d20",
      gutterBackground: "#1e293b",
      gutterColor: "#475569",
      codeFoldBackground: "#1e293b",
      codeFoldGutterBackground: "#1e293b",
    },
  },
  line: {
    fontSize: "13px",
    fontFamily: "'JetBrains Mono', monospace",
  },
};

export default function ResumeDiff({
  unifiedDiff,
  changeLog,
  originalText,
  rewrittenText,
}: Props) {
  return (
    <div className="space-y-4">
      {/* Change log summary */}
      {changeLog.length > 0 && (
        <div className="rounded-xl border border-navy-700 bg-navy-800 p-4">
          <h3 className="text-lg font-semibold text-white">
            Changes Made ({changeLog.length})
          </h3>
          <div className="mt-3 max-h-64 space-y-2 overflow-y-auto">
            {changeLog.map((change, i) => (
              <div
                key={i}
                className="rounded-lg border border-navy-700 bg-navy-900/50 p-3"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-amber-400">
                    {change.section}
                  </span>
                  {change.requires_verification && (
                    <span className="rounded bg-orange-500/20 px-1.5 py-0.5 text-[10px] font-bold text-orange-400">
                      VERIFY
                    </span>
                  )}
                  <span className="rounded bg-navy-600 px-1.5 py-0.5 text-[10px] text-navy-300">
                    {change.confidence}
                  </span>
                </div>
                <p className="mt-1 text-sm text-navy-300">{change.reason}</p>
                <div className="mt-2 flex gap-2 text-xs">
                  {change.dimension_improved.map((dim) => (
                    <span
                      key={dim}
                      className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-emerald-400"
                    >
                      {dim.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Diff viewer */}
      {originalText && rewrittenText && (
        <div className="overflow-hidden rounded-xl border border-navy-700">
          <ReactDiffViewer
            oldValue={originalText}
            newValue={rewrittenText}
            splitView={true}
            useDarkTheme={true}
            compareMethod={DiffMethod.WORDS}
            styles={diffStyles}
            leftTitle="Original Resume"
            rightTitle="Tailored Resume"
          />
        </div>
      )}

      {/* Fallback: raw unified diff */}
      {!originalText && unifiedDiff && (
        <div className="overflow-hidden rounded-xl border border-navy-700 bg-navy-900 p-4">
          <h3 className="mb-2 text-sm font-semibold text-navy-400">
            Unified Diff
          </h3>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap font-mono text-xs text-navy-300">
            {unifiedDiff}
          </pre>
        </div>
      )}
    </div>
  );
}
