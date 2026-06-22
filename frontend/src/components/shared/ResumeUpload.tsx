/** Resume file upload component with drag-and-drop support. */

import { useCallback, useRef, useState } from "react";

interface Props {
  onUpload: (file: File) => void;
  loading?: boolean;
  fileName?: string;
}

export default function ResumeUpload({ onUpload, loading, fileName }: Props) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) onUpload(file);
    },
    [onUpload]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onUpload(file);
    },
    [onUpload]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`flex h-32 cursor-pointer items-center justify-center rounded-lg border-2 border-dashed transition-colors ${
        dragging
          ? "border-amber-400 bg-amber-500/5"
          : fileName
            ? "border-emerald-500/50 bg-emerald-500/5"
            : "border-[var(--border-primary)] hover:border-[var(--accent)]"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.doc"
        onChange={handleChange}
        className="hidden"
      />
      {loading ? (
        <div className="flex items-center gap-2 text-amber-400">
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
            <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
          </svg>
          <span className="text-sm">Parsing...</span>
        </div>
      ) : fileName ? (
        <div className="text-center">
          <p className="text-sm font-medium text-emerald-400">{fileName}</p>
          <p className="mt-1 text-xs text-muted-theme">Click to replace</p>
        </div>
      ) : (
        <p className="text-sm text-muted-theme">
          Drop PDF/DOCX here or click to upload
        </p>
      )}
    </div>
  );
}
