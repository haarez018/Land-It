/** Status column for the Kanban board — droppable zone. */

import type { Application } from "../../lib/types";
import Card from "./Card";

interface Props {
  id: string;
  label: string;
  applications: Application[];
  count: number;
  onSelectApp?: (id: string) => void;
  onDrop?: (appId: string, newStatus: string) => void;
}

const COLUMN_COLORS: Record<string, string> = {
  queued: "text-blue-400",
  tailoring: "text-amber-400",
  ready: "text-emerald-400",
  submitted: "text-purple-400",
  interviewing: "text-orange-400",
  offer: "text-emerald-300",
};

export default function Column({
  id,
  label,
  applications,
  count,
  onSelectApp,
  onDrop,
}: Props) {
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.add("ring-2", "ring-amber-500/30");
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove("ring-2", "ring-amber-500/30");
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.remove("ring-2", "ring-amber-500/30");
    const appId = e.dataTransfer.getData("text/plain");
    if (appId && onDrop) {
      onDrop(appId, id);
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="flex min-w-[260px] flex-shrink-0 flex-col rounded-xl border border-navy-700 bg-navy-800 transition-all"
    >
      {/* Column header */}
      <div className="flex items-center justify-between border-b border-navy-700 px-4 py-3">
        <div className="flex items-center gap-2">
          <h3
            className={`text-sm font-semibold ${
              COLUMN_COLORS[id] || "text-navy-300"
            }`}
          >
            {label}
          </h3>
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-navy-700 text-[10px] font-bold text-navy-400">
            {count}
          </span>
        </div>
      </div>

      {/* Cards */}
      <div className="flex-1 space-y-2 overflow-y-auto p-3" style={{ maxHeight: "calc(100vh - 320px)" }}>
        {applications.length > 0 ? (
          applications.map((app) => (
            <div
              key={app.id}
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData("text/plain", app.id);
              }}
            >
              <Card application={app} onSelect={onSelectApp} />
            </div>
          ))
        ) : (
          <div className="rounded-lg border border-dashed border-navy-600 p-4 text-center text-xs text-navy-500">
            No applications
          </div>
        )}
      </div>
    </div>
  );
}
