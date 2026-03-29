/** Fixed locale so SSR and browser produce identical strings (avoids hydration mismatch). */
const LOCALE = "en-US";

export function formatJournalListDate(iso) {
  try {
    return new Intl.DateTimeFormat(LOCALE, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function formatJournalDetailDate(iso) {
  try {
    return new Intl.DateTimeFormat(LOCALE, {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}
