import type { SubmissionStatus } from "./api";

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/** Show "-" while not graded; otherwise the score out of 100 (backend stores 0–100). */
export function formatSubmissionGrade(grade: number, status: SubmissionStatus): string {
  if (status === "pending" || status === "running") return "-";
  const g = Number.isFinite(grade) ? grade : 0;
  const rounded = Math.abs(g % 1) < 1e-9 ? g.toFixed(0) : g.toFixed(1);
  return `${rounded} / 100`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (iso == null || iso === "") return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
