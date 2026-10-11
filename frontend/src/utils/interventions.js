export const NOTE_MAX = 1000;

export const KINDS = [
  { value: "meeting", label: "Meeting" },
  { value: "tutoring", label: "Tutoring" },
  { value: "counselling", label: "Counselling" },
  { value: "parent_contact", label: "Parent or guardian contact" },
  { value: "referral", label: "Referral" },
  { value: "other", label: "Other" },
];

export const kindLabel = (value) => KINDS.find((k) => k.value === value)?.label ?? value;

/** Accepts "YYYY-MM-DD" or the server's "YYYY-MM-DD HH:MM:SS" (UTC); returns e.g. "12 Oct 2026". */
export function formatDate(value) {
  if (!value) return "";
  const iso = value.length <= 10 ? `${value}T00:00:00Z` : `${value.replace(" ", "T")}Z`;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

/** First `max` characters of a note, cut at a word where possible. */
export function excerpt(text, max = 110) {
  const flat = text.replace(/\s+/g, " ").trim();
  if (flat.length <= max) return flat;
  const cut = flat.slice(0, max);
  const space = cut.lastIndexOf(" ");
  return `${(space > max * 0.6 ? cut.slice(0, space) : cut).trimEnd()}…`;
}
