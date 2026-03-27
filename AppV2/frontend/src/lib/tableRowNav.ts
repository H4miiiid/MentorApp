import { goto } from "$app/navigation";

/** Navigate unless the click started on an interactive child (link, button, form control). */
export function tableRowClick(e: MouseEvent, href: string): void {
  const el = e.target as HTMLElement | null;
  if (el?.closest("a, button, input, textarea, select, label")) return;
  void goto(href);
}

export function tableRowKeydown(e: KeyboardEvent, href: string): void {
  if (e.key !== "Enter" && e.key !== " ") return;
  e.preventDefault();
  void goto(href);
}
