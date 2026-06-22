/** Drag-and-drop Kanban board for the application pipeline. */

import { useState } from "react";
import type { Application, ApplicationStatus } from "../../lib/types";
import Column from "./Column";

interface Props {
  applications: Application[];
  onStatusChange?: (appId: string, newStatus: ApplicationStatus) => void;
  onSelectApp?: (id: string) => void;
}

const COLUMNS: { id: ApplicationStatus; label: string }[] = [
  { id: "queued", label: "Queued" },
  { id: "tailoring", label: "Tailoring" },
  { id: "ready", label: "Ready" },
  { id: "submitted", label: "Submitted" },
  { id: "interviewing", label: "Interviewing" },
  { id: "offer", label: "Offer" },
];

export default function Board({
  applications,
  onStatusChange,
  onSelectApp,
}: Props) {
  const [localApps, setLocalApps] = useState(applications);

  // Group applications by status
  const grouped = COLUMNS.reduce(
    (acc, col) => {
      acc[col.id] = localApps.filter((a) => a.status === col.id);
      return acc;
    },
    {} as Record<string, Application[]>
  );

  const handleDrop = (appId: string, newStatus: string) => {
    setLocalApps((prev) =>
      prev.map((app) =>
        app.id === appId
          ? { ...app, status: newStatus as ApplicationStatus }
          : app
      )
    );
    onStatusChange?.(appId, newStatus as ApplicationStatus);
  };

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {COLUMNS.map((col) => (
        <Column
          key={col.id}
          id={col.id}
          label={col.label}
          applications={grouped[col.id] || []}
          count={(grouped[col.id] || []).length}
          onSelectApp={onSelectApp}
          onDrop={handleDrop}
        />
      ))}
    </div>
  );
}
