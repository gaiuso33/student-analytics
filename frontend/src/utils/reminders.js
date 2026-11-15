import { formatDate } from "./interventions";

/** Short wording for when a follow-up is due, e.g. "Due tomorrow (13 Oct 2026)". Empty when there is nothing to say. */
export function dueLabel(item) {
  if (item.status === "done" || !item.due_date) return "";
  const date = formatDate(item.due_date);
  if (item.overdue) return `Overdue, was due ${date}`;
  if (item.due_soon) {
    const days = item.due_in_days;
    const when = days === 0 ? "Due today" : days === 1 ? "Due tomorrow" : `Due in ${days} days`;
    return `${when} (${date})`;
  }
  return `Due ${date}`;
}

/** How many follow-ups assigned to me are overdue or due soon (from GET /api/reminders). */
export const attentionCount = (summary) => (summary?.mine ? summary.mine.overdue + summary.mine.due_soon : 0);
