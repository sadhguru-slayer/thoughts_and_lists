import { formatJournalListDate } from "@/lib/formatDate";

export default function JournalList({ journals, onSelect }) {
  if (journals.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-300 bg-white/60 px-6 py-14 text-center dark:border-zinc-600 dark:bg-zinc-900/40">
        <p className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
          No journal entries yet.
        </p>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
          Create one with “New journal” above.
        </p>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {journals.map((j) => {
        const textPreview = j.content?.trim()
          ? j.content.length > 120
            ? `${j.content.slice(0, 120).trim()}…`
            : j.content
          : null;
        const sectionCount = j.sectionCount ?? 0;
        const preview =
          textPreview ||
          (sectionCount > 0
            ? `${sectionCount} section${sectionCount === 1 ? "" : "s"}`
            : "Empty entry");
        return (
          <li key={j.id}>
            <button
              type="button"
              onClick={() => onSelect(j.id)}
              className="group flex w-full items-start gap-4 rounded-xl border border-zinc-200 bg-white px-4 py-4 text-left shadow-sm transition hover:border-zinc-300 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-zinc-600 dark:focus-visible:ring-zinc-500 dark:focus-visible:ring-offset-zinc-950"
            >
              <div className="min-w-0 flex-1">
                <time
                  dateTime={j.date}
                  className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
                >
                  {formatJournalListDate(j.date)}
                </time>
                <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-zinc-900 dark:text-zinc-100">
                  {preview}
                </p>
              </div>
              <span
                className="mt-1 shrink-0 text-zinc-400 transition group-hover:translate-x-0.5 group-hover:text-zinc-600 dark:text-zinc-500 dark:group-hover:text-zinc-300"
                aria-hidden
              >
                →
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
